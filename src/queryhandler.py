# queryhandler.py

import os
import re
import logging
import base64
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union
from google import genai
from google.genai import types
from src.settings import (
    MAX_RESULTS,
    QUERY_PROMPT_TEMPLATE,
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

    async def process_query(self, texts: List, images: List) -> Tuple[str, List[Dict]]:
        """
        Process a knowledge query and return a response.
        Returns tuple of (response text, list of matching entries)
        """
        try:

            # the last text is the current message, so use that 
            # to generate the embedding for query to retrieve relevent context from the DB
            query_embedding = await self.embedding_manager.generate_embedding(texts[-1])
            
            # Search ChromaDB
            results = self.embedding_manager.collection.query(
                query_embeddings=[query_embedding],
                n_results=MAX_RESULTS,
                include=['metadatas', 'documents', 'distances']
            )

            logger.info(f'Retrived {len(results["ids"][0])} matching info from Chroma.')
            
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
                # if no context, don't try to answer using general knowledge. Simply say I don't know.
                return "I don't know the answer to that question.", []
            
            # Generate response using Gemini
            response = await self._generate_response(texts, images, contexts)
            
            return response, entries
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return "Sorry, I encountered an error while trying to answer that question.", []

    async def _generate_response(self, texts: List, images: List, contexts: List[str]) -> str:
        """Generate a response using Gemini."""
        try:
            # Format the prompt using the template
            print(texts[-1])
            prompt = QUERY_PROMPT_TEMPLATE.format(
                query=texts[-1],
                contexts='\n'.join(contexts)
            )

            logger.debug(prompt)

            # find bot mentions
            mention_pattern = r"<@(U[A-Z0-9]+)>"

            # construct the contents List
            contents: List[Dict[str, Union[str, List[Dict[str, bytes]]]]] = []
            #if (len(texts)>1):
            for idx, (text, imgs) in enumerate(zip(texts,images)):
                
                # this is a hack and assumes that any mention using @ is a bot mention
                # and hence the message is a user message
                # TODO: Call Slack API to get the user associated with the message
                # and check if that is the bot's name. (Add a constant to settings.py)
                # to set the bot's name in case people want to change the name from 
                # Klug-bot to something else.
                mentions = re.findall(mention_pattern, text)
                role  = 'user' if mentions else 'model'

                # For the last message, use the full prompt
                message_text = prompt if idx == len(texts) - 1 else text
                
                # Create parts list starting with text
                #parts: List[Dict[str, Union[str, bytes]]] = []
                parts = [{'text':message_text}]
                
                # Add images if any exist for this message
                for img_data in imgs:
                    try:
                        # Pass raw bytes directly to Part.from_bytes
                        image_part = types.Blob(
                            data=base64.b64decode(img_data),
                            mime_type="image/jpeg"
                        ) 

                        parts.append({'inlineData':image_part})
                        logger.info('Added an image')
                    except Exception as img_err:
                        logger.error(f"Error processing image: {img_err}", exc_info=True)

                
                # Create the content object
                content = {
                    "role": role,
                    "parts": parts,
                }
                
                contents.append(content)
                
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=LLM_MODEL,
                contents=contents,
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