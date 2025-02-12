import json
from pathlib import Path
import logging
from elasticsearch import Elasticsearch
from typing import Optional, Dict, Any
import os
from datetime import datetime
from ..elasticsearch.indexer import ContentIndexer
from ..utils.parse_data import transform_content
from ..nlp.processor import NLPProcessor
from tqdm import tqdm

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
        pages = data.get('results', [])
        logger.info(f"Loaded {len(pages)} pages")
        return data
    except Exception as e:
        logger.error(f"Error loading crawl results: {str(e)}")
        raise

def get_elasticsearch_client() -> Elasticsearch:
    """Get Elasticsearch client from environment variables"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
    es_port = os.getenv('ELASTICSEARCH_PORT', '9200')
    
    return Elasticsearch(
        [f"http://{es_host}:{es_port}"],
        basic_auth=("elastic", "elastic123")
    )

def save_transformed_results(transformed_data: Dict[str, Any], nlp_data: Dict[str, Any]) -> Path:
    """Save transformed results to file in the correct data directory"""
    # Get the data directory from environment or use default
    data_root = Path(os.getenv('DEV_DATA_PATH', '../data'))
    
    # Create the transformed_results directory inside the data directory
    output_path = data_root / 'transformed_results'
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Also create a local transformed_results directory for easy access
    local_output = Path('transformed_results')
    local_output.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'transformed_{timestamp}.json'
    
    # Combine transformed data with NLP data
    output_data = {
        **transformed_data,
        'nlp_stats': nlp_data
    }
    
    # Save to both locations
    output_file = output_path / filename
    local_file = local_output / filename
    
    # Save the file in both locations
    for file_path in [output_file, local_file]:
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nTransformed results saved to:")
    logger.info(f"- Docker volume: {output_file}")
    logger.info(f"- Local directory: {local_file}")
    
    return output_file

def main():
    try:
        print("\n=== Starting Content Processing Pipeline ===")
        
        # Find and load crawl results
        latest_crawl = find_latest_crawl_results()
        if not latest_crawl:
            logger.error("No crawl results found")
            return
        
        crawl_data = load_crawl_results(latest_crawl)
        
        # Take only 40 documents
        crawl_data['results'] = crawl_data['results'][:40]
        print(f"\nSelected {len(crawl_data['results'])} documents for processing")
        
        # Transform content
        print("\n1. Transforming HTML Content")
        transformed_data = transform_content(crawl_data)
        total_pages = len(transformed_data.get('pages', []))
        print(f"Transformed {total_pages} pages")
        
        # Process with NLP
        print("\n2. Running NLP Processing")
        nlp_processor = NLPProcessor()
        
        # Process all pages with progress bar
        pages = transformed_data['pages']
        processed_docs = []
        
        for page in tqdm(pages, desc="Processing documents", unit="doc"):
            try:
                processed_doc, _ = nlp_processor.process_documents([page])
                if processed_doc:
                    processed_docs.extend(processed_doc)
            except Exception as e:
                logger.error(f"Error processing document {page.get('url', 'unknown')}: {str(e)}")
        
        # Calculate corpus stats at the end
        _, corpus_stats = nlp_processor.process_documents(pages)  # Use all pages for corpus stats
        
        print(f"\nSuccessfully processed {len(processed_docs)} documents")
        
        # Save results
        print("\n3. Saving Transformed Results")
        transformed_data['pages'] = processed_docs
        transformed_file = save_transformed_results(transformed_data, corpus_stats)
        
        # Index pages
        print("\n4. Indexing in Elasticsearch")
        indexer = ContentIndexer(get_elasticsearch_client())
        result = indexer.index_pages(processed_docs)
        
        print("\n=== Processing Complete ===")
        print(f"Total pages processed: {result['total_pages']}")
        print(f"Successfully indexed: {result['indexed']}")
        print(f"Failed: {result['failed']}")
        
        # Get index stats
        try:
            stats = indexer.get_index_stats()
            print(f"\nIndex Statistics:")
            print(f"Documents in index: {stats['doc_count']}")
            print(f"Index size: {stats['store_size'] / 1024 / 1024:.2f} MB")
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise

if __name__ == "__main__":
    main() 