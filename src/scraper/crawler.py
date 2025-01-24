from playwright.async_api import async_playwright
from typing import List, Dict, Any, Set
import asyncio
import structlog
from src.config import settings
from dataclasses import dataclass
from contextlib import asynccontextmanager
import sys
import json
from pathlib import Path

logger = structlog.get_logger()

@dataclass
class CrawlStats:
    """Statistics for the crawling process"""
    total_processed: int = 0
    total_failed: int = 0
    total_queued: int = 0

@dataclass
class StorageStats:
    """Statistics for storage monitoring"""
    total_bytes: int = 0
    max_bytes: int = 1024 * 1024 * 1024  # 1GB in bytes
    
    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)
    
    @property
    def usage_percentage(self) -> float:
        return (self.total_bytes / self.max_bytes) * 100

class SharedState:
    """Thread-safe shared state for crawling"""
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.stats = CrawlStats()
        self.storage_stats = StorageStats()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: List[Dict[str, Any]] = []
        self._url_lock = asyncio.Lock()
        self._results_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        self._storage_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
    
    async def check_storage_limits(self, content: Dict[str, Any]) -> bool:
        """Check if adding content would exceed storage limits"""
        async with self._storage_lock:
            # Calculate content size in bytes
            content_size = sys.getsizeof(json.dumps(content))
            
            # Check if adding this content would exceed limits
            if self.storage_stats.total_bytes + content_size > self.storage_stats.max_bytes:
                logger.warning(
                    "Storage limit would be exceeded",
                    current_mb=self.storage_stats.total_mb,
                    content_size_mb=content_size / (1024 * 1024),
                    max_mb=self.storage_stats.max_bytes / (1024 * 1024)
                )
                return False
            
            # Update storage stats
            self.storage_stats.total_bytes += content_size
            
            # Log warning if approaching limit
            if self.storage_stats.usage_percentage > 80:
                logger.warning(
                    "Storage usage high",
                    usage_percentage=self.storage_stats.usage_percentage,
                    total_mb=self.storage_stats.total_mb
                )
            
            return True
    
    async def add_visited_url(self, url: str) -> bool:
        """Thread-safe addition of visited URLs"""
        async with self._url_lock:
            if url in self.visited_urls:
                return False
            self.visited_urls.add(url)
            return True
    
    async def add_result(self, result: Dict[str, Any]) -> bool:
        """Thread-safe addition of results with storage check"""
        if not await self.check_storage_limits(result):
            self.stop_crawling()
            return False
            
        async with self._results_lock:
            self.results.append(result)
            return True
    
    async def update_stats(self, processed: int = 0, failed: int = 0, queued: int = 0):
        """Thread-safe update of statistics"""
        async with self._stats_lock:
            self.stats.total_processed += processed
            self.stats.total_failed += failed
            self.stats.total_queued += queued
    
    def stop_crawling(self):
        """Signal workers to stop"""
        self._stop_event.set()
    
    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()

class WebCrawler:
    def __init__(self):
        self.state = SharedState()
        self.browser = None
        self.playwright = None
        
    @asynccontextmanager
    async def browser_context(self):
        """Context manager for browser initialization and cleanup"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch()
            yield
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def extract_content(self, page) -> Dict[str, Any]:
        """Extract content from a page"""
        content = {
            "url": page.url,
            "title": await page.title(),
            "content": await page.content(),
            "type": await self._determine_content_type(page),
            "metadata": await self._extract_metadata(page),
            "media": await self._extract_media(page),
        }
        return content
    
    async def _determine_content_type(self, page) -> str:
        """Determine the type of content on the page"""
        # Implementation depends on specific website structure
        pass
    
    async def _extract_metadata(self, page) -> Dict[str, Any]:
        """Extract metadata from the page"""
        try:
            metadata = {
                "last_updated": await page.evaluate("() => document.lastModified"),
                "word_count": await page.evaluate("""
                    () => document.body.innerText.split(/\s+/).length
                """)
            }
            return metadata
        except Exception as e:
            logger.error("Error extracting metadata", error=str(e))
            return {}
    
    async def _extract_media(self, page) -> List[Dict[str, Any]]:
        """Extract media elements from the page"""
        try:
            media = []
            # Extract images with retry mechanism
            for attempt in range(3):
                try:
                    images = await page.evaluate("""
                        () => Array.from(document.images).map(img => ({
                            type: 'image',
                            url: img.src,
                            alt: img.alt
                        }))
                    """)
                    media.extend(images)
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error("Failed to extract images", error=str(e))
                    await asyncio.sleep(1)
            
            # Extract videos
            videos = await page.evaluate("""
                () => Array.from(document.getElementsByTagName('video')).map(video => ({
                    type: 'video',
                    url: video.src,
                    poster: video.poster
                }))
            """)
            media.extend(videos)
            
            return media
        except Exception as e:
            logger.error("Error extracting media", error=str(e))
            return []
    
    async def _extract_links(self, page) -> List[str]:
        """Extract valid links from the page"""
        try:
            links = await page.evaluate(f"""
                () => Array.from(document.links)
                    .map(link => link.href)
                    .filter(href => href.startsWith('{settings.TARGET_DOMAIN}'))
            """)
            return links
        except Exception as e:
            logger.error("Error extracting links", error=str(e))
            return []
    
    async def _worker(self, worker_id: int):
        """Worker to process URLs from the queue"""
        async with self.browser.new_context() as context:
            page = await context.new_page()
            
            while not self.state.should_stop:
                try:
                    # Get URL with timeout
                    try:
                        url = await asyncio.wait_for(
                            self.state.queue.get(), 
                            timeout=10
                        )
                    except asyncio.TimeoutError:
                        if self.state.queue.empty():
                            break
                        continue
                    
                    # Check if URL was already processed
                    if not await self.state.add_visited_url(url):
                        self.state.queue.task_done()
                        continue
                    
                    logger.info(f"Worker {worker_id} processing", url=url)
                    
                    # Navigate with retry mechanism
                    for attempt in range(3):
                        try:
                            await page.goto(
                                url, 
                                wait_until="networkidle",
                                timeout=30000
                            )
                            break
                        except Exception as e:
                            if attempt == 2:
                                raise
                            await asyncio.sleep(2 ** attempt)
                    
                    content = await self.extract_content(page)
                    
                    # Try to add result, stop if storage limit reached
                    if not await self.state.add_result(content):
                        logger.error(
                            "Storage limit reached - stopping crawler",
                            total_mb=self.state.storage_stats.total_mb,
                            url=url
                        )
                        self.state.stop_crawling()
                        break
                    
                    await self.state.update_stats(processed=1)
                    
                    # Process new links
                    new_urls = await self._extract_links(page)
                    queued = 0
                    for new_url in new_urls:
                        if new_url not in self.state.visited_urls:
                            await self.state.queue.put(new_url)
                            queued += 1
                    
                    await self.state.update_stats(queued=queued)
                    
                    # Respect rate limiting
                    await asyncio.sleep(settings.SCRAPING_DELAY)
                    
                except Exception as e:
                    logger.error(
                        "Error processing URL", 
                        url=url, 
                        error=str(e),
                        worker_id=worker_id
                    )
                    await self.state.update_stats(failed=1)
                finally:
                    self.state.queue.task_done()
    
    async def crawl(self, start_url: str, max_duration: int = 3600):
        """Main crawling method with timeout"""
        async with self.browser_context():
            # Initialize with start URL
            await self.state.queue.put(start_url)
            await self.state.update_stats(queued=1)
            
            # Create workers
            workers = [
                self._worker(i) 
                for i in range(settings.MAX_CONCURRENT_SCRAPES)
            ]
            
            try:
                # Run workers with timeout
                await asyncio.wait_for(
                    asyncio.gather(*workers),
                    timeout=max_duration
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Crawl timeout reached",
                    duration=max_duration,
                    processed=self.state.stats.total_processed
                )
                self.state.stop_crawling()
            except Exception as e:
                logger.error("Crawl error", error=str(e))
                self.state.stop_crawling()
            finally:
                # Wait for queue to be empty
                if not self.state.queue.empty():
                    await self.state.queue.join()
            
            return {
                "results": self.state.results,
                "stats": self.state.stats.__dict__,
                "storage": {
                    "total_mb": self.state.storage_stats.total_mb,
                    "usage_percentage": self.state.storage_stats.usage_percentage,
                    "max_mb": self.state.storage_stats.max_bytes / (1024 * 1024)
                }
            } 