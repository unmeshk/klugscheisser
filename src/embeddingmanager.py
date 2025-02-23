from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np
import logging
import os

from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Manages embedding generation and vector storage."""
    
    def __init__(self):
        """Initialize the embedding model and vector store."""
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Get absolute path for storage
        self.storage_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "chroma_storage"
        ))
        
        # Create directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"ChromaDB storage directory: {self.storage_path}")
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.storage_path)
        
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="klugbot_embeddings",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        logger.info("ChromaDB initialized successfully")


    async def generate_embedding(self, text: str) -> list:
        """Generate embedding for text."""
        try:
            # Generate embedding
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise

    async def store_embedding(self, 
                            entry_id: str, 
                            content: str, 
                            metadata: Dict[str, Any]):
        """Store embedding and metadata in ChromaDB."""
        try:
            # Generate embedding
            embedding = await self.generate_embedding(content)
            
            # Store in ChromaDB
            self.collection.add(
                ids=[str(entry_id)],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[content]
            )

            return embedding
            
        except Exception as e:
            logger.error(f"Error storing embedding: {e}", exc_info=True)
            raise