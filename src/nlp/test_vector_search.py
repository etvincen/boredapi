import logging
from elasticsearch import Elasticsearch
from src.config import settings
from src.elasticsearch.test_indexer import TestContentIndexer, test_vector_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test vector search pipeline"""
    # Initialize Elasticsearch client
    es = Elasticsearch([
        {
            'host': settings.elasticsearch.HOST,
            'port': settings.elasticsearch.PORT,
            'scheme': 'https' if settings.elasticsearch.USE_SSL else 'http'
        }
    ], basic_auth=(
        settings.elasticsearch.USERNAME,
        settings.elasticsearch.PASSWORD
    ) if settings.elasticsearch.USERNAME else None)
    
    try:
        # Get documents from main index
        response = es.search(
            index="roc_eclerc_content",
            body={
                "size": 5,
                "query": {"match_all": {}},
                "_source": ["url", "title", "raw_text", "statistics"]
            }
        )
        
        docs = [hit['_source'] for hit in response['hits']['hits']]
        
        # Initialize test indexer
        test_indexer = TestContentIndexer(es)
        
        # Index sample documents with embeddings
        logger.info("Indexing sample documents with embeddings...")
        results = test_indexer.index_sample_documents(docs)
        
        logger.info("\nIndexing Results:")
        logger.info("-" * 50)
        logger.info(f"Total documents: {results['total']}")
        logger.info(f"Successfully indexed: {results['indexed']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Documents with embeddings: {results['with_embeddings']}")
        
        # Test vector search with different queries
        test_queries = [
            "Comment préparer ses obsèques ?",
            "Je veux envoyer des fleurs pour un décès",
            "Quels sont les différents types de devis ?"
        ]
        
        for query in test_queries:
            test_vector_search(es, query)
            
    except Exception as e:
        logger.error(f"Error testing vector search pipeline: {str(e)}")
        raise
        
if __name__ == '__main__':
    main() 