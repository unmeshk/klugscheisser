import os
import json
import csv
import tempfile
import pytest
import asyncio
import aiofiles

from src.filehandler import FileHandler
from src.settings import KLUGBOT_TEACHERS

# Dummy implementations to simulate database and embedding operations
class DummyKB:
    async def create_entry(self, entry):
        # Return a dummy object with an 'id' attribute
        class DummyEntry:
            id = "dummy-id"
        return DummyEntry()

class DummyEmbeddingManager:
    async def store_embedding(self, entry_id, content, metadata):
        # Return a dummy embedding vector
        return [0.1, 0.2, 0.3]

# Fixture for FileHandler instance with dummy dependencies
@pytest.fixture
def file_handler():
    dummy_kb = DummyKB()
    dummy_em = DummyEmbeddingManager()
    return FileHandler(dummy_kb, dummy_em)

def test_is_authorized(file_handler):
    # User from settings should be authorized
    authorized_user = KLUGBOT_TEACHERS[0]
    unauthorized_user = "some-other-id"
    assert file_handler.is_authorized(authorized_user) is True
    assert file_handler.is_authorized(unauthorized_user) is False

@pytest.mark.asyncio
async def test_process_file_upload_unsupported_format(file_handler):
    # Create a temporary file with an unsupported extension (.exe)
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"Test content")
        tmp_path = tmp.name

    metadata = {
        'user': KLUGBOT_TEACHERS[0],
        'ts': '1234567890.123456',
        'file_url': 'http://example.com/file.exe',
        'file_type': 'exe',
        'file_name': os.path.basename(tmp_path)
    }
    
    with pytest.raises(ValueError, match="Unsupported file format"):
        await file_handler.process_file_upload(tmp_path, 'exe', metadata)
    
    os.remove(tmp_path)

@pytest.mark.asyncio
async def test_process_file_upload_file_too_large(file_handler):
    # Create a temporary text file with a small amount of data
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        content = "a" * 100  # 100 bytes of content
        tmp.write(content.encode('utf-8'))
        tmp_path = tmp.name

    metadata = {
        'user': KLUGBOT_TEACHERS[0],
        'ts': '1234567890.123456',
        'file_url': 'http://example.com/file.txt',
        'file_type': 'txt',
        'file_name': os.path.basename(tmp_path)
    }
    # Set a maximum file size smaller than the file (e.g., 50 bytes)
    with pytest.raises(ValueError, match="File too large"):
        await file_handler.process_file_upload(tmp_path, 'txt', metadata, max_file_size=50)
    
    os.remove(tmp_path)

@pytest.mark.asyncio
async def test_process_file_upload_text_file(file_handler):
    # Create a temporary text file with a simple sentence
    test_text = "Hello world. This is a test file. It should be processed into one chunk."
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(test_text)
        tmp_path = tmp.name

    metadata = {
        'user': KLUGBOT_TEACHERS[0],
        'ts': '1234567890.123456',
        'file_url': 'http://example.com/file.txt',
        'file_type': 'txt',
        'file_name': os.path.basename(tmp_path)
    }
    
    result = await file_handler.process_file_upload(tmp_path, 'txt', metadata, max_file_size=10000)
    # Since the file is small, expect at least one chunk and that all chunks were stored successfully.
    assert result['total_chunks'] >= 1
    assert result['stored_chunks'] == result['total_chunks']
    os.remove(tmp_path)

@pytest.mark.asyncio
async def test_process_file_upload_csv(file_handler):
    # Create a temporary CSV file with a header and two rows
    csv_content = "col1,col2\nvalue1,value2\nvalue3,value4"
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    metadata = {
        'user': KLUGBOT_TEACHERS[0],
        'ts': '1234567890.123456',
        'file_url': 'http://example.com/file.csv',
        'file_type': 'csv',
        'file_name': os.path.basename(tmp_path)
    }
    
    result = await file_handler.process_file_upload(tmp_path, 'csv', metadata, max_file_size=10000)
    # CSV file should yield one chunk per row (2 rows expected)
    assert result['total_chunks'] == 2
    os.remove(tmp_path)

@pytest.mark.asyncio
async def test_process_file_upload_json(file_handler):
    # Create a temporary JSON file containing a list of two objects
    json_data = [{"key": "value"}, {"key": "value2"}]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tmp:
        json.dump(json_data, tmp)
        tmp_path = tmp.name

    metadata = {
        'user': KLUGBOT_TEACHERS[0],
        'ts': '1234567890.123456',
        'file_url': 'http://example.com/file.json',
        'file_type': 'json',
        'file_name': os.path.basename(tmp_path)
    }
    
    result = await file_handler.process_file_upload(tmp_path, 'json', metadata, max_file_size=10000)
    # Each JSON object should be processed into one chunk
    assert result['total_chunks'] == 2
    os.remove(tmp_path)
