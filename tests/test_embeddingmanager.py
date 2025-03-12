import os
import pytest
import tempfile
import numpy as np
from src.embeddingmanager import EmbeddingManager

# Dummy implementation for SentenceTransformer
class DummySentenceTransformer:
    def __init__(self, model_name):
        self.model_name = model_name
    def encode(self, text):
        # Return a vector containing the length of the text (as a float)
        return np.array([float(len(text))])

# Dummy collection to simulate ChromaDB behavior
class DummyCollection:
    def __init__(self):
        self.data = {}
    def add(self, ids, embeddings, metadatas, documents):
        for i, doc_id in enumerate(ids):
            self.data[doc_id] = {
                "embedding": embeddings[i],
                "metadata": metadatas[i],
                "document": documents[i]
            }
    def delete(self, ids):
        for doc_id in ids:
            if doc_id in self.data:
                del self.data[doc_id]
    def get(self, where, include):
        matched_ids = []
        matched_metadatas = []
        matched_documents = []
        for doc_id, entry in self.data.items():
            match = True
            for key, value in where.items():
                if entry["metadata"].get(key) != value:
                    match = False
                    break
            if match:
                matched_ids.append(doc_id)
                matched_metadatas.append(entry["metadata"])
                matched_documents.append(entry["document"])
        return {
            "ids": matched_ids,
            "metadatas": [matched_metadatas],
            "documents": [matched_documents],
            "distances": [[]]
        }

# Dummy PersistentClient for ChromaDB
class DummyPersistentClient:
    def __init__(self, path):
        self.path = path
        self.collection = DummyCollection()
    def get_or_create_collection(self, name, metadata):
        return self.collection
    def persist(self):
        pass

# Fixture to create an EmbeddingManager instance with dummy dependencies.
@pytest.fixture
def embedding_manager(monkeypatch, tmp_path):
    # Override SentenceTransformer and PersistentClient with our dummy versions.
    monkeypatch.setattr("src.embeddingmanager.SentenceTransformer", DummySentenceTransformer)
    monkeypatch.setattr("src.embeddingmanager.chromadb.PersistentClient", DummyPersistentClient)
    
    # Create a temporary directory for the dummy storage
    temp_storage = tmp_path / "chroma_storage"
    temp_storage.mkdir()
    
    # Instantiate and return the EmbeddingManager
    return EmbeddingManager()

@pytest.mark.asyncio
async def test_generate_embedding(embedding_manager):
    text = "hello"
    embedding = await embedding_manager.generate_embedding(text)
    # Our dummy returns a list with the length of the text (as a float)
    assert embedding == [5.0]

@pytest.mark.asyncio
async def test_store_embedding(embedding_manager):
    entry_id = "test-id"
    content = "sample content"
    metadata = {"source_url": "http://example.com"}
    
    # Store the embedding and verify the result
    embedding = await embedding_manager.store_embedding(entry_id, content, metadata)
    assert embedding == [float(len(content))]
    
    # Check that the dummy collection contains the entry with correct details
    collection = embedding_manager.collection
    assert entry_id in collection.data
    stored_entry = collection.data[entry_id]
    assert stored_entry["embedding"] == [float(len(content))]
    assert stored_entry["metadata"] == metadata
    assert stored_entry["document"] == content

@pytest.mark.asyncio
async def test_delete_embeddings_by_ids(embedding_manager):
    collection = embedding_manager.collection
    # Pre-add two dummy embeddings
    collection.add(
        ["id1", "id2"],
        [[1.0], [2.0]],
        [{"dummy": 1}, {"dummy": 2}],
        ["doc1", "doc2"]
    )
    # Delete one embedding by its ID and check that only one is removed
    deleted_count = await embedding_manager.delete_embeddings_by_ids(["id1"])
    assert deleted_count == 1
    assert "id1" not in collection.data
    assert "id2" in collection.data

@pytest.mark.asyncio
async def test_delete_embeddings_by_source_url(embedding_manager):
    collection = embedding_manager.collection
    # Add entries with matching and non-matching source_url values
    metadata1 = {"source_url": "http://example.com", "other": "a"}
    metadata2 = {"source_url": "http://example.com", "other": "b"}
    metadata3 = {"source_url": "http://other.com"}
    collection.add(
        ["id1", "id2", "id3"],
        [[1.0], [2.0], [3.0]],
        [metadata1, metadata2, metadata3],
        ["doc1", "doc2", "doc3"]
    )
    # Delete by matching source_url and verify that two entries are removed
    deleted_count = await embedding_manager.delete_embeddings_by_source_url("http://example.com")
    assert deleted_count == 2
    assert "id1" not in collection.data
    assert "id2" not in collection.data
    assert "id3" in collection.data

@pytest.mark.asyncio
async def test_delete_embeddings_by_filters(embedding_manager):
    collection = embedding_manager.collection
    # Add entries with different combinations of metadata fields
    metadata1 = {"source_url": "http://example.com", "source": "slack", "date": "2025-01-01"}
    metadata2 = {"source_url": "http://example.com", "source": "offline", "date": "2025-01-01"}
    metadata3 = {"source_url": "http://example.com", "source": "slack", "date": "2025-02-01"}
    collection.add(
        ["id1", "id2", "id3"],
        [[1.0], [2.0], [3.0]],
        [metadata1, metadata2, metadata3],
        ["doc1", "doc2", "doc3"]
    )
    
    # Define filter criteria to match only one entry (metadata1)
    filters = {"url": "http://example.com", "source": "slack", "date": "2025-01-01"}
    deleted_count = await embedding_manager.delete_embeddings_by_filters(filters)
    assert deleted_count == 1
    # Verify that the matching entry has been removed
    assert "id1" not in collection.data
    # The others should still exist
    assert "id2" in collection.data
    assert "id3" in collection.data
