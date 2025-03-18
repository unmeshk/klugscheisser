import os
import logging
import json
import csv
import PyPDF2
from typing import List, Dict, Any, AsyncGenerator
from pathlib import Path
import aiofiles
from src.settings import KLUGBOT_TEACHERS
from src.models import KnowledgeEntrySchema

# Configure logging
logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file uploads and content extraction."""
    
    SUPPORTED_FORMATS = {
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.mdx': 'text/markdown+jsx',
        '.rst': 'text/x-rst',
        '.pdf': 'application/pdf'
    }
    
    def __init__(self, knowledge_base, embedding_manager):
        """Initialize with knowledge base and embedding manager."""
        self.kb = knowledge_base
        self.embedding_manager = embedding_manager
        self.max_chars = 5000
        self.overlap_chars = 200

    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized to upload files."""
        return user_id in KLUGBOT_TEACHERS

    async def process_file_upload(self, 
                                file_path: str, 
                                file_type: str,
                                metadata: Dict[str, Any],
                                max_file_size=None) -> Dict[str, Any]:
        """
        Process uploaded file and store knowledge entries.
        Returns summary of processing results.
        """
        try:
            # Check file size
            file_size = Path(file_path).stat().st_size
            if max_file_size and file_size > max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {max_file_size} bytes)")
            
            # Validate file format
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported file format: {file_ext}")

            # Process and store chunks
            total_chunks = 0
            stored_chunks = 0
            failed_chunks = 0
            
            async for chunk in self._extract_content(file_path, file_ext):
                total_chunks += 1
                try:
                    entry = await self._store_chunk(chunk, metadata)
                    if entry:
                        stored_chunks += 1
                    else:
                        failed_chunks += 1
                except Exception as e:
                    logger.error(f"Error storing chunk: {e}")
                    failed_chunks += 1

            return {
                'total_chunks': total_chunks,
                'stored_chunks': stored_chunks,
                'failed_chunks': failed_chunks
            }

        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            raise

    async def _extract_content(self, 
                             file_path: str, 
                             file_ext: str) -> AsyncGenerator[str, None]:
        """Extract content from file and yield chunks."""
        try:
            if file_ext == '.pdf':
                async for chunk in self._process_pdf(file_path):
                    yield chunk
            elif file_ext == '.csv':
                async for chunk in self._process_csv(file_path):
                    yield chunk
            elif file_ext == '.json':
                async for chunk in self._process_json(file_path):
                    yield chunk
            else:  # txt or md
                async for chunk in self._process_text(file_path):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            raise

    async def _process_pdf(self, file_path: str) -> AsyncGenerator[str, None]:
        """Process PDF file and yield text chunks."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                async for chunk in self._chunk_text(text):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise

    async def _process_csv(self, file_path: str) -> AsyncGenerator[str, None]:
        """Process CSV file and yield rows as chunks."""
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
                content = await file.read()
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    # Convert row to formatted text
                    text = "\n".join(f"{k}: {v}" for k, v in row.items())
                    if text.strip():
                        yield text
                    
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            raise

    async def _process_json(self, file_path: str) -> AsyncGenerator[str, None]:
        """Process JSON file and yield entries as chunks."""
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
                content = await file.read()
                data = json.loads(content)
                
                if isinstance(data, list):
                    for item in data:
                        text = json.dumps(item, indent=2)
                        async for chunk in self._chunk_text(text):
                            yield chunk
                else:
                    text = json.dumps(data, indent=2)
                    async for chunk in self._chunk_text(text):
                        yield chunk
                    
        except Exception as e:
            logger.error(f"Error processing JSON: {e}")
            raise

    async def _process_text(self, file_path: str) -> AsyncGenerator[str, None]:
        """Process text file and yield chunks."""
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
                content = await file.read()
                async for chunk in self._chunk_text(content):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error processing text file: {e}")
            raise

    async def _chunk_text(self, text: str) -> AsyncGenerator[str, None]:
        """
        Split text into overlapping chunks based on character count,
        attempting to break at sentence boundaries.
        """
        start = 0
        text_length = len(text)
        
        # Define sentence boundary markers
        sentence_endings = '.!?\n'
        
        while start < text_length:
            # Calculate the ideal end point
            ideal_end = min(start + self.max_chars, text_length)
            
            # If we're not at the end of the text, try to find a sentence boundary
            if ideal_end < text_length:
                # Look for the last sentence boundary within our window
                # First look backwards from ideal_end to ideal_end - overlap
                look_back_start = max(ideal_end - self.overlap_chars, start)
                last_boundary = -1
                
                # Look for the last sentence boundary in our preferred range
                for i in range(ideal_end - 1, look_back_start - 1, -1):
                    if text[i] in sentence_endings:
                        # Check if this is really a sentence end (e.g., not Mr. or U.S.)
                        if not (text[i] == '.' and i > 0 and text[i-1].isupper() and 
                              (i < 2 or text[i-2].isspace())):
                            last_boundary = i + 1
                            break
                
                # If we found a boundary, use it
                if last_boundary != -1:
                    ideal_end = last_boundary
                else:
                    # If no sentence boundary found, look for last space instead
                    for i in range(ideal_end - 1, look_back_start - 1, -1):
                        if text[i].isspace():
                            ideal_end = i + 1
                            break
            
            # Extract the chunk
            chunk = text[start:ideal_end].strip()
            if chunk:  # Only yield non-empty chunks
                yield chunk
            
            # Calculate next start position
            if ideal_end >= text_length:
                break
                
            # Move back by overlap characters from where we ended,
            # but ensure we make forward progress
            start = max(start + 1, ideal_end - self.overlap_chars)
            
            # Try to start at a clean boundary
            while start < text_length and start > 0 and not text[start-1].isspace():
                start += 1

    async def _store_chunk(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Store a content chunk in both databases."""
        try:
            # Get current date in ISO format (YYYY-MM-DD)
            from datetime import date
            current_date = date.today().isoformat()
            
            # Determine source ('slack' for Slack uploads, 'offline' for bulk imports)
            source = 'slack'
            if metadata.get('import_source') == 'bulk_import':
                source = 'offline'
                
            # Create knowledge entry
            entry = KnowledgeEntrySchema(
                content=content,
                slack_username=metadata['user'],
                slack_timestamp=metadata['ts'],
                source_url=metadata['file_url'],
                tags=['imported'],
                additional_metadata={
                    'file_type': metadata['file_type'],
                    'file_name': metadata['file_name'],
                    'import_source': 'file_upload',
                    'source': source,
                    'date': current_date
                }
            )
            entry = await self.kb.create_entry(entry)
            
            # Store embedding
            await self.embedding_manager.store_embedding(
                str(entry.id),
                content,
                {
                    'id': str(entry.id),
                    'slack_username': metadata['user'],
                    'slack_timestamp': metadata['ts'],
                    'source_url': metadata['file_url'],
                    'tags': 'imported',
                    'file_type': metadata['file_type'],
                    'file_name': metadata['file_name'],
                    'import_source': 'file_upload',
                    'source': source,
                    'date': current_date
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing chunk: {e}")
            return False