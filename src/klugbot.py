import os
import re
import logging 
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from models import KnowledgeBase, KnowledgeEntrySchema
from embeddingmanager import EmbeddingManager


logger = logging.getLogger(__name__)

class KlugBot:
    """Slack bot for knowledge management."""

    def __init__(self):
        """Initialize the Slack bot with necessary tokens and configurations."""
        self.bolt_app = AsyncApp(
            token=os.getenv("SLACK_BOT_TOKEN"),
            signing_secret=os.getenv("SLACK_SIGNING_SECRET")        )
        self.handler = AsyncSlackRequestHandler(self.bolt_app)
        self.kb = KnowledgeBase()
        self.embedding_manager = EmbeddingManager()
        
        # Command patterns
        self.learn_pattern = re.compile(
            r'<@[A-Z0-9]+>\s+learn\s+(?P<content>.+)',
            re.IGNORECASE
        )
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Set up event listeners for Slack events."""
        
        @self.bolt_app.event("app_mention")
        async def handle_mention(event: Dict[str, Any], say):
            """Handle when the bot is mentioned in a channel."""
            try:
                await self._process_mention(event, say)
            except Exception as e:
                logger.error(f"Error processing mention: {e}")
                await say("Sorry, I encountered an error processing your request.")

    async def _process_mention(self, event: dict, say):
        """Process mention events and route to appropriate handlers."""
        try:
            text = event.get('text', '')
            
            # Check for learn command
            if learn_match := self.learn_pattern.match(text):
                await self._handle_learn_command(event, say, learn_match)
                return
            
            # Default response if no command matches
            await say(
                text="Hello! I can help you manage knowledge. Try '@klug-bot learn <something>'",
                thread_ts=event.get('ts')
            )
            
        except Exception as e:
            logger.error(f"Error in message processing: {e}", exc_info=True)
            raise

    async def _handle_learn_command(self, event: dict, say, match):
        """Handle the learn command and store new knowledge."""
        try:
            content = match.group('content').strip()
            if not content:
                await say(
                    text="I couldn't understand what you want me to learn. Please provide some content.",
                    thread_ts=event.get('ts')
                )
                return
            
            # Extract metadata and store knowledge
            metadata = self._extract_metadata(event)
            entry = await self._store_knowledge(content, metadata)
            
            # Generate and store embedding
            await self._store_embedding(entry, content, metadata)
            
            await say(
                text=f"I've learned that: {content}\nStored with ID: {entry.id}",
                thread_ts=event.get('ts')
            )
            
        except Exception as e:
            logger.error(f"Error handling learn command: {e}", exc_info=True)
            await say(
                text="Sorry, I encountered an error while trying to learn that.",
                thread_ts=event.get('ts')
            )

    def _extract_metadata(self, event: dict) -> dict:
        """Extract metadata from Slack event."""
        return {
            'slack_username': event.get('user', ''),
            'slack_timestamp': event.get('ts', ''),
            'channel': event.get('channel', ''),
            'team': event.get('team', ''),
            'source_url': self._construct_message_link(event)
        }
    
    def _construct_message_link(self, event: dict) -> Optional[str]:
        """Construct a link to the Slack message."""
        try:
            team = event.get('team')
            channel = event.get('channel')
            timestamp = event.get('ts', '').replace('.', '')
            
            if all([team, channel, timestamp]):
                return f"https://slack.com/archives/{channel}/p{timestamp}"
        except Exception as e:
            logger.warning(f"Could not construct message link: {e}")
        
        return None

    def _extract_tags(self, content: str) -> list:
        """Extract hashtags from content and convert to kebab-case tags."""
        # Find hashtags in content
        hashtags = re.findall(r'#(\w+)', content)
        
        # Convert to kebab-case and limit to 3
        tags = [
            re.sub(r'([a-z])([A-Z])', r'\1-\2', tag).lower()
            for tag in hashtags
        ][:3]
        
        # If no hashtags found, try to generate a default tag
        if not tags:
            # Simple example: use first word as tag if it's not a stopword
            first_word = content.split()[0].lower()
            if first_word not in {'the', 'a', 'an', 'in', 'on', 'at', 'to'}:
                tags = [first_word]
        
        return tags

    async def _store_knowledge(self, content: str, metadata: dict) -> KnowledgeEntrySchema:
        """Store knowledge entry in the database."""
        try:
            # Extract any hashtags as potential tags
            tags = self._extract_tags(content)
            
            entry = KnowledgeEntrySchema(
                content=content,
                slack_username=metadata['slack_username'],
                slack_timestamp=metadata['slack_timestamp'],
                source_url=metadata['source_url'],
                tags=tags,
                additional_metadata={
                    'channel': metadata['channel'],
                    'team': metadata['team']
                }
            )
            
            stored_entry = await self.kb.create_entry(entry)
            logger.info(f"Stored knowledge entry with ID: {stored_entry.id}")
            return stored_entry
            
        except Exception as e:
            logger.error(f"Error storing knowledge entry: {e}", exc_info=True)
            raise

    async def _store_embedding(self, entry, content: str, metadata: dict):
        """Generate and store embedding for the content."""
        try:
            # Prepare metadata for ChromaDB
            chroma_metadata = {
                'id': str(entry.id),
                'slack_username': metadata['slack_username'],
                'slack_timestamp': metadata['slack_timestamp'],
                'channel': metadata['channel'],
                'team': metadata['team'],
                'source_url': metadata['source_url'],
                'tags': ','.join(entry.tags) if entry.tags else ''
            }
            
            # Generate and store embedding
            embedding = await self.embedding_manager.store_embedding(
                str(entry.id),
                content,
                chroma_metadata
            )
            
            # Update PostgreSQL entry with the embedding
            await self.kb.update_entry(
                entry.id,
                {'embedding': embedding}
            )
            
            logger.info(f"Stored embedding for entry: {entry.id}")
            
        except Exception as e:
            logger.error(f"Error storing embedding: {e}", exc_info=True)
            raise

    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            self.embedding_manager.chroma_client.persist()
            logger.info("ChromaDB state persisted successfully")
        except Exception as e:
            logger.error(f"Error persisting ChromaDB state: {e}")