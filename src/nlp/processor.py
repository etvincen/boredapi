from typing import List, Dict, Any
import logging
from .topic_modeling import TopicModeler
from .keyword_extraction import KeywordExtractor

logger = logging.getLogger(__name__)

class NLPProcessor:
    def __init__(self):
        """Initialize NLP components"""
        self.topic_modeler = TopicModeler(n_topics=3, max_features=1000)
        self.keyword_extractor = KeywordExtractor(min_frequency=2, max_keywords=50)
        
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of documents with all NLP components"""
        try:
            # First, fit the topic model on the entire corpus
            logger.info("Fitting topic model on corpus...")
            self.topic_modeler.fit(documents)
            
            # Process each document
            processed_documents = []
            for i, doc in enumerate(documents, 1):
                try:
                    # Extract topics
                    topic_features = self.topic_modeler.transform_document(doc)
                    
                    # Extract keywords and entities
                    keyword_features = self.keyword_extractor.extract_keywords(doc)
                    
                    # Add NLP features to document
                    doc_with_nlp = {
                        **doc,  # Original document
                        'nlp_features': {
                            'topics': topic_features['topic_distribution'],
                            'keywords': keyword_features['word_cloud'],
                            'named_entities': keyword_features['named_entities'],
                            'noun_chunks': keyword_features['noun_chunks']
                        }
                    }
                    
                    processed_documents.append(doc_with_nlp)
                    
                    if i % 10 == 0:
                        logger.info(f"Processed {i} documents")
                        
                except Exception as e:
                    logger.error(f"Error processing document {i}: {str(e)}")
                    # Add original document without NLP features
                    processed_documents.append(doc)
                    
            # Get corpus-level keyword statistics
            corpus_keywords = self.keyword_extractor.extract_corpus_keywords(documents)
            
            logger.info("NLP processing completed")
            return processed_documents, corpus_keywords
            
        except Exception as e:
            logger.error(f"Error during NLP processing: {str(e)}")
            raise 