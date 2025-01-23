from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from src.scraper.crawler import WebCrawler
from src.storage.elasticsearch import ElasticsearchClient
from src.storage.postgresql import PostgresClient
from src.config import settings

router = APIRouter()
es_client = ElasticsearchClient()
pg_client = PostgresClient()

@router.post("/start")
async def start_migration(
    background_tasks: BackgroundTasks,
    start_url: str
):
    """Start content migration"""
    if not start_url.startswith(settings.TARGET_DOMAIN):
        raise HTTPException(
            status_code=400,
            detail=f"URL must be within domain: {settings.TARGET_DOMAIN}"
        )
    
    crawler = WebCrawler()
    background_tasks.add_task(crawler.crawl, start_url)
    
    return {"message": "Migration started", "start_url": start_url}

@router.get("/status")
async def get_migration_status():
    """Get migration status statistics"""
    try:
        stats = await pg_client.get_migration_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry/{content_id}")
async def retry_migration(content_id: str):
    """Retry migration for specific content"""
    content = await es_client.get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    await pg_client.update_migration_status(
        content_id=content_id,
        url=content["url"],
        status="pending"
    )
    
    return {"message": "Migration retry queued", "content_id": content_id} 