import json
from pathlib import Path
import logging
from src.nlp.preprocessor import TextPreprocessor
from src.nlp.topic_modeling import TopicModeler
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_latest_transformed_file() -> Path:
    """Find the most recent transformed results file"""
    transform_dir = Path('transformed_results')
    if not transform_dir.exists():
        raise FileNotFoundError("transformed_results directory not found")
        
    result_files = list(transform_dir.glob('transformed_*.json'))
    if not result_files:
        raise FileNotFoundError("No transformed result files found")
        
    return max(result_files, key=lambda p: p.stat().st_mtime)

def load_transformed_data(file_path: Path) -> Dict[str, Any]:
    """Load transformed data from JSON file"""
    with file_path.open('r', encoding='utf-8') as f:
        return json.load(f)

def prepare_texts_for_lda(pages: List[Dict[str, Any]], preprocessor: TextPreprocessor) -> List[str]:
    """Prepare texts for LDA by preprocessing each page"""
    processed_texts = []
    for page in pages:
        # Process document to get lemmatized tokens
        nlp_results = preprocessor.process_document(page)
        # Join lemmatized tokens into a single string
        processed_text = ' '.join(nlp_results['lemmatized_tokens'])
        processed_texts.append(processed_text)
    return processed_texts

def analyze_nlp_results(page: Dict[str, Any], preprocessor: TextPreprocessor, topic_modeler: TopicModeler) -> None:
    """Analyze and display NLP processing results for a single page"""
    logger.info("\n=== Processing Page ===")
    logger.info(f"URL: {page.get('url')}")
    logger.info(f"Title: {page.get('title')}")
    
    # Display section structure
    logger.info("\nSection Structure:")
    def print_sections(sections, level=0):
        for section in sections:
            indent = "  " * level
            title = section.get('title', 'Untitled Section')
            text_preview = section.get('text', '')[:100] + '...' if section.get('text') else 'No text'
            logger.info(f"{indent}- {title}")
            logger.info(f"{indent}  Text preview: {text_preview}")
            if section.get('subsections'):
                print_sections(section['subsections'], level + 1)
    
    print_sections(page.get('sections', []))
    
    # Process with NLP
    logger.info("\nNLP Analysis Results:")
    nlp_results = preprocessor.process_document(page)
    
    # Get topic distribution for this document
    topic_results = topic_modeler.transform_document(page)
    
    # Display topic distribution
    logger.info("\nTopic Distribution:")
    for topic in topic_results['topic_distribution']:
        logger.info(f"\nTopic {topic['topic_id']} (Probability: {topic['probability']:.3f}):")
        for term in topic['terms']:
            logger.info(f"- {term['term']} ({term['weight']:.3f})")
    
    # Display top keywords
    logger.info("\nTop Keywords (frequency):")
    top_keywords = sorted(nlp_results['keyword_frequencies'].items(), 
                         key=lambda x: x[1], reverse=True)[:10]
    for keyword, freq in top_keywords:
        logger.info(f"- {keyword}: {freq}")
    
    # Display named entities
    logger.info("\nNamed Entities:")
    entity_types = {}
    for entity in nlp_results['named_entities']:
        entity_type = entity['label']
        if entity_type not in entity_types:
            entity_types[entity_type] = []
        entity_types[entity_type].append(entity['text'])
    
    for entity_type, entities in entity_types.items():
        logger.info(f"\n{entity_type}:")
        for entity in entities[:5]:  # Show up to 5 entities per type
            logger.info(f"- {entity}")
    
    # Display some noun chunks
    logger.info("\nSample Noun Chunks (first 10):")
    for chunk in nlp_results['noun_chunks'][:10]:
        logger.info(f"- {chunk}")

def main():
    try:
        # Find and load latest transformed results
        latest_file = find_latest_transformed_file()
        logger.info(f"Loading transformed results from: {latest_file}")
        
        data = load_transformed_data(latest_file)
        
        # Initialize NLP components
        preprocessor = TextPreprocessor()
        topic_modeler = TopicModeler(n_topics=3, max_features=1000)
        
        # Get all pages for topic modeling
        pages = data.get('pages', [])
        
        # First fit the topic model on all pages
        logger.info("\nFitting topic model on all pages...")
        topic_modeler.fit(pages)
        
        # Display overall topic model information
        logger.info("\n=== Overall Topic Model ===")
        for topic_idx in range(topic_modeler.n_topics):
            terms = topic_modeler.get_topic_terms(topic_idx, n_top_words=10)
            logger.info(f"\nTopic {topic_idx}:")
            for term in terms:
                logger.info(f"- {term['term']} ({term['weight']:.3f})")
        
        # Now analyze individual pages (first 3)
        for i, page in enumerate(pages[:3], 1):
            logger.info(f"\n\n{'='*50}")
            logger.info(f"Processing page {i} of 3")
            analyze_nlp_results(page, preprocessor, topic_modeler)
            
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise

if __name__ == "__main__":
    main() 