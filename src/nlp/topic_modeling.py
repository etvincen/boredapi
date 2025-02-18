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
            stop_words=None,  # Already handled by preprocessor
            min_df=2  # Require terms to appear in at least 2 documents
        )
        
        self.lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method='online'
        )
        
        self.is_fitted = False
        self.topic_labels = {}  # Store assigned labels
        
        logger.info(f"Initialized TopicModeler with {n_topics} topics and {max_features} max features")
        
        # Predefined topic categories with their related terms in French
        self.topic_categories = {
            "Services Funéraires": ["obsèques", "funéraire", "service", "funérailles", "cérémonie"],
            "Support Familial": ["famille", "deuil", "accompagnement", "soutien", "aide"],
            "Aspects Commerciaux": ["devis", "prix", "tarif", "contrat", "assurance"],
            "Aspects Pratiques": ["transport", "démarche", "document", "administratif", "organisation"],
            "Monuments & Hommages": ["monument", "fleur", "plaque", "urne", "souvenir"]
        }
        
    def fit_preprocessed(self, token_lists: List[List[str]]) -> None:
        """Fit the topic model on preprocessed token lists"""
        if not token_lists:
            raise ValueError("No token lists provided for fitting")
            
        logger.info(f"Starting topic modeling on {len(token_lists)} documents")
        
        try:
            # Join tokens into space-separated strings for vectorizer
            processed_texts = [' '.join(tokens) for tokens in token_lists]
            
            logger.info("Creating document-term matrix...")
            self.dtm = self.vectorizer.fit_transform(processed_texts)
            
            # Log vocabulary stats
            vocab = self.vectorizer.get_feature_names_out()
            logger.info(f"Vocabulary size: {len(vocab)}")
            logger.debug(f"Sample vocabulary terms: {list(vocab[:20])}")
            
            logger.info(f"Document-term matrix shape: {self.dtm.shape}")
            if self.dtm.shape[1] == 0:
                raise ValueError("Empty vocabulary in document-term matrix")
            
            logger.info("Fitting LDA model...")
            self.lda.fit(self.dtm)
            
            self.feature_names = vocab
            self.is_fitted = True
            
            # Assign topic labels after fitting
            self._assign_topic_labels()
            
            logger.info("Topic model fitted successfully")
            
        except Exception as e:
            logger.error(f"Error during topic modeling: {str(e)}")
            raise
        
    def _assign_topic_labels(self) -> None:
        """Assign unique labels to topics based on their terms"""
        # Get terms for all topics
        topic_terms = [self.get_topic_terms(i) for i in range(self.n_topics)]
        
        # Calculate similarities for all topics with all categories
        topic_similarities = []
        for terms in topic_terms:
            top_terms = [term['term'] for term in terms[:5]]
            
            category_scores = {}
            for category, category_terms in self.topic_categories.items():
                # Simple overlap-based similarity
                similarity_sum = sum(
                    1 for term in top_terms
                    if any(cat_term in term or term in cat_term
                          for cat_term in category_terms)
                )
                category_scores[category] = similarity_sum / len(top_terms)
            
            topic_similarities.append(category_scores)
        
        # Assign labels greedily based on highest similarities
        used_categories = set()
        for topic_idx, similarities in enumerate(topic_similarities):
            # Sort categories by similarity
            sorted_categories = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Find the best unused category
            for category, score in sorted_categories:
                if category not in used_categories:
                    self.topic_labels[topic_idx] = category
                    used_categories.add(category)
                    break
            
            # If all categories are used, assign "Autre"
            if topic_idx not in self.topic_labels:
                self.topic_labels[topic_idx] = "Autre"
        
    def get_topic_terms(self, topic_idx: int, n_top_words: int = 10) -> List[Dict[str, float]]:
        """Get the top terms for a specific topic"""
        if not hasattr(self, 'feature_names'):
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
        
    def transform_preprocessed(self, tokens: List[str]) -> Dict[str, Any]:
        """Get topic distribution for preprocessed tokens"""
        if not self.is_fitted:
            raise ValueError("Model needs to be fitted first")
            
        # Join tokens into space-separated string
        processed_text = ' '.join(tokens)
        
        # Transform to document-term matrix
        doc_dtm = self.vectorizer.transform([processed_text])
        
        # Get topic distribution
        topic_dist = self.lda.transform(doc_dtm)[0]
        
        # Get top topics with their terms
        top_topics = []
        for idx in topic_dist.argsort()[::-1][:self.n_topics]:
            terms = self.get_topic_terms(idx, n_top_words=10)
            
            top_topics.append({
                "topic_id": int(idx),
                "name": self.topic_labels[idx],
                "probability": float(topic_dist[idx]),
                "terms": terms
            })
            
        return {
            "topic_distribution": top_topics
        }
        
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
            terms = self.get_topic_terms(idx, n_top_words=10)
            
            top_topics.append({
                "topic_id": int(idx),
                "name": self.topic_labels[idx],  # Use pre-assigned label
                "probability": float(topic_dist[idx]),
                "terms": terms
            })
            
        return {
            "topic_distribution": top_topics
        }
        
    def transform_corpus(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get topic distributions for multiple documents"""
        return [self.transform_document(doc) for doc in documents] 