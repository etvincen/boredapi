from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import Dict, Any, List, Generator
import logging
from datetime import datetime
from .mappings import get_index_settings, get_index_name
import time
from tqdm import tqdm

logger = logging.getLogger(__name__)

class ContentIndexer:
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.index_name = get_index_name()
        self.batch_size = 10
        
    def create_index(self, force_recreate: bool = False) -> None:
        """Create the Elasticsearch index with proper mappings
        
        Args:
            force_recreate: If True, delete existing index and create new one
        """
        try:
            exists = self.es.indices.exists(index=self.index_name)
            
            if exists and not force_recreate:
                logger.info(f"Index {self.index_name} already exists")
                return
                
            if exists:
                logger.info(f"Deleting existing index {self.index_name}")
                self.es.indices.delete(index=self.index_name)
                time.sleep(1)  # Brief pause after deletion
            
            # Create new index
            settings = get_index_settings()
            self.es.indices.create(index=self.index_name, body=settings)
            logger.info(f"Created fresh index {self.index_name}")
            time.sleep(1)  # Brief pause after creation
            
            # Wait for index to be ready
            for _ in range(3):  # Try up to 3 times
                if self.es.indices.exists(index=self.index_name):
                    break
                time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise
            
    def generate_bulk_actions(self, documents: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """Generate actions for bulk indexing"""
        for doc in documents:
            yield {
                "_index": self.index_name,
                "_id": doc['url'],  # Use URL as document ID
                "_source": doc
            }
            
    def index_pages(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Index a list of documents"""
        if not documents:
            return {'total_pages': 0, 'indexed': 0, 'failed': 0}
        
        try:
            # Always recreate the index for consistency
            self.create_index(force_recreate=True)
        
            # Prepare bulk indexing operations
            operations = []
            for doc in documents:
                try:
                    # Each operation needs both the action and source lines
                    operations.append({"index": {"_index": self.index_name, "_id": doc['url']}})
                    operations.append(doc)
                except Exception as e:
                    logger.error(f"Error preparing document for indexing: {str(e)}")
            
            # Perform bulk indexing with progress bar
            total_docs = len(documents)
            indexed = 0
            failed = 0
            
            if operations:
                try:
                    with tqdm(total=total_docs, desc="Indexing documents", unit="doc") as pbar:
                        for i in range(0, len(operations), self.batch_size * 2):  # *2 because each doc has 2 lines
                            batch = operations[i:i + self.batch_size * 2]
                            try:
                                response = self.es.bulk(operations=batch, refresh=True)
                                
                                # Count successes and failures
                                for item in response['items']:
                                    if item['index']['status'] == 201 or item['index']['status'] == 200:
                                        indexed += 1
                                    else:
                                        failed += 1
                                        logger.error(f"Failed to index document: {item['index']['error']}")
                                    pbar.update(1)
                                    
                            except Exception as e:
                                logger.error(f"Error during bulk indexing: {str(e)}")
                                failed += len(batch) // 2  # Divide by 2 because each doc has 2 lines
                                pbar.update(len(batch) // 2)
                    
                    # Final refresh
                    self.es.indices.refresh(index=self.index_name)
                    time.sleep(1)  # Give ES time to complete the refresh
                    
                except Exception as e:
                    logger.error(f"Error during bulk indexing: {str(e)}")
                    failed = total_docs - indexed
            
            return {
                'total_pages': total_docs,
                'indexed': indexed,
                'failed': failed
            }
            
        except Exception as e:
            logger.error(f"Error during indexing process: {str(e)}")
            raise
            
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index"""
        stats = self.es.indices.stats(index=self.index_name)
        doc_count = self.es.count(index=self.index_name)
            
        return {
            'doc_count': doc_count['count'],
            'store_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes']
        }