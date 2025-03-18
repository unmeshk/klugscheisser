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
            
    async def delete_embeddings_by_ids(self, entry_ids: list) -> int:
        """Delete embeddings with matching IDs from ChromaDB.
        
        Args:
            entry_ids: List of document IDs to delete
            
        Returns:
            Number of deleted embeddings
        """
        try:
            if not entry_ids:
                return 0
                
            # Delete from ChromaDB
            self.collection.delete(ids=entry_ids)
            
            return len(entry_ids)
            
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}", exc_info=True)
            raise
            
    async def delete_embeddings_by_source_url(self, source_url: str) -> int:
        """Delete embeddings with matching source_url from ChromaDB.
        
        Args:
            source_url: Source URL to match
            
        Returns:
            Number of deleted embeddings
        """
        try:
            # Query to find matching documents
            results = self.collection.get(
                where={"source_url": source_url},
                include=["metadatas", "documents"]
            )
            
            if not results or not results["ids"]:
                return 0
                
            # Delete the matched documents
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
            
        except Exception as e:
            logger.error(f"Error deleting embeddings by source_url: {e}", exc_info=True)
            raise
            
    async def delete_embeddings_by_filters(self, filters: dict) -> int:
        """Delete embeddings matching multiple filter criteria.
        
        Args:
            filters: Dictionary of filter criteria with keys:
                - url: Source URL to match
                - source: Source type ('slack' or 'offline')
                - date: Date in ISO format (YYYY-MM-DD)
                
        Returns:
            Number of deleted embeddings
        """
        try:
            # Build where clause for ChromaDB
            where_clause = {}
            
            if 'url' in filters and filters['url']:
                where_clause["source_url"] = filters['url']
                
            if 'source' in filters and filters['source']:
                where_clause["source"] = filters['source']
                
            if 'date' in filters and filters['date']:
                where_clause["date"] = filters['date']
                
            if not where_clause:
                logger.warning("No valid filters provided for ChromaDB deletion")
                return 0
                
            # Query to find matching documents
            results = self.collection.get(
                where=where_clause,
                include=["metadatas", "documents"]
            )
            
            if not results or not results["ids"]:
                logger.info(f"No embeddings found matching filters: {filters}")
                return 0
                
            # Delete the matched documents
            self.collection.delete(ids=results["ids"])
            
            logger.info(f"Deleted {len(results['ids'])} embeddings matching filters: {filters}")
            return len(results["ids"])
            
        except Exception as e:
            logger.error(f"Error deleting embeddings by filters: {e}", exc_info=True)
            raise