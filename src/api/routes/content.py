from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List, Literal
from elasticsearch import Elasticsearch
from src.config import settings
from src.api.services.search import SearchService, SearchMode

router = APIRouter()

def get_es_client() -> Elasticsearch:
    """Get Elasticsearch client"""
    return Elasticsearch([
        {
            'host': settings.elasticsearch.HOST,
            'port': settings.elasticsearch.PORT,
            'scheme': 'https' if settings.elasticsearch.USE_SSL else 'http'
        }
    ], basic_auth=(
        settings.elasticsearch.USERNAME,
        settings.elasticsearch.PASSWORD
    ) if settings.elasticsearch.USERNAME else None)

@router.get("/content/search")
async def search_content(
    q: str = Query(..., description="Search query"),
    mode: SearchMode = Query("hybrid", description="Search mode: hybrid, semantic, or keyword"),
    size: int = Query(10, ge=1, le=100, description="Number of results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    min_length: Optional[int] = Query(None, ge=0, description="Minimum content length"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    include_stats: bool = Query(False, description="Include content statistics in results")
) -> Dict[str, Any]:
    """
    Search content with various filters and configurable search mode
    """
    try:
        es = get_es_client()
        search_service = SearchService(es, "roc_eclerc_content")
        
        # Calculate offset for pagination
        from_idx = (page - 1) * size
        
        # Perform search with selected mode
        results = search_service.search(
            query=q,
            mode=mode,
            size=size,
            include_stats=include_stats
        )
        
        # Apply additional filters if needed
        if min_length or content_type:
            results = [
                r for r in results
                if (not min_length or len(r.get('text_preview', '')) >= min_length)
                and (not content_type or r.get('content_type') == content_type)
            ]
        
        # Paginate results
        paginated_results = results[from_idx:from_idx + size]
        
        return {
            "total": len(results),
            "page": page,
            "size": size,
            "search_mode": mode,
            "results": paginated_results,
            "performance": {
                "took_ms": paginated_results[0]['took_ms'] if paginated_results else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/{content_id}")
async def get_content(content_id: str) -> Dict[str, Any]:
    """
    Get a specific content by ID (URL)
    """
    try:
        es = get_es_client()
        result = es.get(index="roc_eclerc_content", id=content_id)
        return result["_source"]
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Content not found: {str(e)}"
        )

@router.get("/content/stats")
async def get_content_stats() -> Dict[str, Any]:
    """
    Get overall content statistics
    """
    try:
        es = get_es_client()
        
        result = es.search(
            index="roc_eclerc_content",
            body={
                "size": 0,
                "aggs": {
                    "content_types": {
                        "terms": {
                            "field": "metadata.content_type"
                        }
                    },
                    "avg_content_length": {
                        "avg": {
                            "field": "content_stats.text_length"
                        }
                    },
                    "avg_images": {
                        "avg": {
                            "field": "content_stats.image_count"
                        }
                    },
                    "content_length_distribution": {
                        "histogram": {
                            "field": "content_stats.text_length",
                            "interval": 1000
                        }
                    }
                }
            }
        )
        
        return {
            "total_documents": result["hits"]["total"]["value"],
            "aggregations": result["aggregations"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 