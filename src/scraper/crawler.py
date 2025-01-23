from playwright.async_api import async_playwright
from typing import List, Dict, Any
import asyncio
import structlog
from src.config import settings

logger = structlog.get_logger()

class WebCrawler:
    def __init__(self):
        self.visited_urls: set = set()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: List[Dict[str, Any]] = []
        
    async def init_playwright(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        
    async def close(self):
        await self.browser.close()
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
        # Implementation will depend on the specific website structure
        pass
    
    async def _extract_metadata(self, page) -> Dict[str, Any]:
        """Extract metadata from the page"""
        metadata = {
            "last_updated": await page.evaluate("() => document.lastModified"),
            "word_count": await page.evaluate("""
                () => document.body.innerText.split(/\s+/).length
            """)
        }
        return metadata
    
    async def _extract_media(self, page) -> List[Dict[str, Any]]:
        """Extract media elements from the page"""
        media = []
        # Extract images
        images = await page.evaluate("""
            () => Array.from(document.images).map(img => ({
                type: 'image',
                url: img.src,
                alt: img.alt
            }))
        """)
        media.extend(images)
        
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
    
    async def crawl(self, start_url: str):
        """Main crawling method"""
        await self.init_playwright()
        await self.queue.put(start_url)
        
        workers = [
            self._worker(i) 
            for i in range(settings.MAX_CONCURRENT_SCRAPES)
        ]
        await asyncio.gather(*workers)
        
        await self.close()
        return self.results
    
    async def _worker(self, worker_id: int):
        """Worker to process URLs from the queue"""
        context = await self.browser.new_context()
        page = await context.new_page()
        
        while True:
            try:
                url = await self.queue.get()
                
                if url in self.visited_urls:
                    self.queue.task_done()
                    continue
                
                logger.info(f"Worker {worker_id} processing", url=url)
                
                await page.goto(url, wait_until="networkidle")
                content = await self.extract_content(page)
                self.results.append(content)
                
                # Find new links
                new_urls = await self._extract_links(page)
                for new_url in new_urls:
                    if new_url not in self.visited_urls:
                        await self.queue.put(new_url)
                
                self.visited_urls.add(url)
                self.queue.task_done()
                
                # Respect rate limiting
                await asyncio.sleep(settings.SCRAPING_DELAY)
                
            except Exception as e:
                logger.error("Error processing URL", 
                           url=url, 
                           error=str(e),
                           worker_id=worker_id)
                self.queue.task_done()
    
    async def _extract_links(self, page) -> List[str]:
        """Extract valid links from the page"""
        links = await page.evaluate(f"""
            () => Array.from(document.links)
                .map(link => link.href)
                .filter(href => href.startsWith('{settings.TARGET_DOMAIN}'))
        """)
        return links 