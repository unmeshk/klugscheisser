# queryhandler.py

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from settings import (
    SIMILARITY_THRESHOLD,
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

    async def _generate_response(self, query: str, contexts: List[str]) -> str:
        """Generate a response using Gemini."""
        try:
            # Format the prompt using the template
            prompt = QUERY_PROMPT_TEMPLATE.format(
                query=query,
                contexts='\n'.join(contexts)
            )

            print(prompt)

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