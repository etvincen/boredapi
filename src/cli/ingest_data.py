import asyncio
import structlog
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, List
from src.storage.elasticsearch import ElasticsearchClient
from src.storage.postgresql import PostgresClient

logger = structlog.get_logger()

class DataIngestion:
    def __init__(self):
        self.es_client = ElasticsearchClient()
        self.pg_client = PostgresClient()
        
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
            
            # Store metadata in PostgreSQL
            await self.pg_client.update_migration_status(
                content_id=content_id,
                url=content["url"],
                status="completed"
            )
            
            # If content has hierarchy information, store it
            if "hierarchy" in content:
                await self.pg_client.store_hierarchy(
                    content_id=content_id,
                    parent_id=content["hierarchy"].get("parent_id"),
                    level=content["hierarchy"].get("level", 0),
                    path=content["hierarchy"].get("path", [])
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
        
        ingestion = DataIngestion()
        
        # Initialize storage
        logger.info("Initializing storage")
        await ingestion.init_storage()
        
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
    finally:
        # Close connections
        await ingestion.es_client.close()
        await ingestion.pg_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 