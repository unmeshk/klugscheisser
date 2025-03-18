import pytest
import asyncio
import base64
from src.queryhandler import QueryHandler
from src.settings import MAX_RESULTS, QUERY_PROMPT_TEMPLATE, MAX_OUTPUT_TOKENS, LLM_MODEL

@pytest.fixture(autouse=True)
def set_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key")

# Dummy response class to simulate Gemini API responses.
class DummyResponse:
    def __init__(self, text):
        self.text = text

# Dummy collection that returns preset results.
class DummyCollection:
    def __init__(self, results):
        self.results = results

    def query(self, query_embeddings, n_results, include):
        return self.results

# Dummy embedding manager that implements generate_embedding and has a collection.
class DummyEmbeddingManager:
    async def generate_embedding(self, text):
        # Return a fixed dummy embedding.
        return [0.1, 0.2, 0.3]

    def __init__(self, results):
        self.collection = DummyCollection(results)

# Dummy client to simulate Gemini API calls.
class DummyAioModels:
    async def generate_content(self, model, contents, config):
        # Return a dummy response with fixed text.
        return DummyResponse("generated response")

class DummyAio:
    def __init__(self):
        self.models = DummyAioModels()

class DummyClient:
    def __init__(self):
        self.aio = DummyAio()

# Fixtures for QueryHandler with different collection query results.
@pytest.fixture
def dummy_query_handler_no_results():
    # Simulate no results from the vector store.
    results = {
        'ids': [[]],
        'documents': [[]],
        'metadatas': [[]],
        'distances': [[]]
    }
    embedding_manager = DummyEmbeddingManager(results)
    qh = QueryHandler(embedding_manager)
    qh.client = DummyClient()
    return qh

@pytest.fixture
def dummy_query_handler_with_results():
    # Simulate one matching result.
    results = {
        'ids': [['1']],
        'documents': [['This is a sample document']],
        'metadatas': [[{'id': '1', 'source_url': 'https://example.com'}]],
        'distances': [[0.5]]
    }
    embedding_manager = DummyEmbeddingManager(results)
    qh = QueryHandler(embedding_manager)
    qh.client = DummyClient()
    return qh

# --- Tests for process_query ---

@pytest.mark.asyncio
async def test_process_query_no_results(dummy_query_handler_no_results):
    texts = ["What is the capital of France?"]
    images = [[]]  # Simulate no images.
    response, entries = await dummy_query_handler_no_results.process_query(texts, images)
    # If no results are found, QueryHandler should return a default answer.
    assert response == "I don't know the answer to that question. <end>"
    assert entries == []

@pytest.mark.asyncio
async def test_process_query_with_results(dummy_query_handler_with_results):
    # Override _generate_response to return a dummy response.
    async def dummy_generate_response(texts, images, contexts):
        return "dummy response"
    dummy_query_handler_with_results._generate_response = dummy_generate_response

    texts = ["What is the capital of France?"]
    images = [[]]
    response, entries = await dummy_query_handler_with_results.process_query(texts, images)
    assert response == "dummy response"
    # Check that one entry was returned with expected data.
    assert len(entries) == 1
    entry = entries[0]
    assert entry['id'] == '1'
    assert entry['content'] == "This is a sample document"
    assert 'source_url' in entry['metadata']

# --- Tests for helper methods ---

def test_is_small_payload():
    # Create a QueryHandler with a dummy embedding manager.
    qh = QueryHandler(DummyEmbeddingManager({}))
    # Create a small payload.
    small_img = base64.b64encode(b"test image").decode('utf-8')
    assert qh._is_small_payload([small_img]) is True

def test_format_slack_response():
    qh = QueryHandler(DummyEmbeddingManager({}))
    response = "base response"
    entries = [{'metadata': {'source_url': 'https://example.com'}}]
    formatted = qh.format_slack_response(response, entries)
    # The formatted response should include the source URL and a reference header.
    assert "https://example.com" in formatted
    assert "References:" in formatted

# --- Test for _generate_response ---

@pytest.mark.asyncio
async def test_generate_response(monkeypatch):
    # Create a dummy function to simulate the Gemini API call.
    dummy_response_text = "generated response"
    async def dummy_generate_content(model, contents, config):
        return DummyResponse(dummy_response_text)
    
    # Create a QueryHandler instance.
    qh = QueryHandler(DummyEmbeddingManager({}))
    
    # Set up a dummy client with our dummy generate_content.
    class DummyAioModelsOverride:
        async def generate_content(self, model, contents, config):
            return DummyResponse(dummy_response_text)
    class DummyAioOverride:
        def __init__(self):
            self.models = DummyAioModelsOverride()
    class DummyClientOverride:
        def __init__(self):
            self.aio = DummyAioOverride()
    qh.client = DummyClientOverride()
    
    texts = ["Initial text"]
    images = [[]]
    contexts = ["Context 1: Sample document."]
    result = await qh._generate_response(texts, images, contexts)
    assert result == dummy_response_text
