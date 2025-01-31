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
        """Transform a page into an Elasticsearch document with flattened sections"""
        # Initialize text collection
        all_text = []
        section_titles = []
        
        def process_section(section: Dict[str, Any]) -> None:
            """Process a section and its subsections recursively"""
            # Add title if present
            if section.get('title'):
                section_titles.append(section['title'].strip())
                
            # Add text content
            if section.get('text'):
                all_text.append(section['text'].strip())
                
            # Process subsections
            for subsection in section.get('subsections', []):
                process_section(subsection)
        
        # Process all sections
        for section in page.get('sections', []):
            process_section(section)
            
        # Combine all text, removing extra whitespace and newlines
        combined_text = ' '.join(text for text in all_text if text)
        
        # Calculate basic statistics
        word_count = len(combined_text.split()) if combined_text else 0
        section_count = len(section_titles)
        
        # Ensure timestamp is in ISO format
        timestamp = page.get('timestamp')
        if not timestamp:
            timestamp = datetime.now().isoformat()
        elif not isinstance(timestamp, str):
            timestamp = timestamp.isoformat()
            
        # Prepare metadata
        metadata = {
            'language': page.get('metadata', {}).get('language', 'fr'),  # Default to French
            'last_updated': timestamp,
            'word_count': word_count,
            'section_count': section_count
        }
        
        # Prepare the document
        doc = {
            'url': page.get('url', ''),  # Empty string if missing
            'timestamp': timestamp,
            'title': page.get('title', ''),  # Empty string if missing
            'meta_tags': {
                'description': page.get('meta_tags', {}).get('description', ''),
                'keywords': page.get('meta_tags', {}).get('keywords', '')
            },
            'content': {
                'text': combined_text,
                'section_titles': section_titles if section_titles else []  # Empty list if no titles
            },
            'metadata': metadata
        }
        
        # Log document structure for debugging
        logger.debug(f"Prepared document for {doc['url']} with {word_count} words and {section_count} sections")
        
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