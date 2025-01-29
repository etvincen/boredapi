from fastapi import APIRouter
from elasticsearch import Elasticsearch
from src.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Check health of all services"""
    # Initialize clients
    es = Elasticsearch([f"http://{settings.elasticsearch.HOST}:{settings.elasticsearch.PORT}"])
    
    # Check Elasticsearch
    es_health = 1 if es.ping() else 0
    
    return {
        "status": "ok" if all([es_health]) else "error",
        "services": {
            "elasticsearch": "connected" if es_health else "error"
        }
    } 