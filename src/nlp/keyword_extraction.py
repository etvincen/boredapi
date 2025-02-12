from typing import List, Dict, Any
import logging
from collections import Counter
from .preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

class KeywordExtractor:
    def __init__(self, min_frequency: int = 2, max_keywords: int = 50):
        """Initialize the keyword extractor"""
        self.min_frequency = min_frequency
        self.max_keywords = max_keywords
        self.preprocessor = TextPreprocessor()
        
    def extract_keywords(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords and named entities from a document"""
        # Process document with spaCy
        nlp_features = self.preprocessor.process_document(document)
        
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
            },
            'noun_chunks': nlp_features['noun_chunks']
        }
        
    def extract_corpus_keywords(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract keywords from multiple documents and compute corpus-level statistics"""
        all_keywords = Counter()
        all_entities = Counter()
        all_noun_chunks = Counter()
        
        # Process each document
        for doc in documents:
            features = self.extract_keywords(doc)
            
            # Aggregate keyword frequencies
            for kw in features['word_cloud']:
                all_keywords[kw['text']] += kw['weight']
                
            # Aggregate named entities
            for entity_type, entities in features['named_entities']['groups'].items():
                for entity in entities:
                    all_entities[f"{entity_type}:{entity}"] += 1
                    
            # Aggregate noun chunks
            for chunk in features['noun_chunks']:
                all_noun_chunks[chunk] += 1
                
        # Get most common keywords across corpus
        top_keywords = [
            {"text": word, "weight": count}
            for word, count in all_keywords.most_common(self.max_keywords)
        ]
        
        # Get most common entities
        top_entities = [
            {
                "type": ent.split(':')[0],
                "text": ent.split(':')[1],
                "count": count
            }
            for ent, count in all_entities.most_common(self.max_keywords)
        ]
        
        return {
            'corpus_keywords': top_keywords,
            'corpus_entities': top_entities,
            'corpus_chunks': dict(all_noun_chunks.most_common(self.max_keywords))
        } 