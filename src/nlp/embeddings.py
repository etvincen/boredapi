from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union, Dict, Any
import logging

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
        
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the text embedding
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()  # Convert to list for JSON serialization
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
            
    def generate_document_embedding(self, doc: Dict[str, Any]) -> List[float]:
        """Generate embedding for a document using chunking and averaging
        
        Args:
            doc: Document dictionary containing title and raw_text
            
        Returns:
            Combined embedding for the document
        """
        try:
            title = doc.get('title', '')
            content = doc.get('raw_text', '')
            
            # Always embed the title separately (important for search)
            chunks = [title] if title else []
            
            # Add content chunks
            if content:
                content_chunks = self.chunk_text(content)
                # Take first few chunks to keep processing manageable
                chunks.extend(content_chunks[:5])  # Limit to first 5 chunks (~2500 tokens)
            
            if not chunks:
                return None
                
            # Generate embeddings for all chunks
            embeddings = self.model.encode(chunks, convert_to_numpy=True)
            
            # Weighted average: title gets 2x weight if present
            if title and len(chunks) > 1:
                weights = np.array([2.0] + [1.0] * (len(chunks) - 1))
                weights = weights / weights.sum()  # Normalize weights
                final_embedding = np.average(embeddings, axis=0, weights=weights)
            else:
                final_embedding = np.mean(embeddings, axis=0)
                
            return final_embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating document embedding: {str(e)}")
            raise
            
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a search query
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding
        """
        return self.generate_embedding(query)