from fastapi import APIRouter, HTTPException
from src.storage.elasticsearch import ElasticsearchClient
from src.storage.postgresql import PostgresClient

router = APIRouter()
es_client = ElasticsearchClient()
pg_client = PostgresClient()

@router.get("/health")
async def health_check():
    """Check system health"""
    try:
        # Check Elasticsearch
        es_health = await es_client.client.cluster.health()
        
        # Check PostgreSQL
        async with pg_client.pool.acquire() as conn:
            pg_health = await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "elasticsearch": es_health["status"],
            "postgresql": "connected" if pg_health == 1 else "error"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"System unhealthy: {str(e)}"
        ) 