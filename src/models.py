# models.py

from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, String, DateTime, ARRAY, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
import os
import numpy as np

# Initialize SQLAlchemy
Base = declarative_base()

class KnowledgeEntry(Base):
    """SQLAlchemy model for knowledge entries."""
    __tablename__ = 'knowledge_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    slack_username = Column(String, nullable=False)
    slack_timestamp = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    
    # Tags (stored as array of strings)
    tags = Column(ARRAY(String), nullable=False)
    
    # Metadata can be extended without schema changes
    additional_metadata = Column(JSONB, nullable=True)
    
    # Vector embedding
    embedding = Column(ARRAY(Float), nullable=True)

class KnowledgeEntrySchema(BaseModel):
    """Pydantic model for validation and serialization."""
    id: Optional[uuid.UUID] = None
    content: str
    slack_username: str
    slack_timestamp: str
    source_url: Optional[str] = None
    tags: List[str] = Field(max_length=3)
    additional_metadata: Optional[dict] = None
    embedding: Optional[List[float]] = None

    model_config = {
        "from_attributes": True  # This allows conversion from SQLAlchemy models
    }

    @field_validator('tags')  
    @classmethod 
    def validate_tags(cls, tags):
        if len(tags) > 3:
            raise ValueError('Maximum 3 tags allowed')
        
        # Enforce kebab-case format
        pattern = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        for tag in tags:
            if not pattern.match(tag):
                raise ValueError(f'Tag "{tag}" must be in kebab-case format')
        return tags
    
class KnowledgeBase:
    """Handler for knowledge base operations."""
    
    def __init__(self):
        """Initialize database connection and ChromaDB client."""
        self.db_url = os.getenv('DATABASE_URL')
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize ChromaDB client (placeholder for future integration)
        self.vector_store = None

    def create_tables(self):
        """Create database tables."""
        Base.metadata.create_all(self.engine)

    async def create_entry(self, entry: KnowledgeEntrySchema) -> KnowledgeEntry:
        """Create a new knowledge entry."""
        db_entry = KnowledgeEntry(**entry.dict(exclude_unset=True))
        
        with self.SessionLocal() as session:
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
        
        return db_entry

    async def get_entry(self, entry_id: uuid.UUID) -> Optional[KnowledgeEntry]:
        """Retrieve a knowledge entry by ID."""
        with self.SessionLocal() as session:
            return session.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()

    async def update_entry(self, entry_id: uuid.UUID, updated_data: dict) -> Optional[KnowledgeEntry]:
        """Update a knowledge entry."""
        with self.SessionLocal() as session:
            entry = session.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
            if entry:
                for key, value in updated_data.items():
                    setattr(entry, key, value)
                entry.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(entry)
            return entry

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        """Delete a knowledge entry."""
        with self.SessionLocal() as session:
            entry = session.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
            if entry:
                session.delete(entry)
                session.commit()
                return True
            return False

    async def search_by_tags(self, tags: List[str]) -> List[KnowledgeEntry]:
        """Search entries by tags."""
        with self.SessionLocal() as session:
            return session.query(KnowledgeEntry).filter(KnowledgeEntry.tags.overlap(tags)).all()

    async def setup_vector_store(self):
        """
        Placeholder for ChromaDB integration.
        This will be implemented in a future update to:
        1. Initialize ChromaDB connection
        2. Create collection for embeddings
        3. Set up indexing and similarity search
        """
        pass

    async def semantic_search(self, query: str, limit: int = 5) -> List[KnowledgeEntry]:
        """
        Placeholder for semantic search implementation.
        Will be implemented to:
        1. Generate embedding for query
        2. Perform similarity search in ChromaDB
        3. Return matched entries from PostgreSQL
        """
        pass

# Stub for connecting with Slack bot
async def process_knowledge_command(kb: KnowledgeBase, command: str, message_data: dict) -> str:
    """
    Process knowledge-related commands from Slack.
    This stub will be expanded to handle commands like:
    - /store (store new knowledge)
    - /search (search by tags or semantic similarity)
    - /update (update existing entry)
    - /delete (delete entry)
    """
    # Implementation will be added in future update
    pass