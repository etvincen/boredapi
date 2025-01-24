import asyncio
import structlog
from src.scraper.crawler import WebCrawler
from src.config import settings
import json
from pathlib import Path
from datetime import datetime

logger = structlog.get_logger()

async def run_crawler_test():
    try:
        logger.info("Starting crawler test")
        
        # Initialize crawler
        crawler = WebCrawler()
        
        # Run crawl operation
        results = await crawler.crawl(
            start_url=settings.TARGET_DOMAIN,
            max_duration=3600
        )
        
        # Create output directory if it doesn't exist
        output_dir = Path("crawl_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save results to file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"crawl_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "stats": results["stats"],
                    "storage": results["storage"],
                    "results": results["results"],
                    "config": {
                        "target_domain": settings.TARGET_DOMAIN,
                        "max_concurrent_scrapes": settings.MAX_CONCURRENT_SCRAPES,
                        "scraping_delay": settings.SCRAPING_DELAY
                    }
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        
        logger.info(
            "Crawl completed",
            total_processed=results["stats"]["total_processed"],
            total_failed=results["stats"]["total_failed"],
            total_queued=results["stats"]["total_queued"],
            storage_mb=results["storage"]["total_mb"],
            storage_percentage=results["storage"]["usage_percentage"],
            output_file=str(output_file)
        )
        
        # Print summary
        print("\nCrawl Summary:")
        print(f"Total Processed: {results['stats']['total_processed']}")
        print(f"Total Failed: {results['stats']['total_failed']}")
        print(f"Total URLs Found: {results['stats']['total_queued']}")
        print(f"\nStorage Usage:")
        print(f"Total Size: {results['storage']['total_mb']:.2f} MB")
        print(f"Usage: {results['storage']['usage_percentage']:.1f}%")
        print(f"\nResults saved to: {output_file}")
        
        # Alert if storage usage is high
        if results["storage"]["usage_percentage"] > 80:
            print("\n⚠️  WARNING: Storage usage is high!")
            
    except Exception as e:
        logger.error("Crawler test failed", error=str(e))
        raise

def main():
    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    )
    
    # Run the crawler
    asyncio.run(run_crawler_test())

if __name__ == "__main__":
    main() 