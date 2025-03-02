# queryhandler.py

import os
import logging
import base64
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from settings import (
    MAX_RESULTS,
    QUERY_PROMPT_TEMPLATE,
    QUERY_WITH_CONTEXT_TEMPLATE,
    QUERY_WITH_IMAGES_TEMPLATE,
    MAX_OUTPUT_TOKENS,
    LLM_MODEL
)

# Configure logging
logger = logging.getLogger(__name__)

class QueryHandler:
    """Handles knowledge retrieval and response generation."""
    
    def __init__(self, embedding_manager):
        """Initialize with embedding manager and LLM."""
        self.embedding_manager = embedding_manager

        # Get API key and verify it exists
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it to use the Gemini API."
            )
        
        # Configure Gemini client
        self.client = genai.Client(api_key=api_key)

    async def process_query(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Process a knowledge query and return a response.
        Returns tuple of (response text, list of matching entries)
        """
        try:
            # Generate embedding for query
            query_embedding = await self.embedding_manager.generate_embedding(query)
            
            # Search ChromaDB
            results = self.embedding_manager.collection.query(
                query_embeddings=[query_embedding],
                n_results=MAX_RESULTS,
                include=['metadatas', 'documents', 'distances']
            )

            print(f'Retrived {len(results["ids"][0])} matching info from Chroma.')
            #print(results)
            
            # Check if we have any good matches
            if not results['ids'][0]: # or results['distances'][0][0] > SIMILARITY_THRESHOLD:
                return "I don't know the answer to that question. <end>", []
            
            # Format context from results
            contexts = []
            entries = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                contexts.append(f"Content {i+1}: {doc}")
                entries.append({
                    'id': metadata['id'],
                    'content': doc,
                    'metadata': metadata
                })
            
            if not contexts:
                return "I don't know the answer to that question.", []
            
            # Generate response using Gemini
            response = await self._generate_response(query, contexts)
            
            return response, entries
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return "Sorry, I encountered an error while trying to answer that question.", []

    async def process_query_with_context(self, query: str, thread_context: str = "", images: List[str] = None) -> Tuple[str, List[Dict]]:
        """
        Process a knowledge query with conversation thread context and/or images.
        Returns tuple of (response text, list of matching entries)
        """
        try:
            # Check if we have images or thread context
            has_thread = bool(thread_context and thread_context.strip())
            has_images = bool(images and len(images) > 0)
            
            if not has_thread and not has_images:
                logger.warning("process_query_with_context called but no thread context or images provided")
                return await self.process_query(query)
            
            # Generate embedding for query
            query_embedding = await self.embedding_manager.generate_embedding(query)
            
            # Search ChromaDB
            results = self.embedding_manager.collection.query(
                query_embeddings=[query_embedding],
                n_results=MAX_RESULTS,
                include=['metadatas', 'documents', 'distances']
            )

            logger.info(f'Retrieved {len(results["ids"][0])} matching info from Chroma.')
            
            # Format context from results
            contexts = []
            entries = []
            
            if results['ids'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    contexts.append(f"Content {i+1}: {doc}")
                    entries.append({
                        'id': metadata['id'],
                        'content': doc,
                        'metadata': metadata
                    })
            
            # Check what kind of context we have
            if not results['ids'][0] and not has_thread and not has_images:
                # No knowledge, no thread, no images
                return "I don't know the answer to that question.", []
                
            # Generate appropriate response based on available context
            if has_thread:
                # With thread context (may also have images)
                response = await self._generate_response_with_context(query, contexts, thread_context, images)
            elif has_images:
                # Images only, no thread context
                response = await self._generate_response_with_images(query, contexts, images)
            else:
                # Shouldn't happen, but fallback to standard query
                response = await self._generate_response(query, contexts)
                
            return response, entries
            
        except Exception as e:
            logger.error(f"Error processing query with context: {e}", exc_info=True)
            return "Sorry, I encountered an error while trying to answer that question.", []

    async def _generate_response(self, query: str, contexts: List[str]) -> str:
        """Generate a response using Gemini."""
        try:
            # Format the prompt using the template
            prompt = QUERY_PROMPT_TEMPLATE.format(
                query=query,
                contexts='\n'.join(contexts)
            )

            logger.debug(prompt)

            # Generate response
            response = await self.client.aio.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more focused responses
                    candidate_count=1,
                    stop_sequences=[],
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
            )

            return response.text
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}", exc_info=True)
            return "Sorry, I encountered an error while generating a response."
            
    async def _generate_response_with_context(self, query: str, contexts: List[str], thread_context: str, images: List[str] = None, message_history: List[dict] = None) -> str:
        """Generate a response using Gemini with thread context, message history, and optional images."""
        try:
            # Format the prompt using the template with thread context
            prompt = QUERY_WITH_CONTEXT_TEMPLATE.format(
                query=query,
                contexts='\n'.join(contexts) if contexts else "No relevant knowledge entries found.",
                thread_context=thread_context
            )

            logger.debug(prompt)
            
            # Prepare structured conversation for the API call
            if message_history and len(message_history) > 0:
                # Create a structured conversation with role-based parts
                content_items = []
                
                # Add previous messages with their respective images
                for message in message_history:
                    if message["role"] == "user":
                        parts = [message["content"]]
                        # Add image if this message had one
                        if "image" in message and message["image"]:
                            parts.append(
                                types.Part.from_bytes(
                                    data=base64.b64decode(message["image"]), 
                                    mime_type="image/jpeg"
                                )
                            )
                        content_items.append({"role": "user", "parts": parts})
                    else:
                        content_items.append({"role": "model", "parts": [message["content"]]})
                
                # Add the current message with its image
                current_parts = [prompt]
                if images and len(images) > 0:
                    for img_data in images:
                        current_parts.append(
                            types.Part.from_bytes(
                                data=base64.b64decode(img_data), 
                                mime_type="image/jpeg"
                            )
                        )
                content_items.append({"role": "user", "parts": current_parts})
            else:
                # If no message history, handle as before
                content_items = []
                
                # Handle images if provided
                if images and len(images) > 0:
                    # For small payloads (< 20MB total)
                    if self._is_small_payload(images):
                        # Add text prompt
                        content_items.append(prompt)
                        
                        # Add image parts using Part.from_bytes for base64 encoded images
                        for img_data in images:
                            content_items.append(
                                types.Part.from_bytes(data=base64.b64decode(img_data), mime_type="image/jpeg")
                            )
                    else:
                        # For large payloads, use File API
                        file_refs = []
                        for img_data in images:
                            # Create a temporary file from base64 data
                            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                                temp_file.write(base64.b64decode(img_data))
                                temp_file_path = temp_file.name
                            
                            # Upload to File API
                            file_ref = self.client.files.upload(file=temp_file_path)
                            file_refs.append(file_ref)
                            
                            # Clean up the temporary file
                            os.unlink(temp_file_path)
                        
                        # Add text prompt
                        content_items.append(prompt)
                        
                        # Add file references
                        content_items.extend(file_refs)
                else:
                    # Text-only - just use the prompt
                    content_items = [prompt]
            
            # Generate response
            print(content_items)
            response = await self.client.aio.models.generate_content(
                model=LLM_MODEL,
                contents=content_items,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    candidate_count=1,
                    stop_sequences=[],
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
            )

            return response.text
            
        except Exception as e:
            logger.error(f"Error generating LLM response with context: {e}", exc_info=True)
            return "Sorry, I encountered an error while generating a response."
    
    async def _generate_response_with_images(self, query: str, contexts: List[str], images: List[str]) -> str:
        """Generate a response using Gemini with images but no thread context."""
        try:
            # Format the prompt using the template for images without thread context
            prompt = QUERY_WITH_IMAGES_TEMPLATE.format(
                query=query,
                contexts='\n'.join(contexts) if contexts else "No relevant knowledge entries found."
            )

            logger.debug(prompt)
            
            # Prepare content items for the API call
            content_items = []
            
            # Handle images
            if self._is_small_payload(images):
                # Add text prompt
                content_items.append(prompt)
                
                # Add image parts using Part.from_bytes for base64 encoded images
                for img_data in images:
                    content_items.append(
                        types.Part.from_bytes(data=base64.b64decode(img_data), mime_type="image/jpeg")
                    )
            else:
                # For large payloads, use File API
                file_refs = []
                for img_data in images:
                    # Create a temporary file from base64 data
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        temp_file.write(base64.b64decode(img_data))
                        temp_file_path = temp_file.name
                    
                    # Upload to File API
                    file_ref = self.client.files.upload(file=temp_file_path)
                    file_refs.append(file_ref)
                    
                    # Clean up the temporary file
                    os.unlink(temp_file_path)
                
                # Add text prompt
                content_items.append(prompt)
                
                # Add file references
                content_items.extend(file_refs)
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=LLM_MODEL,
                contents=content_items,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    candidate_count=1,
                    stop_sequences=[],
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
            )

            return response.text
            
        except Exception as e:
            logger.error(f"Error generating LLM response with images: {e}", exc_info=True)
            return "Sorry, I encountered an error while analyzing the images."
    
    def _is_small_payload(self, images: List[str]) -> bool:
        """Check if the total size of images is less than 20MB."""
        total_size = sum(len(base64.b64decode(img)) for img in images)
        return total_size < 20 * 1024 * 1024  # 20MB in bytes

    def format_slack_response(self, response: str, entries: List[Dict]) -> str:
        """Format response for Slack, including reference links."""
        if not entries:
            return response
            
        # Add reference links
        references = "\n\n*References:*"
        for entry in entries:
            source_url = entry['metadata'].get('source_url', '')
            if source_url:
                references += f"\n• <{source_url}|View source>"
            
        return response + references