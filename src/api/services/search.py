from elasticsearch import Elasticsearch
from typing import Dict, Any, List
import logging
from ...nlp.embeddings import EmbeddingsGenerator

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, es_client: Elasticsearch, index_name: str):
        self.es = es_client
        self.index_name = index_name
        self.embeddings_generator = EmbeddingsGenerator()
        
    def hybrid_search(self, query: str, size: int = 5) -> List[Dict[str, Any]]:
        """Perform hybrid search combining BM25 and vector similarity
        
        Args:
            query: Search query text
            size: Number of results to return
            
        Returns:
            List of search results with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings_generator.generate_query_embedding(query)
            
            # Construct hybrid query
            search_query = {
                "size": size,
                "query": {
                    "combined_fields": {
                        "query": query,
                        "fields": ["title^2", "raw_text"]
                    }
                },
                "knn": {
                    "field": "text_embedding",
                    "query_vector": query_embedding,
                    "k": size,
                    "num_candidates": size * 2
                },
                "rank": {
                    "rrf": {
                        "window_size": size,
                        "rank_constant": 20
                    }
                }
            }
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_query
            )
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'url': hit['_source']['url'],
                    'title': hit['_source']['title'],
                    'score': hit['_score'],
                    'text_preview': hit['_source']['raw_text'][:200] + '...'  # Short preview
                }
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {str(e)}")
            raise