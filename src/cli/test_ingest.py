import logging
import json
from pathlib import Path
import os
from elasticsearch import Elasticsearch
from src.config import settings
from src.elasticsearch.indexer import ContentIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test ingestion with embeddings"""
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
        # First, create a snapshot of current index
        logger.info("Creating backup of current index...")
        backup_index = "roc_eclerc_content_backup"
        
        # Check if backup exists and delete if it does
        if es.indices.exists(index=backup_index):
            es.indices.delete(index=backup_index)
            
        # Reindex current data to backup
        es.reindex(
            body={
                "source": {"index": "roc_eclerc_content"},
                "dest": {"index": backup_index}
            }
        )
        logger.info(f"Backup created in index: {backup_index}")
        
        # Initialize indexer
        indexer = ContentIndexer(es)
        
        # Get latest transformed file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        transformed_dir = base_dir / "transformed_results"
        files = list(transformed_dir.glob("transformed_*.json"))
        if not files:
            logger.error("No transformed files found!")
            return
            
        latest_file = max(files)
        logger.info(f"Using latest transformed file: {latest_file}")
        
        # Load and process a sample of documents
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            pages = data.get('pages', [])[:5]  # Test with 5 documents first
            
        if not pages:
            logger.error("No pages found in the transformed results!")
            return
            
        logger.info(f"Testing ingestion with {len(pages)} documents...")
        
        # Index the documents
        results = indexer.index_pages(pages)
        
        logger.info("\nIngestion Results:")
        logger.info("-" * 50)
        logger.info(f"Total documents: {results['total_pages']}")
        logger.info(f"Successfully indexed: {results['indexed']}")
        logger.info(f"Failed: {results['failed']}")
        
        # Validate embeddings
        response = es.search(
            index="roc_eclerc_content",
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
        
        docs_with_embeddings = response['aggregations']['has_embedding']['doc_count']
        logger.info(f"Documents with embeddings: {docs_with_embeddings}")
        
        # Test a sample search
        logger.info("\nTesting vector search...")
        test_query = "Comment préparer ses obsèques ?"
        
        search_response = es.search(
            index="roc_eclerc_content",
            body={
                "size": 3,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                            "params": {"query_vector": indexer.embeddings_generator.generate_query_embedding(test_query)}
                        }
                    }
                }
            }
        )
        
        logger.info(f"\nTest search results for: {test_query}")
        logger.info("-" * 50)
        for hit in search_response['hits']['hits']:
            logger.info(f"\nTitle: {hit['_source']['title']}")
            logger.info(f"Score: {hit['_score']:.3f}")
            
        logger.info("\nNext steps:")
        logger.info("1. Review the results above")
        logger.info("2. If everything looks good, run the full ingest_data.py script")
        logger.info("3. If issues occur, restore from backup using:")
        logger.info("   - Delete current index")
        logger.info("   - Reindex from roc_eclerc_content_backup")
        
    except Exception as e:
        logger.error(f"Error during test ingestion: {str(e)}")
        raise
        
if __name__ == '__main__':
    main() 