from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union, Dict, Any
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)

class EmbeddingsGenerator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embeddings generator with a specific SBERT model"""
        self.model = SentenceTransformer(model_name)
        self.chunk_size = 512  # Approximate tokens per chunk
        
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of roughly equal size
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        # Simple sentence-based chunking
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            # Rough estimate of tokens (words + some overhead)
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.chunk_size:
                if current_chunk:  # Only add if we have content
                    chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:  # Add the last chunk
            chunks.append('. '.join(current_chunk) + '.')
            
        return chunks
        
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of input texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embeddings for each text
        """
        try:
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                all_embeddings.extend(batch_embeddings.tolist())
            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
            
    def generate_document_embeddings(self, documents: List[Dict[str, Any]], 
                                   batch_size: int = 32, 
                                   show_progress: bool = True) -> List[List[float]]:
        """Generate embeddings for multiple documents using chunking and averaging
        
        Args:
            documents: List of document dictionaries
            batch_size: Number of chunks to process at once
            show_progress: Whether to show progress bar
            
        Returns:
            List of document embeddings
        """
        try:
            all_embeddings = []
            iterator = tqdm(documents, desc="Generating embeddings") if show_progress else documents
            
            for doc in iterator:
                try:
                    title = doc.get('title', '')
                    content = doc.get('raw_text', '')
                    
                    # Always embed the title separately (important for search)
                    chunks = [title] if title else []
                    
                    # Add content chunks
                    if content:
                        content_chunks = self.chunk_text(content)
                        # Take first few chunks to keep processing manageable
                        chunks.extend(content_chunks[:5])  # Limit to first 5 chunks
                    
                    if not chunks:
                        all_embeddings.append(None)
                        continue
                    
                    # Generate embeddings for all chunks
                    chunk_embeddings = np.array(self.generate_embeddings_batch(chunks, batch_size))
                    
                    # Weighted average: title gets 2x weight if present
                    if title and len(chunks) > 1:
                        weights = np.array([2.0] + [1.0] * (len(chunks) - 1))
                        weights = weights / weights.sum()  # Normalize weights
                        final_embedding = np.average(chunk_embeddings, axis=0, weights=weights)
                    else:
                        final_embedding = np.mean(chunk_embeddings, axis=0)
                        
                    all_embeddings.append(final_embedding.tolist())
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('url', 'unknown')}: {str(e)}")
                    all_embeddings.append(None)
                    
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating document embeddings: {str(e)}")
            raise
            
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a search query
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding
        """
        return self.model.encode(query, convert_to_numpy=True).tolist()