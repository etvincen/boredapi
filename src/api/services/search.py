from elasticsearch import Elasticsearch
from typing import Dict, Any, List, Literal
import logging
import time
from ...nlp.embeddings import EmbeddingsGenerator

logger = logging.getLogger(__name__)

SearchMode = Literal["hybrid", "semantic", "keyword"]

class SearchService:
    def __init__(self, es_client: Elasticsearch, index_name: str):
        self.es = es_client
        self.index_name = index_name
        self.embeddings_generator = EmbeddingsGenerator()
        
    def hybrid_search(
        self,
        query: str,
        size: int = 5,
        min_score: float = None,
        include_stats: bool = False
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining BM25 and vector similarity
        
        Args:
            query: Search query text
            size: Number of results to return
            min_score: Minimum score threshold for results
            include_stats: Whether to include document statistics
            
        Returns:
            List of search results with scores
        """
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding = self.embeddings_generator.generate_query_embedding(query)
            
            # Construct hybrid query
            search_query = {
                "size": size,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "title^2",
                                        "raw_text",
                                        "preprocessed_keywords^1.5"
                                    ],
                                    "type": "best_fields",
                                    "analyzer": "french_exact"
                                }
                            }
                        ],
                        "should": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["url", "title", "raw_text"] + (["statistics"] if include_stats else [])
            }
            
            if min_score:
                search_query["min_score"] = min_score
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_query
            )
            
            # Calculate time taken
            took_ms = (time.time() - start_time) * 1000
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'url': hit['_source']['url'],
                    'title': hit['_source']['title'],
                    'score': hit['_score'],
                    'text_preview': hit['_source']['raw_text'][:200] + '...',  # Short preview
                    'took_ms': took_ms
                }
                
                if include_stats and 'statistics' in hit['_source']:
                    result['statistics'] = hit['_source']['statistics']
                    
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {str(e)}")
            raise

    def semantic_search(
        self,
        query: str,
        size: int = 5,
        min_score: float = None,
        include_stats: bool = False
    ) -> List[Dict[str, Any]]:
        """Perform pure semantic search using vector similarity
        
        Args:
            query: Search query text
            size: Number of results to return
            min_score: Minimum score threshold for results
            include_stats: Whether to include document statistics
            
        Returns:
            List of search results with scores
        """
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding = self.embeddings_generator.generate_query_embedding(query)
            
            # Construct semantic-only query
            search_query = {
                "size": size,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                            "params": {"query_vector": query_embedding}
                        }
                    }
                },
                "_source": ["url", "title", "raw_text"] + (["statistics"] if include_stats else [])
            }
            
            if min_score:
                search_query["min_score"] = min_score
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_query
            )
            
            # Calculate time taken
            took_ms = (time.time() - start_time) * 1000
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'url': hit['_source']['url'],
                    'title': hit['_source']['title'],
                    'score': hit['_score'],
                    'text_preview': hit['_source']['raw_text'][:200] + '...',  # Short preview
                    'took_ms': took_ms
                }
                
                if include_stats and 'statistics' in hit['_source']:
                    result['statistics'] = hit['_source']['statistics']
                    
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            raise

    def search(
        self,
        query: str,
        mode: SearchMode = "hybrid",
        size: int = 5,
        min_score: float = None,
        include_stats: bool = False
    ) -> List[Dict[str, Any]]:
        """Unified search function with configurable mode
        
        Args:
            query: Search query text
            mode: Search mode ("hybrid", "semantic", or "keyword")
            size: Number of results to return
            min_score: Minimum score threshold for results
            include_stats: Whether to include document statistics
            
        Returns:
            List of search results with scores
        """
        if mode == "semantic":
            return self.semantic_search(query, size, min_score, include_stats)
        elif mode == "hybrid":
            return self.hybrid_search(query, size, min_score, include_stats)
        elif mode == "keyword":
            return self._keyword_search(query, size, min_score, include_stats)
        else:
            raise ValueError(f"Invalid search mode: {mode}")
            
    def _keyword_search(
        self,
        query: str,
        size: int = 5,
        min_score: float = None,
        include_stats: bool = False
    ) -> List[Dict[str, Any]]:
        """Perform keyword-only search using BM25
        
        Args:
            query: Search query text
            size: Number of results to return
            min_score: Minimum score threshold for results
            include_stats: Whether to include document statistics
            
        Returns:
            List of search results with scores
        """
        try:
            start_time = time.time()
            
            # Construct keyword-only query
            search_query = {
                "size": size,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^2",
                            "raw_text",
                            "preprocessed_keywords^1.5"
                        ],
                        "type": "best_fields",
                        "analyzer": "french_exact"
                    }
                },
                "_source": ["url", "title", "raw_text"] + (["statistics"] if include_stats else [])
            }
            
            if min_score:
                search_query["min_score"] = min_score
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_query
            )
            
            # Calculate time taken
            took_ms = (time.time() - start_time) * 1000
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'url': hit['_source']['url'],
                    'title': hit['_source']['title'],
                    'score': hit['_score'],
                    'text_preview': hit['_source']['raw_text'][:200] + '...',  # Short preview
                    'took_ms': took_ms
                }
                
                if include_stats and 'statistics' in hit['_source']:
                    result['statistics'] = hit['_source']['statistics']
                    
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error performing keyword search: {str(e)}")
            raise