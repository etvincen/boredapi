from typing import List, Dict, Any
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class KeywordExtractor:
    def __init__(self, min_frequency: int = 2, max_keywords: int = 50):
        """Initialize the keyword extractor"""
        self.min_frequency = min_frequency
        self.max_keywords = max_keywords
        
    def extract_keywords_from_features(self, nlp_features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords and named entities from preprocessed features"""
        # Get keyword frequencies
        keyword_freq = nlp_features['keyword_frequencies']
        
        # Filter by minimum frequency and sort by frequency
        filtered_keywords = {
            word: freq for word, freq in keyword_freq.items()
            if freq >= self.min_frequency
        }
        
        # Sort by frequency and limit to max_keywords
        sorted_keywords = sorted(
            filtered_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )[:self.max_keywords]
        
        # Format for word cloud
        word_cloud_data = [
            {"text": word, "weight": freq}
            for word, freq in sorted_keywords
        ]
        
        # Group named entities by type
        entity_groups = {}
        for entity in nlp_features['named_entities']:
            entity_type = entity['label']
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(entity['text'])
        
        # Count entities by type
        entity_counts = {
            entity_type: len(entities)
            for entity_type, entities in entity_groups.items()
        }
        
        return {
            'word_cloud': word_cloud_data,
            'named_entities': {
                'groups': entity_groups,
                'counts': entity_counts
            }
        }
        
    def get_corpus_stats(self, preprocessed_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate corpus-level keyword statistics from preprocessed documents"""
        all_keywords = Counter()
        all_entities = Counter()
        
        # Process each document's features
        for features in preprocessed_docs:
            # Skip if features are missing
            if not isinstance(features, dict):
                continue
            
            # Aggregate keyword frequencies from lemmatized tokens
            if 'lemmatized_tokens' in features:
                for token in features['lemmatized_tokens']:
                    all_keywords[token] += 1
                
            # Aggregate named entities
            if 'named_entities' in features:
                for entity in features['named_entities']:
                    if isinstance(entity, dict) and 'text' in entity and 'label' in entity:
                        entity_key = f"{entity['label']}:{entity['text']}"
                        all_entities[entity_key] += 1
        
        return {
            'corpus_keywords': [
                {"text": word, "weight": count}
                for word, count in all_keywords.most_common(self.max_keywords)
            ],
            'corpus_entities': [
                {
                    "type": ent.split(':')[0],
                    "text": ent.split(':')[1],
                    "count": count
                }
                for ent, count in all_entities.most_common(self.max_keywords)
            ]
        } 