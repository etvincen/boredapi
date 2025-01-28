from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from src.storage.elasticsearch import ElasticsearchClient
from src.config import settings
from elasticsearch import Elasticsearch

router = APIRouter()
es_client = ElasticsearchClient()

@router.get("/search")
async def search_content(
    query: str,
    content_type: Optional[str] = None,
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100)
):
    """Search content with pagination"""
    try:
        results = await es_client.search_content(
            query=query,
            content_type=content_type,
            page=page,
            size=size
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/{content_id}")
async def get_content(content_id: str):
    """Get content by ID"""
    try:
        es = Elasticsearch([f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"])
        result = es.get(index="roc_eclerc_content", id=content_id)
        return result["_source"]
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Content not found: {str(e)}"
        ) 