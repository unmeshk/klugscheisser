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
import logging

logger = logging.getLogger(__name__)

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
        db_user = os.getenv('POSTGRES_USER')
        db_pw = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT')
        db_db = os.getenv('POSTGRES_DB')
        db_ip = os.getenv('POSTGRES_IP')
        self.db_url = f'postgresql://{db_user}:{db_pw}@{db_ip}:{db_port}/{db_db}'
        logger.info(self.db_url)
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
            
    async def delete_entries_by_source_url(self, source_url: str) -> int:
        """Delete all knowledge entries with matching source_url.
        
        Args:
            source_url: The source URL to match against.
            
        Returns:
            Number of entries deleted and their IDs.
        """
        with self.SessionLocal() as session:
            # Debug: Check what URLs actually exist in the database
            all_urls = session.query(KnowledgeEntry.source_url).distinct().all()
            logger.info(f"Available URLs in DB: {all_urls}")
            logger.info(f"Looking for URL: '{source_url}'")
            
            # Find all entries with matching source_url
            entries = session.query(KnowledgeEntry).filter(KnowledgeEntry.source_url == source_url).all()
            
            # Get IDs before deletion for ChromaDB deletion
            entry_ids = [str(entry.id) for entry in entries]
            
            # Delete the entries
            count = session.query(KnowledgeEntry).filter(KnowledgeEntry.source_url == source_url).delete()
            session.commit()
            
            return count, entry_ids
            
    async def delete_entries_by_filters(self, filters: dict) -> tuple:
        """Delete all knowledge entries that match the given filters.
        
        Args:
            filters: A dictionary of filters to apply. Supported keys:
                - url: The source URL to match
                - source: The source type ('slack' or 'offline')
                - date: The date in ISO format (YYYY-MM-DD)
            
        Returns:
            Tuple of (count of deleted entries, list of deleted entry IDs)
        """
        with self.SessionLocal() as session:
            # Start with a base query
            query = session.query(KnowledgeEntry)
            
            # Apply filters
            if 'url' in filters and filters['url']:
                query = query.filter(KnowledgeEntry.source_url == filters['url'])
                
            # For additional_metadata fields (source, date), we need to use JSON operators
            if 'source' in filters and filters['source']:
                # PostgreSQL JSON containment operator @>
                query = query.filter(
                    KnowledgeEntry.additional_metadata.contains({'source': filters['source']})
                )
                
            if 'date' in filters and filters['date']:
                query = query.filter(
                    KnowledgeEntry.additional_metadata.contains({'date': filters['date']})
                )
                
            # Get matching entries before deletion
            entries = query.all()
            
            if not entries:
                logger.info("No entries matched the deletion filters")
                return 0, []
                
            # Get IDs for ChromaDB deletion
            entry_ids = [str(entry.id) for entry in entries]
            
            # Execute deletion
            count = query.delete(synchronize_session=False)
            session.commit()
            
            logger.info(f"Deleted {count} entries matching filters: {filters}")
            return count, entry_ids

    async def search_by_tags(self, tags: List[str]) -> List[KnowledgeEntry]:
        """Search entries by tags."""
        with self.SessionLocal() as session:
            return session.query(KnowledgeEntry).filter(KnowledgeEntry.tags.overlap(tags)).all()

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