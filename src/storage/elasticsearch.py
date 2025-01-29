from elasticsearch import AsyncElasticsearch
from typing import Dict, Any, List, Optional
import structlog
from src.config import settings

logger = structlog.get_logger()

class ElasticsearchClient:
    def __init__(self):
        auth = None
        if settings.elasticsearch.USERNAME:
            auth = (settings.elasticsearch.USERNAME, settings.elasticsearch.PASSWORD)
            
        self.client = AsyncElasticsearch(
            hosts=[f"http://{settings.elasticsearch.HOST}:{settings.elasticsearch.PORT}"],
            basic_auth=auth
        )
        self.index = "content"
        
    async def init_indices(self):
        """Initialize Elasticsearch indices with proper mappings"""
        if not await self.client.indices.exists(index=self.index):
            await self.client.indices.create(
                index=self.index,
                body={
                    "mappings": {
                        "properties": {
                            "url": {"type": "keyword"},
                            "title": {"type": "text"},
                            "content": {"type": "text"},
                            "type": {"type": "keyword"},
                            "hierarchy": {
                                "properties": {
                                    "level": {"type": "integer"},
                                    "parent_id": {"type": "keyword"},
                                    "breadcrumb": {"type": "keyword"}
                                }
                            },
                            "metadata": {
                                "properties": {
                                    "word_count": {"type": "integer"},
                                    "last_updated": {"type": "date"},
                                    "status": {"type": "keyword"}
                                }
                            },
                            "media": {
                                "properties": {
                                    "type": {"type": "keyword"},
                                    "url": {"type": "keyword"},
                                    "metadata": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            )
            logger.info("Created Elasticsearch index", index=self.index)
    
    async def store_content(self, content: Dict[str, Any]) -> str:
        """Store content and return document ID"""
        result = await self.client.index(
            index=self.index,
            document=content
        )
        return result["_id"]
    
    async def search_content(
        self, 
        query: str, 
        content_type: Optional[str] = None,
        page: int = 1, 
        size: int = 10
    ) -> Dict[str, Any]:
        """Search content with pagination"""
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"multi_match": {
                            "query": query,
                            "fields": ["title^2", "content"]
                        }}
                    ]
                }
            },
            "from": (page - 1) * size,
            "size": size
        }
        
        if content_type:
            body["query"]["bool"]["must"].append(
                {"term": {"type": content_type}}
            )
        
        results = await self.client.search(
            index=self.index,
            body=body
        )
        
        return {
            "total": results["hits"]["total"]["value"],
            "items": [hit["_source"] for hit in results["hits"]["hits"]]
        }
    
    async def get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve content by ID"""
        try:
            result = await self.client.get(
                index=self.index,
                id=content_id
            )
            return result["_source"]
        except:
            return None
    
    async def close(self):
        """Close the Elasticsearch client"""
        await self.client.close() 