import os
import re
import logging 
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from typing import Dict, Any, Optional
from models import KnowledgeBase, KnowledgeEntrySchema
from embeddingmanager import EmbeddingManager
from queryhandler import QueryHandler
from filehandler import FileHandler
from settings import MAX_FILE_SIZE


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
        self.query_handler = QueryHandler(self.embedding_manager)
        self.file_handler = FileHandler(self.kb, self.embedding_manager)
        
        # Command patterns
        self.learn_pattern = re.compile(
            r'<@[A-Z0-9]+>\s+learn(?:\s+(?P<content>.+))?',
            re.IGNORECASE
        )
        self.query_pattern = re.compile(
            r'<@[A-Z0-9]+>\s+(?!learn\s+)(?P<query>.+)',
            re.IGNORECASE
        )

        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Set up event listeners for Slack events."""
        
        @self.bolt_app.event("app_mention")
        async def handle_mention(event, say, client):
            """Handle when the bot is mentioned in a channel."""
            try:
                # First check if this is a learn command
                is_learn_command = bool(self.learn_pattern.match(event.get('text', '')))
                
                if is_learn_command:
                    # Check authorization for learn commands
                    if not self.file_handler.is_authorized(event.get('user')):
                        await say(
                            text="Sorry, you are not authorized to teach me new things.",
                            thread_ts=event.get('ts')
                        )
                        return
                    
                    # Check if there's a file to process
                    if 'files' in event:
                        await say(
                            text="Found a file to process",
                            thread_ts=event.get('ts')
                        )
                        await self._process_file_upload(event, say, client)
                        return
                    
                    # No file, process as regular learn command
                    await self._process_mention(event, say)
                    return
                
                # Not a learn command, process as regular mention
                await self._process_mention(event, say)
                
            except Exception as e:
                logger.error(f"Error processing mention: {e}", exc_info=True)
                await say(
                    text="Sorry, I encountered an error processing your request.",
                    thread_ts=event.get('ts')
                )    

    async def _process_mention(self, event: dict, say):
        """Process mention events and route to appropriate handlers."""
        try:
            text = event.get('text', '')
            
            # Check for learn command
            if learn_match := self.learn_pattern.match(text):
                await self._handle_learn_command(event, say, learn_match)
                return
            
            # Check for query
            if query_match := self.query_pattern.match(text):
                await self._handle_query_command(event, say, query_match)
                return
            
            # Default response if no command matches
            await say(
                text="Hello! I can help you manage knowledge. Try '@klug-bot <something>' to learn about <something>",
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

    async def _handle_query_command(self, event: dict, say, match):
        """Handle knowledge query and generate response."""
        try:
            query = match.group('query').strip()
            if not query:
                await say(
                    text="I couldn't understand your question. Please try asking something specific.",
                    thread_ts=event.get('ts')
                )
                return
            
            # Process query
            response, entries = await self.query_handler.process_query(query)
            
            # Format response for Slack
            formatted_response = self.query_handler.format_slack_response(response, entries)
            
            await say(
                text=formatted_response,
                thread_ts=event.get('ts')
            )
            
        except Exception as e:
            logger.error(f"Error handling query: {e}", exc_info=True)
            await say(
                text="Sorry, I encountered an error while trying to answer that question.",
                thread_ts=event.get('ts')
            )

    async def _process_file_upload(self, event: dict, say, client):
        """Process an uploaded file."""
        try:
            # Get file info from the first file (we'll process one file at a time)
            file = event['files'][0]
            
            # Get file info and download URL
            file_info = await client.files_info(file=file['id'])
            download_url = file_info['file']['url_private_download']
            
            # Download file
            temp_path = f"/tmp/{file['name']}"
            try:
                # Download the file using the bot's token for authentication
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        download_url,
                        headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                    ) as resp:
                        if resp.status != 200:
                            raise ValueError(f"Failed to download file: {resp.status}")
                        content = await resp.read()
                
                # Save file temporarily
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                # Process file
                metadata = {
                    'user': event.get('user'),
                    'ts': event.get('ts'),
                    'file_url': file.get('url_private'),
                    'file_type': file.get('filetype'),
                    'file_name': file.get('name')
                }
                
                results = await self.file_handler.process_file_upload(
                    temp_path,
                    file['filetype'],
                    metadata,
                    MAX_FILE_SIZE
                )
                
                # Send summary
                summary = (
                    f"File processing complete:\n"
                    f"• Total chunks: {results['total_chunks']}\n"
                    f"• Successfully stored: {results['stored_chunks']}\n"
                    f"• Failed: {results['failed_chunks']}"
                )
                
                await say(
                    text=summary,
                    thread_ts=event.get('ts')
                )
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error processing file upload: {e}", exc_info=True)
            await say(
                text="Sorry, I encountered an error while processing the file.",
                thread_ts=event.get('ts')
            )


    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            self.embedding_manager.chroma_client.persist()
            logger.info("ChromaDB state persisted successfully")
        except Exception as e:
            logger.error(f"Error persisting ChromaDB state: {e}")