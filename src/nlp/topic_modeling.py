from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import logging
from .preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

class TopicModeler:
    def __init__(self, n_topics: int = 3, max_features: int = 1000):
        """Initialize the topic modeler"""
        self.n_topics = n_topics
        self.max_features = max_features
        self.preprocessor = TextPreprocessor()
        
        # Initialize but don't fit yet
        self.vectorizer = CountVectorizer(
            max_features=max_features,
            stop_words=None  # We'll use spaCy's preprocessing
        )
        
        self.lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method='online'
        )
        
        self.is_fitted = False
        
    def _prepare_texts(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Prepare texts for topic modeling using preprocessor"""
        processed_texts = []
        
        for doc in documents:
            # Process document
            nlp_features = self.preprocessor.process_document(doc)
            # Join lemmatized tokens
            processed_texts.append(' '.join(nlp_features['lemmatized_tokens']))
            
        return processed_texts
        
    def fit(self, documents: List[Dict[str, Any]]) -> None:
        """Fit the topic model on a corpus of documents"""
        logger.info("Preparing texts for topic modeling...")
        processed_texts = self._prepare_texts(documents)
        
        logger.info("Creating document-term matrix...")
        self.dtm = self.vectorizer.fit_transform(processed_texts)
        
        logger.info("Fitting LDA model...")
        self.lda.fit(self.dtm)
        
        self.feature_names = self.vectorizer.get_feature_names_out()
        self.is_fitted = True
        
        logger.info("Topic model fitted successfully")
        
    def get_topic_terms(self, topic_idx: int, n_top_words: int = 10) -> List[Dict[str, float]]:
        """Get the top terms for a specific topic"""
        if not self.is_fitted:
            raise ValueError("Model needs to be fitted first")
            
        topic_distribution = self.lda.components_[topic_idx]
        sorted_terms = topic_distribution.argsort()[:-(n_top_words + 1):-1]
        
        return [
            {
                "term": self.feature_names[idx],
                "weight": float(topic_distribution[idx])
            }
            for idx in sorted_terms
        ]
        
    def transform_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Get topic distribution for a single document"""
        if not self.is_fitted:
            raise ValueError("Model needs to be fitted first")
            
        # Process document
        processed_text = self._prepare_texts([document])[0]
        
        # Transform to document-term matrix
        doc_dtm = self.vectorizer.transform([processed_text])
        
        # Get topic distribution
        topic_dist = self.lda.transform(doc_dtm)[0]
        
        # Get top topics with their terms
        top_topics = []
        for idx in topic_dist.argsort()[::-1][:self.n_topics]:
            top_topics.append({
                "topic_id": int(idx),
                "probability": float(topic_dist[idx]),
                "terms": self.get_topic_terms(idx, n_top_words=5)
            })
            
        return {
            "topic_distribution": top_topics
        }
        
    def transform_corpus(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get topic distributions for multiple documents"""
        return [self.transform_document(doc) for doc in documents] 