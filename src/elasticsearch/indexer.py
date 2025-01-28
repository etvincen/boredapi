from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import Dict, Any, List, Generator
import logging
from datetime import datetime
from .mappings import get_index_settings, get_index_name
import time

logger = logging.getLogger(__name__)

class ContentIndexer:
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.index_name = get_index_name()
        
    def create_index(self) -> None:
        """Create the Elasticsearch index with proper mappings"""
        if self.es.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} already exists")
            return
            
        settings = get_index_settings()
        self.es.indices.create(index=self.index_name, body=settings)
        logger.info(f"Created index {self.index_name}")
        
    def prepare_document(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a page into an Elasticsearch document"""
        # Calculate content statistics with safety checks
        content = page.get('content', '')
        links = page.get('links', {'internal': [], 'external': [], 'resources': []})
        images = page.get('images', [])
        
        content_stats = {
            "text_length": len(content) if isinstance(content, str) else 0,
            "section_count": 1,  # Since content is a string, we treat it as one section
            "image_count": len(images),
            "internal_link_count": len(links.get('internal', [])),
            "external_link_count": len(links.get('external', [])),
            "resource_link_count": len(links.get('resources', []))
        }
        
        # Ensure timestamp is in proper format
        if isinstance(page.get('timestamp'), str):
            try:
                datetime.fromisoformat(page['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                page['timestamp'] = datetime.now().isoformat()
        
        # Add content statistics to the document
        doc = {**page, 'content_stats': content_stats}
        return doc
        
    def generate_bulk_actions(self, pages: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """Generate actions for bulk indexing"""
        for page in pages:
            doc = self.prepare_document(page)
            yield {
                "_index": self.index_name,
                "_id": doc['url'],  # Use URL as document ID
                "_source": doc
            }
            
    def index_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index multiple pages using bulk API"""
        try:
            # Create index if it doesn't exist
            self.create_index()
            
            # Process in smaller batches
            batch_size = 10  # Reduced from 100
            total_pages = len(pages)
            total_indexed = 0
            total_failed = 0
            
            for i in range(0, total_pages, batch_size):
                batch = pages[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(total_pages + batch_size - 1)//batch_size}")
                
                # Perform bulk indexing for this batch
                success, failed = bulk(
                    self.es,
                    self.generate_bulk_actions(batch),
                    chunk_size=batch_size,
                    raise_on_error=False,
                    request_timeout=30  # Add timeout
                )
                
                total_indexed += success
                total_failed += len(failed)
                
                # Add a small delay between batches
                if i + batch_size < total_pages:
                    time.sleep(1)  # 1 second delay between batches
            
            return {
                "total_pages": total_pages,
                "indexed": total_indexed,
                "failed": total_failed
            }
            
        except Exception as e:
            logger.error(f"Error during indexing: {e}")
            raise
            
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index"""
        try:
            stats = self.es.indices.stats(index=self.index_name)
            count = self.es.count(index=self.index_name)
            
            return {
                "doc_count": count['count'],
                "store_size": stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                "indexing": stats['indices'][self.index_name]['total']['indexing']
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {} 