from typing import List, Dict, Any
import spacy
import re
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class TextPreprocessor:
    def __init__(self):
        """Initialize the preprocessor with French language model"""
        try:
            self.nlp = spacy.load("fr_core_news_md")
        except OSError:
            logger.info("Downloading French language model...")
            spacy.cli.download("fr_core_news_md")
            self.nlp = spacy.load("fr_core_news_md")
            
        # Custom stop words in addition to spaCy's
        self.custom_stop_words = {
            "roc", "eclerc", "cookies", "javascript", "navigation",
            "menu", "site", "cliquez", "voir", "plus", "roceclerc",
            "pour", "et", "de", "le", "la", "les", "un", "une",
            "des", "du", "au", "aux", "avec", "par", "sur", "dans",
            "en", "vers", "chez", "donc", "car", "mais", "ou", "où",
            "qui", "que", "quoi", "dont", "alors", "si", "très",
            "comment", "pourquoi", "quand", "votre", "nos", "notre",
            "vos", "leur", "leurs", "mon", "ton", "son", "mes", "tes",
            "ses", "ce", "cet", "cette", "ces", "celui", "celle",
            "ceux", "celles", "autre", "autres", "même", "mêmes"
        }
        
        # Add custom stop words to spaCy
        for word in self.custom_stop_words:
            self.nlp.vocab[word].is_stop = True
            
        logger.info(f"Initialized TextPreprocessor with {len(self.custom_stop_words)} custom stop words")
    
    def clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove numbers (including those with decimal points)
        text = re.sub(r'\b\d+(?:\.\d+)?\b', '', text)
        # Fix spaces before cleaning up whitespace
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
        # Normalize all types of whitespace (including newlines) to single spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def process_text(self, text: str) -> spacy.tokens.Doc:
        """Process text with spaCy"""
        cleaned_text = self.clean_text(text)
        return self.nlp(cleaned_text)
    
    def get_lemmatized_tokens(self, doc: spacy.tokens.Doc) -> List[str]:
        """Extract lemmatized tokens, excluding stop words and punctuation"""
        return [
            token.lemma_.lower() for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space
            and len(token.lemma_) > 1
        ]
    
    def get_named_entities(self, doc: spacy.tokens.Doc) -> List[Dict[str, str]]:
        """Extract named entities with their labels"""
        return [
            {"text": ent.text, "label": ent.label_}
            for ent in doc.ents
            if len(ent.text.strip()) > 1
        ]
    
    def get_keyword_frequencies(self, doc: spacy.tokens.Doc) -> Dict[str, int]:
        """Get frequency distribution of keywords"""
        # Get lemmatized tokens
        tokens = self.get_lemmatized_tokens(doc)
        
        # Add named entities
        entities = [ent["text"].lower() for ent in self.get_named_entities(doc)]
        
        # Combine all keywords
        all_keywords = tokens + entities
        
        # Count frequencies
        return dict(Counter(all_keywords))
    
    def process_document(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete document and return NLP features"""
        # Initialize text accumulator
        all_text = []
        
        # Add title if present
        title = content.get('title', '')
        if title:
            all_text.append(title)
        
        # Process sections recursively
        def process_sections(sections):
            for section in sections:
                # Add section title
                if section.get('title'):
                    all_text.append(section['title'])
                
                # Add section text
                if section.get('text'):
                    all_text.append(section['text'])
                
                # Process subsections recursively
                if section.get('subsections'):
                    process_sections(section['subsections'])
        
        # Process all sections
        process_sections(content.get('sections', []))
        
        # Clean and combine all text with proper spacing
        cleaned_texts = [self.clean_text(text) for text in all_text if text and text.strip()]
        full_text = ' '.join(cleaned_texts)
        # Process with spaCy
        doc = self.process_text(full_text)
        
        # Get lemmatized tokens
        lemmatized = self.get_lemmatized_tokens(doc)
        
        # Deduplicate and sort
        unique_tokens = sorted(set(lemmatized))
        
        # Join tokens for certain features
        joined_tokens = ' '.join(unique_tokens)
        
        return {
            'lemmatized_tokens': joined_tokens,  # For backward compatibility
            'token_list': unique_tokens,  # For topic modeling
            'named_entities': self.get_named_entities(doc),
            'keyword_frequencies': self.get_keyword_frequencies(doc),
            'spacy_doc': doc  # Return the spaCy doc for reuse
        } 