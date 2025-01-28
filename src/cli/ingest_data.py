import asyncio
import structlog
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, List
from src.storage.elasticsearch import ElasticsearchClient
from src.storage.postgresql import PostgresClient
from contextlib import asynccontextmanager

logger = structlog.get_logger()

class DataIngestion:
    def __init__(self):
        self.es_client = None
        self.pg_client = None
    
    async def __aenter__(self):
        """Initialize clients when entering context"""
        try:
            self.es_client = ElasticsearchClient()
            self.pg_client = PostgresClient()
            await self.init_storage()
            return self
        except Exception as e:
            logger.error("Failed to initialize storage clients", error=str(e))
            if self.es_client:
                await self.es_client.close()
            if self.pg_client:
                await self.pg_client.close()
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup clients when exiting context"""
        if self.es_client:
            await self.es_client.close()
        if self.pg_client:
            await self.pg_client.close()
    
    async def init_storage(self):
        """Initialize storage connections and schemas"""
        # Initialize Elasticsearch indices
        await self.es_client.init_indices()
        
        # Initialize PostgreSQL connection and tables
        await self.pg_client.init_pool()
        await self.pg_client.init_tables()
    
    async def get_latest_crawl_results(self) -> Dict[str, Any]:
        """Get the latest crawl results file"""
        crawl_dir = Path("crawl_results")
        if not crawl_dir.exists():
            raise FileNotFoundError("No crawl results directory found")
            
        result_files = list(crawl_dir.glob("crawl_results_*.json"))
        if not result_files:
            raise FileNotFoundError("No crawl result files found")
            
        # Get the latest file by name (they contain timestamps)
        latest_file = max(result_files)
        
        logger.info("Found latest crawl results", file=str(latest_file))
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def store_content(self, content: Dict[str, Any]) -> str:
        """Store a single content item and its metadata"""
        try:
            # Store in Elasticsearch
            content_id = await self.es_client.store_content(content)
            
            # Extract metadata
            metadata = {
                'title': content.get('title'),
                'content_type': content.get('type'),
                'word_count': content.get('metadata', {}).get('word_count', 0),
                'media': content.get('media', [])
            }
            
            # Extract hierarchy information
            hierarchy = {
                'parent_id': content.get('hierarchy', {}).get('parent_id'),
                'level': content.get('hierarchy', {}).get('level', 0),
                'path': content.get('hierarchy', {}).get('path', [])
            }
            
            # Store metadata and hierarchy
            await self.pg_client.store_content_metadata(
                content_id=content_id,
                url=content['url'],
                metadata=metadata,
                hierarchy=hierarchy
            )
            
            return content_id
            
        except Exception as e:
            logger.error(
                "Error storing content",
                url=content.get("url"),
                error=str(e)
            )
            raise
    
    async def process_results(self, results: Dict[str, Any]):
        """Process and store all results"""
        stored_count = 0
        failed_count = 0
        
        for content in results["results"]:
            try:
                content_id = await self.store_content(content)
                stored_count += 1
                logger.info(
                    "Stored content",
                    content_id=content_id,
                    url=content["url"]
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    "Failed to store content",
                    url=content.get("url"),
                    error=str(e)
                )
        
        return {
            "stored": stored_count,
            "failed": failed_count,
            "total": len(results["results"])
        }

async def main():
    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    )
    
    try:
        logger.info("Starting data ingestion")
        
        async with DataIngestion() as ingestion:
            # Get latest results
            results = await ingestion.get_latest_crawl_results()
            
            # Process results
            stats = await ingestion.process_results(results)
            
            logger.info(
                "Data ingestion completed",
                stored=stats["stored"],
                failed=stats["failed"],
                total=stats["total"]
            )
            
            # Print summary
            print("\nIngestion Summary:")
            print(f"Total Documents: {stats['total']}")
            print(f"Successfully Stored: {stats['stored']}")
            print(f"Failed: {stats['failed']}")
        
    except Exception as e:
        logger.error("Data ingestion failed", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main()) 