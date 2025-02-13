from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import Dict, Any, List, Generator
import logging
from datetime import datetime
from .mappings import get_index_settings, get_index_name
import time
from tqdm import tqdm
from ..nlp.preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

class ContentIndexer:
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.index_name = get_index_name()
        self.batch_size = 10  # Add batch size as instance variable
        self.preprocessor = TextPreprocessor()
        
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
        
    def prepare_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a document for indexing with all required fields and statistics"""
        # Extract topics from NLP features
        topics = []
        if 'nlp_features' in doc and 'topics' in doc['nlp_features']:
            for topic in doc['nlp_features']['topics']:
                topics.append({
                    'name': topic['name'],
                    'probability': round(topic['probability'], 3)  # Round to 3 decimal places
                })
        
        # Collect all text and calculate statistics
        all_text = []
        section_count = 0
        internal_links = 0
        external_links = 0
        image_count = 0
        
        def process_section(section: Dict[str, Any]) -> None:
            """Process a section and its subsections recursively"""
            nonlocal section_count, internal_links, external_links, image_count
            
            section_count += 1
            
            if section.get('title'):
                all_text.append(section['title'].strip())
            
            if section.get('text'):
                all_text.append(section['text'].strip())
            
            # Count links from the section
            for link in section.get('links', []):
                if link.get('is_internal', False):
                    internal_links += 1
                else:
                    external_links += 1
            
            # Count images
            if 'images' in section:
                image_count += len(section['images'])
            
            # Process subsections recursively
            for subsection in section.get('subsections', []):
                process_section(subsection)
        
        # Process all sections
        for section in doc.get('sections', []):
            process_section(section)
        
        # Combine all text with proper spacing
        raw_text = ' '.join(text for text in all_text if text)
        
        # Calculate text statistics
        sentences = [s.strip() for s in raw_text.split('.') if s.strip()]
        sentence_count = len(sentences)
        words = [w for w in raw_text.split() if w.strip()]  # Filter out empty strings
        word_count = len(words)
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
        
        # Get preprocessed keywords using TextPreprocessor
        preprocessed = self.preprocessor.process_document(doc)
        # Join tokens with proper spacing and ensure no empty tokens
        preprocessed_keywords = ' '.join(token for token in preprocessed['lemmatized_tokens'] if token.strip())
        
        # Prepare the document with all fields
        return {
            'url': doc.get('url', ''),
            'title': doc.get('title', ''),
            'raw_text': raw_text,
            'preprocessed_keywords': preprocessed_keywords,
                    'topics': topics,
            'statistics': {
                    'word_count': word_count,
                'sentence_count': sentence_count,
                    'section_count': section_count,
                'external_link_count': external_links,
                'internal_link_count': internal_links,
                'image_count': image_count,
                'avg_words_per_sentence': round(avg_words_per_sentence, 2)
            }
        }
        
    def generate_bulk_actions(self, pages: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """Generate actions for bulk indexing"""
        for page in pages:
            doc = self.prepare_document(page)
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
                    prepared_doc = self.prepare_document(doc)
                    # Each operation needs both the action and source lines
                    operations.append({"index": {"_index": self.index_name, "_id": prepared_doc['url']}})
                    operations.append(prepared_doc)
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