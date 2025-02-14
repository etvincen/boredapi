from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel
from src.config import settings
from src.api.services.search import SearchService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Roc Eclerc Search API",
    description="API for hybrid search (BM25 + vector similarity) over Roc Eclerc content",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class SearchResult(BaseModel):
    url: str
    title: str
    score: float
    text_preview: str
    statistics: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    total_results: int
    took_ms: float
    results: List[SearchResult]
    facets: Optional[Dict[str, Any]] = None

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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        es = get_es_client()
        health = es.cluster.health()
        return {
            "status": "healthy",
            "elasticsearch": health["status"]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    size: int = Query(10, ge=1, le=50, description="Number of results"),
    min_score: Optional[float] = Query(None, ge=0, description="Minimum score threshold"),
    include_stats: bool = Query(False, description="Include document statistics in results")
) -> SearchResponse:
    """
    Perform hybrid search over the content
    
    This endpoint combines traditional keyword search (BM25) with semantic search using
    sentence embeddings. The results are ranked using a combination of both signals.
    """
    try:
        es = get_es_client()
        search_service = SearchService(es, "roc_eclerc_content")
        
        # Perform hybrid search
        results = search_service.hybrid_search(
            query=q,
            size=size,
            min_score=min_score,
            include_stats=include_stats
        )
        
        # Transform to response model
        search_results = []
        for result in results:
            search_result = SearchResult(
                url=result['url'],
                title=result['title'],
                score=result['score'],
                text_preview=result['text_preview']
            )
            if include_stats and 'statistics' in result:
                search_result.statistics = result['statistics']
            search_results.append(search_result)
            
        return SearchResponse(
            total_results=len(search_results),
            took_ms=results[0].get('took_ms', 0) if results else 0,
            results=search_results
        )
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggest")
async def suggest(
    q: str = Query(..., description="Partial query to get suggestions for"),
    size: int = Query(5, ge=1, le=10, description="Number of suggestions")
) -> List[str]:
    """Get search suggestions based on partial input"""
    try:
        es = get_es_client()
        response = es.search(
            index="roc_eclerc_content",
            body={
                "size": 0,
                "suggest": {
                    "title_suggest": {
                        "prefix": q,
                        "completion": {
                            "field": "title",
                            "size": size,
                            "skip_duplicates": True
                        }
                    }
                }
            }
        )
        
        suggestions = [
            option['text']
            for suggestion in response['suggest']['title_suggest']
            for option in suggestion['options']
        ]
        
        return suggestions[:size]
        
    except Exception as e:
        logger.error(f"Suggestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 