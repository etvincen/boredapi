from typing import List, Dict, Any
import logging
from .topic_modeling import TopicModeler
from .keyword_extraction import KeywordExtractor
from .embeddings import EmbeddingsGenerator
from .preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

class NLPProcessor:
    def __init__(self):
        """Initialize NLP components"""
        self.preprocessor = TextPreprocessor()
        self.topic_modeler = TopicModeler(n_topics=3, max_features=1000)
        self.keyword_extractor = KeywordExtractor(min_frequency=2, max_keywords=50)
        self.embeddings_generator = EmbeddingsGenerator()
        self.is_fitted = False
        
    def calculate_document_statistics(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics for a document"""
        # Initialize counters
        section_count = 0
        internal_links = 0
        external_links = 0
        image_count = 0
        all_text = []
        
        def process_section(section: Dict[str, Any]) -> None:
            """Process a section and its subsections recursively"""
            nonlocal section_count, internal_links, external_links, image_count
            
            section_count += 1
            
            if section.get('title'):
                all_text.append(section['title'].strip())
            
            if section.get('text'):
                all_text.append(section['text'].strip())
            
            # Count links
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
        words = [w for w in raw_text.split() if w.strip()]
        word_count = len(words)
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
        
        return {
            'raw_text': raw_text,
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
    
    def prepare_document_for_indexing(self, doc: Dict[str, Any], nlp_features: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a document with all features for indexing"""
        # Calculate document statistics
        doc_stats = self.calculate_document_statistics(doc)
        
        # Format topics for indexing
        topics = []
        for topic in nlp_features.get('topics', []):
            topics.append({
                'name': topic['name'],
                'probability': round(topic['probability'], 3)
            })
        
        # Get keywords and add non-accented versions
        keywords = nlp_features.get('lemmatized_tokens', '').split()
        normalized_keywords = [word.translate(str.maketrans('áàâäéèêëíìîïóòôöúùûüýÿ', 'aaaaeeeeiiiioooouuuuyy')) for word in keywords]
        combined_keywords = ' '.join(keywords + normalized_keywords)
        
        # Prepare the document with all fields
        return {
            'url': doc.get('url', ''),
            'title': doc.get('title', ''),
            'raw_text': doc_stats['raw_text'],
            'preprocessed_keywords': combined_keywords,
            'topics': topics,
            'statistics': doc_stats['statistics'],
            'text_embedding': nlp_features.get('embedding'),
            'keywords': nlp_features.get('keywords'),
            'named_entities': nlp_features.get('named_entities', {'groups': {}, 'counts': {}})
        }
        
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of documents with all NLP components"""
        try:
            # First, preprocess all documents
            logger.info("Preprocessing documents...")
            preprocessed_docs = []
            for doc in documents:
                try:
                    nlp_features = self.preprocessor.process_document(doc)
                    preprocessed_docs.append((doc, nlp_features))
                except Exception as e:
                    logger.error(f"Error preprocessing document {doc.get('url', 'unknown')}: {str(e)}")
                    continue
            
            if not preprocessed_docs:
                raise ValueError("No documents could be preprocessed")
            
            # Fit topic model on preprocessed documents
            if not self.is_fitted:
                logger.info("Fitting topic model...")
                try:
                    # Extract token list for topic modeling
                    topic_texts = [features['token_list'] for _, features in preprocessed_docs]
                    self.topic_modeler.fit_preprocessed(topic_texts)
                    self.is_fitted = True
                    logger.info("Topic model fitted successfully")
                except Exception as e:
                    logger.error(f"Error fitting topic model: {str(e)}")
                    raise
            
            # Process each document
            processed_documents = []
            for original_doc, nlp_features in preprocessed_docs:
                try:
                    # Extract topics
                    try:
                        topic_features = self.topic_modeler.transform_preprocessed(
                            nlp_features['token_list']
                        )
                        nlp_features['topics'] = topic_features['topic_distribution']
                    except Exception as e:
                        logger.error(f"Error in topic extraction for {original_doc.get('url', 'unknown')}: {str(e)}")
                        nlp_features['topics'] = []
                    
                    # Extract keywords
                    try:
                        keyword_features = self.keyword_extractor.extract_keywords_from_features(nlp_features)
                        nlp_features['keywords'] = keyword_features['word_cloud']
                        nlp_features['named_entities'] = keyword_features['named_entities']
                    except Exception as e:
                        logger.error(f"Error in keyword extraction for {original_doc.get('url', 'unknown')}: {str(e)}")
                        nlp_features['keywords'] = []
                        nlp_features['named_entities'] = {'groups': {}, 'counts': {}}
                    
                    # Generate embeddings
                    try:
                        embedding = self.embeddings_generator.generate_document_embeddings(
                            [original_doc], show_progress=False
                        )[0]
                        nlp_features['embedding'] = embedding
                    except Exception as e:
                        logger.error(f"Error generating embeddings for {original_doc.get('url', 'unknown')}: {str(e)}")
                        nlp_features['embedding'] = None
                    
                    # Prepare document for indexing
                    processed_doc = self.prepare_document_for_indexing(original_doc, nlp_features)
                    processed_documents.append(processed_doc)
                    
                except Exception as e:
                    logger.error(f"Error processing document {original_doc.get('url', 'unknown')}: {str(e)}")
                    processed_documents.append(original_doc)
            
            # Get corpus-level keyword statistics
            try:
                corpus_keywords = self.keyword_extractor.get_corpus_stats(
                    [nlp_features for _, nlp_features in preprocessed_docs]
                )
            except Exception as e:
                logger.error(f"Error calculating corpus statistics: {str(e)}")
                corpus_keywords = {}
            
            return processed_documents, corpus_keywords
            
        except Exception as e:
            logger.error(f"Error during NLP processing: {str(e)}")
            raise 