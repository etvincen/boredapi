import json
from pathlib import Path
import logging
from elasticsearch import Elasticsearch
from typing import Optional, Dict, Any
import os
from datetime import datetime
from ..elasticsearch.indexer import ContentIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_latest_crawl_results() -> Optional[Path]:
    """Find the most recent crawl results file"""
    crawl_dir = Path('crawl_results')
    if not crawl_dir.exists():
        logger.error("Crawl results directory not found")
        return None
        
    result_files = list(crawl_dir.glob('crawl_results_*.json'))
    if not result_files:
        logger.error("No crawl result files found")
        return None
        
    # Sort by modification time
    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Found latest crawl results: {latest_file}")
    return latest_file

def load_crawl_results(file_path: Path) -> Dict[str, Any]:
    """Load crawl results from JSON file"""
    try:
        with file_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading crawl results: {str(e)}")
        raise

def get_elasticsearch_client() -> Elasticsearch:
    """Get Elasticsearch client from environment variables"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
    es_port = os.getenv('ELASTICSEARCH_PORT', '9200')
    es_user = os.getenv('ELASTICSEARCH_USER')
    es_pass = os.getenv('ELASTICSEARCH_PASSWORD')
    
    if es_user and es_pass:
        return Elasticsearch(
            [f"http://{es_host}:{es_port}"],
            basic_auth=(es_user, es_pass)
        )
    else:
        return Elasticsearch([f"http://{es_host}:{es_port}"])

def main():
    try:
        # Find latest crawl results
        latest_crawl = find_latest_crawl_results()
        if not latest_crawl:
            logger.error("No crawl results found")
            return
            
        logger.info(f"Found latest crawl results: {latest_crawl}")
        
        # Load crawl results
        logger.info("Loading crawl results...")
        crawl_data = load_crawl_results(latest_crawl)
        
        # Index pages
        logger.info(f"Indexing {len(crawl_data['results'])} pages...")
        indexer = ContentIndexer(get_elasticsearch_client())
        result = indexer.index_pages(crawl_data['results'])
        
        logger.info("\n=== Indexing Complete ===")
        logger.info(f"Total pages: {result['total_pages']}")
        logger.info(f"Successfully indexed: {result['indexed']}")
        logger.info(f"Failed: {result['failed']}")
        
        # Get index stats
        index_stats = indexer.es.indices.stats(index=indexer.index_name)
        doc_count = indexer.es.count(index=indexer.index_name)
        
        logger.info("\n=== Index Statistics ===")
        logger.info(f"Documents in index: {doc_count['count']}")
        logger.info(f"Index size: {index_stats['indices'][indexer.index_name]['total']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise

if __name__ == "__main__":
    main() 