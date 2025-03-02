import os
import re
import logging
import base64
import requests
import aiohttp
import io
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from typing import Dict, Any, Optional, List, Tuple
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
            r'<@[A-Z0-9]+>\s+--learn(?:\s+(?P<content>.+))?',
            re.IGNORECASE
        )
        self.delete_pattern = re.compile(
            r'<@[A-Z0-9]+>\s+--delete(?:\s+(?P<content>.+))?',
            re.IGNORECASE
        )
        self.query_pattern = re.compile(
            r'<@[A-Z0-9]+>\s+(?!--learn\s+)(?!--delete\s+)(?P<query>.+)',
            re.IGNORECASE
        )

        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Set up event listeners for Slack events."""
        
        @self.bolt_app.event("app_mention")
        async def handle_mention(event, say, client):
            """Handle when the bot is mentioned in a channel."""
            try:
                text = event.get('text', '')

                # First check if this is a learn command
                if learn_match := self.learn_pattern.match(text):
                    # Check authorization for learn commands
                    if not self.file_handler.is_authorized(event.get('user')):
                        await say(
                            text="Sorry, you are not authorized to teach me new things.",
                            thread_ts=event.get('ts')
                        )
                        return
                    
                    # Check if there's a file to process
                    if 'files' in event:
                        logger.info('Found a file attached. Processing...')
                        await self._process_file_upload(event, say, client)
                        return
                    
                    # No file, process as regular learn command
                    await self._handle_learn_command(event, say, learn_match)
                    return
                
                # Check for delete command
                if delete_match := self.delete_pattern.match(text):
                    # Check authorization for delete commands (same as learn)
                    if not self.file_handler.is_authorized(event.get('user')):
                        await say(
                            text="Sorry, you are not authorized to delete entries.",
                                thread_ts=event.get('ts')
                        )
                        return
                    
                    await self._handle_delete_command(event, say, delete_match)
                    return


                # Not a learn command or a delete command, process as a regular query
                await self._process_mention(event, say, client)
                
            except Exception as e:
                logger.error(f"Error processing mention: {e}", exc_info=True)
                await say(
                    text="Sorry, I encountered an error processing your request.",
                    thread_ts=event.get('ts')
                )    

    async def _process_mention(self, event: dict, say, client=None):
        """Process mention events and route to appropriate handlers."""
        try:
            text = event.get('text', '')
            
            # Check for query
            if query_match := self.query_pattern.match(text):
                await self._handle_query_command(event, say, query_match, client)
                return
            
            # Default response if no command matches
            await say(
                text="""Hello! I can help you manage knowledge. 
                Use these commands:\n• '@klug-bot --learn <information>' to teach me something\n
                • '@klug-bot --delete <url>' to delete entries by URL\n
                • '@klug-bot <question>' to ask me a question. 
                Learn and delete are available to authorized users only.""",
                thread_ts=event.get('ts')
            )
            
        except Exception as e:
            logger.error(f"Error in message processing: {e}", exc_info=True)
            raise

    async def _handle_learn_command(self, event: dict, say, match):
        """Handle the learn command and store new knowledge."""
        try:
            content = match.group('content')
            if not content:
                await say(
                    text="I couldn't understand what you want me to learn. Usage: @klug-bot --learn <content to learn>.",
                    thread_ts=event.get('ts')
                )
                return
            
            content = content.strip()
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
            
            # Get current date in ISO format (YYYY-MM-DD)
            from datetime import date
            current_date = date.today().isoformat()
            
            entry = KnowledgeEntrySchema(
                content=content,
                slack_username=metadata['slack_username'],
                slack_timestamp=metadata['slack_timestamp'],
                source_url=metadata['source_url'],
                tags=tags,
                additional_metadata={
                    'channel': metadata['channel'],
                    'team': metadata['team'],
                    'source': 'slack',
                    'date': current_date
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
                'tags': ','.join(entry.tags) if entry.tags else '',
                'source': entry.additional_metadata.get('source', 'slack'),
                'date': entry.additional_metadata.get('date', '')
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

    async def _get_slack_message_content(self, message, client):
        """ Returns the text and images in a message """
        text_content = message.get('text', '')
        
        image_content = []        
        if 'files' in message:
            for file in message['files']:
                if file['mimetype'].startswith('image/'):
                    headers = {'Authorization': f'Bearer {client.token}'}

                    url = file.get('url_private_download', file['url_private'])
                    logging.info(f"Downloading image from {url}")

                    image_response = requests.get(
                        url, 
                        headers=headers,
                        stream = True
                    )

                    if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                        image_data = BytesIO(image_response.content)
                        image_data.seek(0)
                        try:
                            img = Image.open(image_data)
                        except UnidentifiedImageError:
                            logging.error("Unable to identify image file.")
                            continue  # Skip this file if it's not a valid image

                        # Convert to RGB if needed
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Resize if larger than 512px
                        max_size = 512
                        if max(img.size) > max_size:
                            ratio = max_size / max(img.size)
                            new_size = tuple(int(dim * ratio) for dim in img.size)
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Save compressed image
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=70, optimize=True)
                        base64_image = base64.b64encode(output.getvalue()).decode()
                        
                        # Add image in Claude API format
                        image_content.append(base64_image)

        return text_content, image_content

    async def _get_slack_thread_history(self, client, channel_id, thread_ts):
        """ Get the slack message history from the thread"""
        try:
            reply = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            messages = reply["messages"]
            
            text_contents = []
            image_contents = []
            
            for msg in messages:
                text_content, image_content = await self._get_slack_message_content(msg,client)
                text_contents.append(text_content)
                image_contents.append(image_content)
            
            return text_contents, image_contents
        
        except Exception as e:
            logger.error(f"Error getting thread history: {e}")
            return "", []

    async def _handle_query_command(self, event: dict, say, match, client=None):
        """Handle knowledge query and generate response."""
        try:
            query = match.group('query').strip()
            if not query:
                await say(
                    text="I couldn't understand your question. Please try asking something specific.",
                    thread_ts=event.get('ts')
                )
                return
            
            channel_id = event["channel"]
            thread_ts = event.get("thread_ts", None)
            # If this is part of a thread, get the thread history
            if thread_ts:
                text_contents, image_contents = await self._get_slack_thread_history(client, channel_id, thread_ts)
            else:
                # If not in a thread, just use the current message as context
                text_content, image_content = await self._get_slack_message_content(event, client)
                text_contents = [text_content]
                image_contents = [image_content]
                    
            for t,i in zip(text_contents,image_contents):
                logger.info(f'text_content:{t} and number of images: {len(i)}')
            
            response, entries = await self.query_handler.process_query(text_contents, image_contents)
            
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


    async def _handle_delete_command(self, event: dict, say, match):
        """Handle the delete command to remove entries based on filter criteria."""
        try:
            # Extract the content from the match
            content = match.group('content')
            
            # Show help message when no content is provided
            # or when content is empty after stripping
            if content is None or not content.strip():
                await self._show_delete_help(say, event.get('ts'))
                return
            
            content = content.strip()
            
            # Parse filter criteria
            filters = self._parse_delete_filters(content)
            
            if not filters:
                await self._show_delete_help(say, event.get('ts'), prefix="No valid filters found.")
                return
                
            logger.info(f"Deleting with filters: {filters}")
            
            # Delete from both databases using filters
            pg_count, entry_ids = await self.kb.delete_entries_by_filters(filters)
            
            # Delete from ChromaDB using the entry IDs first (more reliable)
            chroma_count_by_ids = 0
            if entry_ids:
                chroma_count_by_ids = await self.embedding_manager.delete_embeddings_by_ids(entry_ids)
            
            # Also try deletion by filters directly in case there are any orphaned entries
            chroma_count_by_filters = await self.embedding_manager.delete_embeddings_by_filters(filters)
            
            # Total ChromaDB deletions (should be same as pg_count in normal operation)
            total_chroma_deletions = max(chroma_count_by_ids, chroma_count_by_filters)
            
            # Generate filter description for user feedback
            filter_desc = self._format_filter_description(filters)
            
            # Report results
            if pg_count > 0 or total_chroma_deletions > 0:
                await say(
                    text=f"Successfully deleted entries matching {filter_desc}\n"
                         f"• Entries removed from PostgreSQL: {pg_count}\n"
                         f"• Entries removed from vector database: {total_chroma_deletions}",
                    thread_ts=event.get('ts')
                )
            else:
                await say(
                    text=f"No entries found matching {filter_desc}",
                    thread_ts=event.get('ts')
                )
                
        except Exception as e:
            logger.error(f"Error handling delete command: {e}", exc_info=True)
            await say(
                text="Sorry, I encountered an error while trying to delete entries.",
                thread_ts=event.get('ts')
            )
            
    async def _show_delete_help(self, say, thread_ts, prefix=""):
        """Show help for the delete command."""
        message = "Delete usage examples:\n" \
                 "• `@klug-bot --delete url:https://example.com`\n" \
                 "• `@klug-bot --delete source:slack`\n" \
                 "• `@klug-bot --delete date:2025-02-22`\n" \
                 "• `@klug-bot --delete source:offline date:2025-02-22`"
        
        if prefix:
            message = f"{prefix} {message}"
            
        await say(
            text=message,
            thread_ts=thread_ts
        )
            
    def _parse_delete_filters(self, content: str) -> dict:
        """Parse delete command content into filter criteria.
        
        Handles formats like:
        - url:https://example.com
        - source:slack
        - date:2025-02-22
        - source:offline date:2025-01-01
        
        Returns:
            Dictionary of filter criteria
        """
        filters = {}
        
        # Match patterns like key:value
        filter_pattern = re.compile(r'(url|source|date):([^\s]+)')
        matches = filter_pattern.findall(content)
        
        for key, value in matches:
            # Clean up URL (Slack adds angle brackets)
            if key == 'url' and value.startswith('<') and value.endswith('>'):
                value = value[1:-1]
                
            filters[key] = value
            
        # If no structured filters found but content looks like a URL, 
        # treat it as the legacy format (just a URL)
        if not filters and ('http://' in content or 'https://' in content):
            url = content
            if url.startswith('<') and url.endswith('>'):
                url = url[1:-1]
            filters['url'] = url
            
        return filters
        
    def _format_filter_description(self, filters: dict) -> str:
        """Format filter criteria for user-friendly display."""
        if not filters:
            return "no criteria"
            
        parts = []
        if 'url' in filters:
            parts.append(f"URL '{filters['url']}'")
        if 'source' in filters:
            parts.append(f"source '{filters['source']}'")
        if 'date' in filters:
            parts.append(f"date '{filters['date']}'")
            
        # Handle any number of parts elegantly
        if len(parts) == 1:
            return parts[0]
        else:
            # Join with commas and add "and" before the last item
            return f"{', '.join(parts[:-1])} and {parts[-1]}"
            
    async def _process_current_message_images(self, event: dict, client) -> List[str]:
        """Process images attached to the current message.
        
        Args:
            event: Slack event containing the message data
            client: Slack client for API calls
            
        Returns:
            List of base64 encoded images
        """
        try:
            # Check if the message has attached files
            if "files" not in event:
                logger.debug(f"No files in current message with ts: {event.get('ts')}")
                return []
                
            encoded_images = []
            
            for file in event["files"]:
                # Only process image files
                if file.get("mimetype", "").startswith("image/"):
                    image_url = file.get("url_private")
                    if image_url:
                        encoded_img = await self._resize_and_encode_image(image_url)
                        if encoded_img:
                            encoded_images.append(encoded_img)
                            logger.info(f"Processed image from current message: {file.get('name')} (ts: {event.get('ts')})")
                        else:
                            logger.warning(f"Failed to encode image: {file.get('name')} (ts: {event.get('ts')})")
                else:
                    logger.debug(f"Skipping non-image file: {file.get('mimetype')} (ts: {event.get('ts')})")
            
            return encoded_images
            
        except Exception as e:
            logger.error(f"Error processing current message images: {e}")
            return []
    
    async def _resize_and_encode_image(self, image_url: str, max_size: int = 512) -> Optional[str]:
        """Resize an image and encode it as base64.
        
        Args:
            image_url: The URL of the image to resize and encode
            max_size: The maximum size for the longest side of the image
            
        Returns:
            A base64-encoded string of the resized image, or None if an error occurred
        """
        try:
            # Download the image from Slack
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    image_url,
                    headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download image: {resp.status}")
                        return None
                    
                    image_data = await resp.read()
            
            # Open and resize the image
            with Image.open(io.BytesIO(image_data)) as img:
                # Calculate new dimensions while maintaining aspect ratio
                width, height = img.size
                if width > height:
                    if width > max_size:
                        new_width = max_size
                        new_height = int(height * (max_size / width))
                    else:
                        new_width, new_height = width, height
                else:
                    if height > max_size:
                        new_height = max_size
                        new_width = int(width * (max_size / height))
                    else:
                        new_width, new_height = width, height
                
                # Resize the image
                resized_img = img.resize((new_width, new_height))
                
                # Convert image with alpha channel (RGBA) to RGB before saving as JPEG
                if resized_img.mode == 'RGBA':
                    # Create a white background
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    # Paste the image on the background using alpha as mask
                    background.paste(resized_img, mask=resized_img.split()[3])
                    resized_img = background
                elif resized_img.mode != 'RGB':
                    # Convert any other mode to RGB
                    resized_img = resized_img.convert('RGB')
                
                # Convert to JPEG to save space and encode as base64
                buffer = io.BytesIO()
                resized_img.save(buffer, format="JPEG")
                buffer.seek(0)
                
                # Encode as base64
                encoded_img = base64.b64encode(buffer.read()).decode('utf-8')
                
                return encoded_img
        
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
            
    async def _fetch_thread_messages(self, client, channel_id: str, thread_ts: str, current_ts: str = None) -> List[Dict]:
        """Fetch all messages in a thread.
        
        Args:
            client: Slack client
            channel_id: Channel ID where the thread exists
            thread_ts: Thread timestamp
            current_ts: The timestamp of the current message to exclude
            
        Returns:
            List of messages in the thread
        """
        try:
            response = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            
            if not response["ok"]:
                logger.error(f"Error fetching thread: {response['error']}")
                return []
                
            # Get all messages from the thread
            messages = response.get("messages", [])
            if not messages:
                return []
                
            # Filter out the current message if provided
            if current_ts:
                messages = [msg for msg in messages if msg.get("ts") != current_ts]
                
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching thread messages: {e}")
            return []
            
    async def _process_thread_context(self, client, event: dict) -> Tuple[str, List[str]]:
        """Process a Slack thread to create context for the LLM.
        
        Args:
            client: Slack client
            event: Slack event data
            
        Returns:
            Tuple of (thread context text, list of base64 encoded images)
        """
        thread_ts = event.get("thread_ts")
        if not thread_ts:
            # This message is not in a thread
            return "", []
            
        channel_id = event.get("channel")
        current_ts = event.get("ts")
        
        # Fetch thread messages, excluding the current message
        messages = await self._fetch_thread_messages(client, channel_id, thread_ts, current_ts)
        if not messages:
            return "", []
            
        # Process thread messages into context
        thread_context = []
        image_contexts = []
        
        for msg in messages:
            user_id = msg.get("user", "Unknown")
            text = msg.get("text", "")
            
            # Skip bot mention tags in previous messages to avoid confusion
            text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
            
            # Add user message to context
            if text:
                # Get user's real name if possible
                try:
                    user_info = await client.users_info(user=user_id)
                    user_name = user_info.get("user", {}).get("real_name", user_id)
                except:
                    user_name = f"User {user_id}"
                
                thread_context.append(f"{user_name}: {text}")
            
            # Process any images in the message
            if "files" in msg:
                for file in msg["files"]:
                    if file.get("mimetype", "").startswith("image/"):
                        image_url = file.get("url_private")
                        if image_url:
                            encoded_img = await self._resize_and_encode_image(image_url)
                            if encoded_img:
                                image_contexts.append(encoded_img)
                                thread_context.append(f"{user_name}: [Shared an image]")
                                logger.info(f"Added image from thread message with ts: {msg.get('ts')}")
        
        return "\n".join(thread_context), image_contexts
            
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        try:
            self.embedding_manager.chroma_client.persist()
            logger.info("ChromaDB state persisted successfully")
        except Exception as e:
            logger.error(f"Error persisting ChromaDB state: {e}")