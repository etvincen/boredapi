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
        # Extract sections text for full-text search
        sections_text = []
        all_sections = []  # Track all sections regardless of nesting
        section_levels = {1: 0, 2: 0, 3: 0}  # Count sections by level
        
        def process_section(section, parent_path=""):
            """Process a section and its subsections recursively"""
            if section.get('title'):
                sections_text.append(section['title'])
            if section.get('text'):
                sections_text.append(section['text'])
                
            # Track section level counts
            level = section.get('level', 1)
            section_levels[level] = section_levels.get(level, 0) + 1
            
            # Create section analytics entry
            section_analytics = {
                'title': section.get('title', ''),
                'text': section.get('text', ''),
                'level': level,
                'path': f"{parent_path}/{section.get('title', '')}" if parent_path else section.get('title', ''),
                'word_count': len(section.get('text', '').split()),
                'has_images': bool(section.get('images')),
                'image_count': len(section.get('images', []))
            }
            all_sections.append(section_analytics)
            
            # Process subsections
            for subsection in section.get('subsections', []):
                process_section(subsection, section_analytics['path'])
        
        # Process all sections
        for section in page.get('sections', []):
            process_section(section)
        
        # Prepare the main content structure
        main_content = {
            'text': ' '.join(sections_text),
            'sections': page.get('sections', [])  # Keep original nested structure
        }
        
        # Prepare metadata
        metadata = page.get('metadata', {})
        if 'last_updated' not in metadata and 'timestamp' in page:
            metadata['last_updated'] = page['timestamp']
        
        # Calculate content statistics
        content_stats = {
            'word_count': len(main_content['text'].split()),
            'text_length': len(main_content['text']),
            'section_count': len(all_sections),
            'sections_by_level': section_levels,
            'paragraph_count': sum(1 for s in all_sections if s.get('text')),
            'sections_with_images': sum(1 for s in all_sections if s.get('has_images')),
            'total_images': sum(s.get('image_count', 0) for s in all_sections),
            'average_section_length': sum(s.get('word_count', 0) for s in all_sections) / len(all_sections) if all_sections else 0
        }
        
        # Prepare the document
        doc = {
            'url': page.get('url'),
            'timestamp': page.get('timestamp', datetime.now().isoformat()),
            'title': page.get('title'),
            'meta_tags': page.get('meta_tags', {}),
            'main_content': main_content,
            'metadata': metadata,
            'content_stats': content_stats,
            'image_stats': page.get('image_stats', {}),
            'section_analytics': {
                'level_distribution': section_levels,
                'sections_list': all_sections
            }
        }
        
        # Log document structure for debugging
        logger.debug(f"Prepared document structure for {doc['url']}")
        
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