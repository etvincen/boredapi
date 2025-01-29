from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from elasticsearch import Elasticsearch
from src.config import settings

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
    size: int = Query(10, ge=1, le=100, description="Number of results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    min_length: Optional[int] = Query(None, ge=0, description="Minimum content length"),
    content_type: Optional[str] = Query(None, description="Filter by content type")
) -> Dict[str, Any]:
    """
    Search content with various filters
    """
    try:
        es = get_es_client()
        
        # Build query
        must_conditions = [
            {"multi_match": {
                "query": q,
                "fields": ["title^2", "content", "meta_tags.description"]
            }}
        ]
        
        if min_length:
            must_conditions.append({
                "range": {
                    "content_stats.text_length": {
                        "gte": min_length
                    }
                }
            })
            
        if content_type:
            must_conditions.append({
                "term": {
                    "metadata.content_type": content_type
                }
            })
        
        # Execute search
        result = es.search(
            index="roc_eclerc_content",
            body={
                "query": {"bool": {"must": must_conditions}},
                "from": (page - 1) * size,
                "size": size,
                "highlight": {
                    "fields": {
                        "content": {},
                        "title": {}
                    }
                },
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
                    }
                }
            }
        )
        
        return {
            "total": result["hits"]["total"]["value"],
            "page": page,
            "size": size,
            "results": [
                {
                    "id": hit["_id"],
                    "title": hit["_source"]["title"],
                    "url": hit["_source"]["url"],
                    "highlights": hit.get("highlight", {}),
                    "content_stats": hit["_source"].get("content_stats", {}),
                    "metadata": hit["_source"].get("metadata", {})
                }
                for hit in result["hits"]["hits"]
            ],
            "aggregations": {
                "content_types": result["aggregations"]["content_types"]["buckets"],
                "avg_content_length": result["aggregations"]["avg_content_length"]["value"]
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