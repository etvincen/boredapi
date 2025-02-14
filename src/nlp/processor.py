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
        self.is_fitted = False
        
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of documents with essential NLP components"""
        try:
            # First, fit models on the entire corpus if not already fitted
            if not self.is_fitted:
                logger.info("Fitting NLP models on corpus...")
                try:
                    # Fit topic model
                    self.topic_modeler.fit(documents)
                    # Fit keyword extractor
                    self.keyword_extractor.fit(documents)
                    self.is_fitted = True
                    logger.info("NLP models fitted successfully")
                except Exception as e:
                    logger.error(f"Error fitting NLP models: {str(e)}")
                    raise
            
            # Then process each document
            processed_documents = []
            for doc in documents:
                try:
                    # Extract topics using the fitted model
                    try:
                        topic_features = self.topic_modeler.transform_document(doc)
                    except Exception as e:
                        logger.error(f"Error in topic extraction for {doc.get('url', 'unknown')}: {str(e)}")
                        topic_features = {'topic_distribution': []}
                    
                    # Extract keywords and entities
                    try:
                        keyword_features = self.keyword_extractor.extract_keywords(doc)
                    except Exception as e:
                        logger.error(f"Error in keyword extraction for {doc.get('url', 'unknown')}: {str(e)}")
                        keyword_features = {
                            'word_cloud': [],
                            'named_entities': {'groups': {}, 'counts': {}},
                            'noun_chunks': []
                        }
                    
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
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('url', 'unknown')}: {str(e)}")
                    processed_documents.append(doc)
            
            # Get corpus-level keyword statistics
            try:
                corpus_keywords = self.keyword_extractor.get_corpus_keywords()
            except Exception as e:
                logger.error(f"Error getting corpus statistics: {str(e)}")
                corpus_keywords = {}
            
            return processed_documents, corpus_keywords
            
        except Exception as e:
            logger.error(f"Error during NLP processing: {str(e)}")
            raise 