import os
import uuid
import pytest
from datetime import datetime
from src.models import (
    KnowledgeEntry,
    KnowledgeEntrySchema,
    KnowledgeBase,
    Base,
)

# Fixture to set up a test PostgreSQL database.
# Ensure you have a test PostgreSQL instance running and set the TEST_DATABASE_URL env variable.
@pytest.fixture(scope="module")
def test_db():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL environment variable not set for PostgreSQL tests.")
    os.environ["DATABASE_URL"] = test_db_url
    kb = KnowledgeBase()
    kb.create_tables()
    yield kb
    # Teardown: drop all tables from the test database
    Base.metadata.drop_all(kb.engine)


def test_validate_tags_valid():
    # Test that valid kebab-case tags within limit pass.
    data = {
        "content": "Test content",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["test-tag", "another-tag"],
    }
    entry = KnowledgeEntrySchema(**data)
    assert entry.tags == data["tags"]


def test_validate_tags_invalid_too_many():
    # Test that more than 3 tags raises an error.
    data = {
        "content": "Test content",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["tag-one", "tag-two", "tag-three", "tag-four"],
    }
    with pytest.raises(ValueError):
        KnowledgeEntrySchema(**data)


def test_validate_tags_invalid_format():
    # Test that a tag not in kebab-case raises an error.
    data = {
        "content": "Test content",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["InvalidTag"],
    }
    with pytest.raises(ValueError):
        KnowledgeEntrySchema(**data)


@pytest.mark.asyncio
async def test_create_and_get_entry(test_db):
    # Create a new entry and then retrieve it.
    data = {
        "content": "This is a test entry",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["test-entry"],
    }
    schema_entry = KnowledgeEntrySchema(**data)
    created_entry = await test_db.create_entry(schema_entry)
    # Verify that an ID was assigned and content matches.
    assert created_entry.id is not None
    assert created_entry.content == data["content"]

    fetched_entry = await test_db.get_entry(created_entry.id)
    assert fetched_entry is not None
    assert fetched_entry.id == created_entry.id


@pytest.mark.asyncio
async def test_update_entry(test_db):
    # Create an entry and update its content.
    data = {
        "content": "Original content",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["update-test"],
    }
    schema_entry = KnowledgeEntrySchema(**data)
    created_entry = await test_db.create_entry(schema_entry)

    updated_content = "Updated content"
    updated_entry = await test_db.update_entry(created_entry.id, {"content": updated_content})
    assert updated_entry is not None
    assert updated_entry.content == updated_content
    # Ensure that updated_at is later than or equal to created_at.
    assert updated_entry.updated_at >= updated_entry.created_at


@pytest.mark.asyncio
async def test_delete_entry(test_db):
    # Create an entry and then delete it.
    data = {
        "content": "Entry to be deleted",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["delete-test"],
    }
    schema_entry = KnowledgeEntrySchema(**data)
    created_entry = await test_db.create_entry(schema_entry)

    result = await test_db.delete_entry(created_entry.id)
    assert result is True

    fetched_entry = await test_db.get_entry(created_entry.id)
    assert fetched_entry is None


@pytest.mark.asyncio
async def test_delete_entries_by_source_url(test_db):
    # Create multiple entries with the same source_url.
    source_url = "http://example.com"
    data1 = {
        "content": "Entry 1",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "source_url": source_url,
        "tags": ["test-source"],
    }
    data2 = {
        "content": "Entry 2",
        "slack_username": "user456",
        "slack_timestamp": "0987654321",
        "source_url": source_url,
        "tags": ["test-source"],
    }
    entry1 = KnowledgeEntrySchema(**data1)
    entry2 = KnowledgeEntrySchema(**data2)
    await test_db.create_entry(entry1)
    await test_db.create_entry(entry2)

    # Delete entries by matching source_url.
    count, entry_ids = await test_db.delete_entries_by_source_url(source_url)
    assert count >= 2
    assert isinstance(entry_ids, list)
    # Confirm that the deleted entries are no longer in the database.
    for eid in entry_ids:
        fetched = await test_db.get_entry(uuid.UUID(eid))
        assert fetched is None


@pytest.mark.asyncio
async def test_delete_entries_by_filters(test_db):
    # Create entries with different additional_metadata values.
    metadata1 = {"source": "slack", "date": "2025-02-22"}
    metadata2 = {"source": "offline", "date": "2025-02-22"}
    data1 = {
        "content": "Filter Test Entry 1",
        "slack_username": "user123",
        "slack_timestamp": "1234567890",
        "tags": ["filter-test"],
        "additional_metadata": metadata1,
    }
    data2 = {
        "content": "Filter Test Entry 2",
        "slack_username": "user456",
        "slack_timestamp": "0987654321",
        "tags": ["filter-test"],
        "additional_metadata": metadata2,
    }
    entry1 = KnowledgeEntrySchema(**data1)
    entry2 = KnowledgeEntrySchema(**data2)
    await test_db.create_entry(entry1)
    await test_db.create_entry(entry2)

    # Delete entries using a filter for source "slack".
    filters = {"source": "slack"}
    count, entry_ids = await test_db.delete_entries_by_filters(filters)
    assert count >= 1
    for eid in entry_ids:
        fetched = await test_db.get_entry(uuid.UUID(eid))
        assert fetched is None
