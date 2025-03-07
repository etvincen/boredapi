import time
import logging
from typing import Dict, Any, List
import numpy as np
from tqdm import tqdm
import json
import glob
import os
from elasticsearch import Elasticsearch
from src.nlp.embeddings import EmbeddingsGenerator
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsMonitor:
    def __init__(self):
        self.embeddings_generator = EmbeddingsGenerator()
        
    def extract_text_from_sections(self, sections: List[Dict[str, Any]]) -> str:
        """Recursively extract text from nested sections
        
        Args:
            sections: List of section dictionaries
            
        Returns:
            Combined text from all sections
        """
        texts = []
        for section in sections:
            if section.get('title'):
                texts.append(section['title'])
            if section.get('text'):
                texts.append(section['text'])
            if section.get('subsections'):
                texts.append(self.extract_text_from_sections(section['subsections']))
        return ' '.join(filter(None, texts))
        
    def test_single_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Test embedding generation for a single document with detailed metrics
        
        Args:
            doc: Document to test
            
        Returns:
            Dictionary with test results and metrics
        """
        start_time = time.time()
        
        # Get content directly from raw_text
        content = doc.get('raw_text', '')
        
        # Get chunks before embedding
        chunks = self.embeddings_generator.chunk_text(content)
        
        # Generate embedding with timing
        chunk_start = time.time()
        embedding = self.embeddings_generator.generate_document_embedding(doc)
        end_time = time.time()
        
        return {
            'total_time_seconds': round(end_time - start_time, 3),
            'chunking_time_seconds': round(chunk_start - start_time, 3),
            'embedding_time_seconds': round(end_time - chunk_start, 3),
            'num_chunks': len(chunks),
            'content_length': len(content),
            'chunks_preview': [c[:100] + '...' for c in chunks[:2]],  # Preview first 2 chunks
            'embedding_dimension': len(embedding) if embedding else 0,
            'embedding_stats': {
                'mean': round(float(np.mean(embedding)), 4) if embedding else None,
                'std': round(float(np.std(embedding)), 4) if embedding else None,
                'min': round(float(np.min(embedding)), 4) if embedding else None,
                'max': round(float(np.max(embedding)), 4) if embedding else None
            }
        }
        
    def test_batch(self, docs: List[Dict[str, Any]], sample_size: int = 5) -> Dict[str, Any]:
        """Test embedding generation for a batch of documents
        
        Args:
            docs: List of documents to test
            sample_size: Number of documents to analyze in detail
            
        Returns:
            Dictionary with batch test results and metrics
        """
        logger.info(f"Testing batch of {len(docs)} documents...")
        
        # Process all documents with progress bar
        start_time = time.time()
        detailed_results = []
        total_chunks = 0
        embedding_times = []
        
        for doc in tqdm(docs[:sample_size], desc="Processing sample documents"):
            result = self.test_single_document(doc)
            detailed_results.append({
                'title': doc.get('title', 'No title'),
                'metrics': result
            })
            total_chunks += result['num_chunks']
            embedding_times.append(result['embedding_time_seconds'])
            
        end_time = time.time()
        
        # Calculate aggregate metrics
        return {
            'total_docs': len(docs),
            'sample_size': sample_size,
            'total_time_seconds': round(end_time - start_time, 3),
            'avg_time_per_doc': round((end_time - start_time) / sample_size, 3),
            'avg_chunks_per_doc': round(total_chunks / sample_size, 2),
            'embedding_time_stats': {
                'mean': round(np.mean(embedding_times), 3),
                'std': round(np.std(embedding_times), 3),
                'min': round(np.min(embedding_times), 3),
                'max': round(np.max(embedding_times), 3)
            },
            'sample_details': detailed_results
        }
        
def test_real_documents(num_docs: int = 5):
    """Test embedding generation with real documents from transformed results
    
    Args:
        num_docs: Number of documents to test (default: 5)
    """
    # Find the latest transformed results file
    result_files = glob.glob('transformed_results/transformed_*.json')
    if not result_files:
        logger.error("No transformed result files found!")
        return
        
    latest_file = max(result_files)
    logger.info(f"Using latest transformed file: {latest_file}")
    
    # Load the documents
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            pages = data.get('pages', [])
            
        if not pages:
            logger.error("No pages found in the transformed results!")
            return
            
        logger.info(f"Found {len(pages)} pages in total")
        
        # Select a sample of documents
        test_pages = pages[:num_docs]
        logger.info(f"Testing with {len(test_pages)} documents")
        
        # Initialize monitor and run tests
        monitor = EmbeddingsMonitor()
        
        # Test batch processing
        logger.info("\nTesting real document processing:")
        batch_result = monitor.test_batch(test_pages, sample_size=num_docs)
        
        # Print detailed results
        logger.info("\nDetailed Results:")
        logger.info("-" * 50)
        for detail in batch_result['sample_details']:
            logger.info(f"\nDocument: {detail['title']}")
            logger.info(f"Processing time: {detail['metrics']['total_time_seconds']:.3f}s")
            logger.info(f"Number of chunks: {detail['metrics']['num_chunks']}")
            logger.info("First chunk preview:")
            for i, chunk in enumerate(detail['metrics']['chunks_preview']):
                logger.info(f"Chunk {i+1}: {chunk}")
                
        logger.info("\nAggregate Statistics:")
        logger.info("-" * 50)
        logger.info(f"Average time per document: {batch_result['avg_time_per_doc']:.3f}s")
        logger.info(f"Average chunks per document: {batch_result['avg_chunks_per_doc']:.2f}")
        logger.info(f"Embedding time stats: {batch_result['embedding_time_stats']}")
        
    except Exception as e:
        logger.error(f"Error processing real documents: {str(e)}")
        raise

def test_elasticsearch_documents(num_docs: int = 5):
    """Test embedding generation with documents from Elasticsearch
    
    Args:
        num_docs: Number of documents to test (default: 5)
    """
    # Initialize Elasticsearch client
    es = Elasticsearch([
        {
            'host': settings.elasticsearch.HOST,
            'port': settings.elasticsearch.PORT,
            'scheme': 'https' if settings.elasticsearch.USE_SSL else 'http'
        }
    ], basic_auth=(
        settings.elasticsearch.USERNAME,
        settings.elasticsearch.PASSWORD
    ) if settings.elasticsearch.USERNAME else None)
    
    try:
        # Get sample documents from Elasticsearch
        response = es.search(
            index="roc_eclerc_content",
            body={
                "size": num_docs,
                "query": {"match_all": {}},
                "_source": ["title", "raw_text", "statistics"]  # Only fetch needed fields
            }
        )
        
        docs = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            # Create document in the format expected by EmbeddingsGenerator
            doc = {
                'title': source['title'],
                'raw_text': source['raw_text'],  # Use raw_text directly
                'stats': source.get('statistics', {})
            }
            docs.append(doc)
            
        if not docs:
            logger.error("No documents found in Elasticsearch!")
            return
            
        logger.info(f"Testing with {len(docs)} documents from Elasticsearch")
        
        # Initialize monitor and run tests
        monitor = EmbeddingsMonitor()
        
        # Test batch processing
        logger.info("\nTesting Elasticsearch document processing:")
        batch_result = monitor.test_batch(docs, sample_size=num_docs)
        
        # Print detailed results with additional stats
        logger.info("\nDetailed Results:")
        logger.info("-" * 50)
        for detail in batch_result['sample_details']:
            doc_stats = next((d['stats'] for d in docs if d['title'] == detail['title']), {})
            
            logger.info(f"\nDocument: {detail['title']}")
            logger.info(f"Processing time: {detail['metrics']['total_time_seconds']:.3f}s")
            logger.info(f"Number of chunks: {detail['metrics']['num_chunks']}")
            logger.info(f"Content length: {detail['metrics']['content_length']} characters")
            logger.info(f"Original stats from ES:")
            logger.info(f"  - Word count: {doc_stats.get('word_count', 'N/A')}")
            logger.info(f"  - Sentence count: {doc_stats.get('sentence_count', 'N/A')}")
            if detail['metrics']['chunks_preview']:
                logger.info("First chunk preview:")
                for i, chunk in enumerate(detail['metrics']['chunks_preview']):
                    logger.info(f"Chunk {i+1}: {chunk}")
            
            # Add embedding stats
            logger.info("Embedding stats:")
            logger.info(f"  - Dimension: {detail['metrics']['embedding_dimension']}")
            logger.info(f"  - Mean: {detail['metrics']['embedding_stats']['mean']}")
            logger.info(f"  - Std: {detail['metrics']['embedding_stats']['std']}")
                
        logger.info("\nAggregate Statistics:")
        logger.info("-" * 50)
        logger.info(f"Average time per document: {batch_result['avg_time_per_doc']:.3f}s")
        logger.info(f"Average chunks per document: {batch_result['avg_chunks_per_doc']:.2f}")
        logger.info(f"Embedding time stats: {batch_result['embedding_time_stats']}")
        
        # Suggest next steps
        logger.info("\nNext Steps:")
        logger.info("-" * 50)
        logger.info("1. Update Elasticsearch mappings to add vector field:")
        logger.info("   - Add dense_vector field with 384 dimensions")
        logger.info("   - Configure for cosine similarity")
        logger.info("2. Modify indexing pipeline to include embeddings")
        logger.info("3. Re-index content with embeddings")
        logger.info("4. Test hybrid search functionality")
        
    except Exception as e:
        logger.error(f"Error processing Elasticsearch documents: {str(e)}")
        raise

def main():
    """Run embedding tests"""
    # Comment out previous tests
    '''
    # ... previous test code stays commented ...
    '''
    
    # Test with Elasticsearch documents instead
    test_elasticsearch_documents(num_docs=5)
    
if __name__ == '__main__':
    main()