#!/usr/bin/env python3
"""
Script to recursively process files from a directory and import them into the knowledge databases.

Usage:
    python add_to_db.py --directory /path/to/directory --formats txt,md,pdf --url-prefix https://example.com
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add both the parent directory and src directory to the path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'src'))

from dotenv import load_dotenv
from src.models import KnowledgeBase
from src.embeddingmanager import EmbeddingManager
from src.filehandler import FileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_directory(
    directory_path: str,
    file_formats: List[str],
    url_prefix: str,
    user_id: str
) -> Dict[str, int]:
    """
    Recursively process files in a directory and add them to the knowledge database.
    
    Args:
        directory_path: The path to the directory to process
        file_formats: List of file extensions to process (without the dot)
        url_prefix: URL prefix to add to file paths for source URLs
        user_id: User ID to use as the creator of the entries
        
    Returns:
        Statistics about the processed files
    """
    # Initialize database connections
    kb = KnowledgeBase()
    embedding_manager = EmbeddingManager()
    file_handler = FileHandler(kb, embedding_manager)
    
    # Convert formats to lowercase with dots
    formats = [f".{fmt.lower().lstrip('.')}" for fmt in file_formats]
    
    # Statistics
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "failed_files": 0,
        "total_chunks": 0,
        "stored_chunks": 0,
        "failed_chunks": 0
    }
    
    # Walk through directory recursively
    directory_path = os.path.abspath(directory_path)
    logger.info(f"Processing directory: {directory_path}")
    
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            if file_ext in formats:
                stats["total_files"] += 1
                relative_path = os.path.relpath(file_path, directory_path)
                source_url = f"{url_prefix.rstrip('/')}/{relative_path}"
                
                logger.info(f"Processing file: {file_path}")
                logger.info(f"Source URL: {source_url}")
                
                try:
                    # Create metadata for the file
                    metadata = {
                        "user": user_id,
                        "ts": str(Path(file_path).stat().st_mtime),
                        "file_url": source_url,
                        "file_type": file_ext.lstrip('.'),
                        "file_name": file
                    }
                    
                    # Process the file
                    result = await file_handler.process_file_upload(
                        file_path,
                        file_ext.lstrip('.'),
                        metadata
                    )
                    
                    # Update statistics
                    stats["processed_files"] += 1
                    stats["total_chunks"] += result["total_chunks"]
                    stats["stored_chunks"] += result["stored_chunks"]
                    stats["failed_chunks"] += result["failed_chunks"]
                    
                    logger.info(f"Successfully processed file: {file} - Chunks: {result['stored_chunks']}/{result['total_chunks']}")
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
                    stats["failed_files"] += 1
    
    # Persist ChromaDB state
    # embedding_manager.chroma_client.persist()
    # logger.info("ChromaDB state persisted successfully")
    
    return stats

async def main():
    """Parse arguments and process the specified directory."""
    parser = argparse.ArgumentParser(description="Import files into knowledge database")
    
    parser.add_argument(
        "--directory", "-d", 
        required=True, 
        help="Directory to process recursively"
    )
    
    parser.add_argument(
        "--formats", "-f", 
        required=True, 
        help="Comma-separated list of file formats to process (e.g., txt,md,pdf)"
    )
    
    parser.add_argument(
        "--url-prefix", "-u", 
        required=True, 
        help="URL prefix to add to file paths for source URLs"
    )
    
    parser.add_argument(
        "--user-id", 
        default="LOCAL_IMPORT", 
        help="User ID to use as creator (default: LOCAL_IMPORT)"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Validate directory exists
    if not os.path.isdir(args.directory):
        logger.error(f"Directory does not exist: {args.directory}")
        sys.exit(1)
    
    # Parse formats
    formats = args.formats.split(",")
    
    # Process the directory
    stats = await process_directory(
        args.directory,
        formats,
        args.url_prefix,
        args.user_id
    )
    
    # Print summary
    logger.info("\nImport Summary:")
    logger.info(f"Total files found: {stats['total_files']}")
    logger.info(f"Successfully processed files: {stats['processed_files']}")
    logger.info(f"Failed files: {stats['failed_files']}")
    logger.info(f"Total chunks extracted: {stats['total_chunks']}")
    logger.info(f"Successfully stored chunks: {stats['stored_chunks']}")
    logger.info(f"Failed chunks: {stats['failed_chunks']}")

if __name__ == "__main__":
    asyncio.run(main())