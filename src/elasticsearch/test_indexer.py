from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import Dict, Any, List, Generator
import logging
from datetime import datetime
from .mappings import get_elasticsearch_mappings
import time
from tqdm import tqdm
from ..nlp.preprocessor import TextPreprocessor
from ..nlp.embeddings import EmbeddingsGenerator

logger = logging.getLogger(__name__)

class TestContentIndexer:
    """Test version of ContentIndexer that includes embeddings"""
    
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.index_name = "test_roc_eclerc_content_v1"  # Use test index
        self.batch_size = 5  # Smaller batch size for testing
        self.preprocessor = TextPreprocessor()
        self.embeddings_generator = EmbeddingsGenerator()
        
    def create_index(self, force_recreate: bool = False) -> None:
        """Create the test Elasticsearch index with vector search enabled"""
        try:
            exists = self.es.indices.exists(index=self.index_name)
            
            if exists and not force_recreate:
                logger.info(f"Test index {self.index_name} already exists")
                return
                
            if exists:
                logger.info(f"Deleting existing test index {self.index_name}")
                self.es.indices.delete(index=self.index_name)
                time.sleep(1)
            
            # Create new index with vector search enabled
            settings = get_elasticsearch_mappings()
            self.es.indices.create(index=self.index_name, body=settings)
            logger.info(f"Created fresh test index {self.index_name}")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error creating test index: {str(e)}")
            raise
            
    def prepare_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a document for indexing with embeddings"""
        # First get the standard prepared document
        prepared_doc = {
            'url': doc.get('url', ''),
            'title': doc.get('title', ''),
            'raw_text': doc.get('raw_text', ''),
            'preprocessed_keywords': self.preprocessor.process_document(doc)['lemmatized_tokens'],
            'statistics': doc.get('statistics', {})
        }
        
        # Generate and add embedding
        try:
            embedding = self.embeddings_generator.generate_document_embedding(prepared_doc)
            if embedding:
                prepared_doc['text_embedding'] = embedding
                logger.debug(f"Generated embedding for document: {prepared_doc['title']}")
        except Exception as e:
            logger.error(f"Error generating embedding for document: {str(e)}")
            # If embedding fails, we'll still index the document without it
            
        return prepared_doc
        
    def index_sample_documents(self, documents: List[Dict[str, Any]], sample_size: int = 5) -> Dict[str, int]:
        """Index a sample of documents with embeddings"""
        if not documents:
            return {'total': 0, 'indexed': 0, 'failed': 0}
            
        # Take a sample
        sample_docs = documents[:sample_size]
        logger.info(f"Testing indexing with {len(sample_docs)} documents")
        
        try:
            # Always recreate the test index
            self.create_index(force_recreate=True)
            
            # Prepare and index documents
            indexed = 0
            failed = 0
            
            with tqdm(total=len(sample_docs), desc="Indexing test documents") as pbar:
                for doc in sample_docs:
                    try:
                        prepared_doc = self.prepare_document(doc)
                        response = self.es.index(
                            index=self.index_name,
                            id=prepared_doc['url'],
                            document=prepared_doc,
                            refresh=True
                        )
                        
                        if response['result'] in ['created', 'updated']:
                            indexed += 1
                        else:
                            failed += 1
                            logger.error(f"Failed to index document: {response}")
                            
                    except Exception as e:
                        logger.error(f"Error indexing document: {str(e)}")
                        failed += 1
                        
                    pbar.update(1)
                    
            # Final refresh
            self.es.indices.refresh(index=self.index_name)
            
            # Get some stats about the embeddings
            stats = self.es.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "has_embedding": {
                            "filter": {
                                "exists": {
                                    "field": "text_embedding"
                                }
                            }
                        }
                    }
                }
            )
            
            docs_with_embeddings = stats['aggregations']['has_embedding']['doc_count']
            
            return {
                'total': len(sample_docs),
                'indexed': indexed,
                'failed': failed,
                'with_embeddings': docs_with_embeddings
            }
            
        except Exception as e:
            logger.error(f"Error during test indexing: {str(e)}")
            raise
            
def test_vector_search(es_client: Elasticsearch, query: str = "Comment préparer ses obsèques ?") -> None:
    """Test vector search functionality"""
    try:
        embeddings_generator = EmbeddingsGenerator()
        query_embedding = embeddings_generator.generate_query_embedding(query)
        
        response = es_client.search(
            index="test_roc_eclerc_content_v1",
            body={
                "size": 3,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                            "params": {"query_vector": query_embedding}
                        }
                    }
                }
            }
        )
        
        logger.info(f"\nTest search results for query: {query}")
        logger.info("-" * 50)
        
        for hit in response['hits']['hits']:
            logger.info(f"\nTitle: {hit['_source']['title']}")
            logger.info(f"Score: {hit['_score']:.3f}")
            logger.info(f"Preview: {hit['_source']['raw_text'][:200]}...")
            
    except Exception as e:
        logger.error(f"Error testing vector search: {str(e)}")
        raise 