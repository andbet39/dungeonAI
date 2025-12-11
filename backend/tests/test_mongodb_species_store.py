"""
Unit tests for MongoDB species knowledge store.

Run with: pytest backend/tests/test_mongodb_species_store.py
"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from bson import Binary

from app.services.mongodb_species_store import MongoDBSpeciesKnowledgeStore
from app.domain.intelligence.generations import SpeciesKnowledgeRecord


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB database."""
    with patch('app.services.mongodb_species_store.mongodb_manager') as mock_manager:
        mock_db = MagicMock()
        mock_manager.db = mock_db
        yield mock_db


@pytest.fixture
def sample_q_table():
    """Sample Q-table for testing."""
    return np.random.rand(100, 10).astype(np.float32)


@pytest.mark.asyncio
async def test_async_save(mock_mongodb, sample_q_table):
    """Test saving species knowledge to MongoDB."""
    store = MongoDBSpeciesKnowledgeStore()

    # Add a test record
    store.records["goblin"] = SpeciesKnowledgeRecord(
        monster_type="goblin",
        generation=5,
        encounters=100,
        total_learning_steps=1000,
        q_table=sample_q_table
    )

    mock_mongodb.species_knowledge.bulk_write = AsyncMock()

    await store._async_save()

    assert mock_mongodb.species_knowledge.bulk_write.called


@pytest.mark.asyncio
async def test_async_load(mock_mongodb, sample_q_table):
    """Test loading species knowledge from MongoDB."""
    store = MongoDBSpeciesKnowledgeStore()

    # Mock MongoDB document
    q_table_binary = Binary(sample_q_table.tobytes())
    mock_doc = {
        "monster_type": "goblin",
        "generation": 5,
        "encounters": 100,
        "total_learning_steps": 1000,
        "q_table": q_table_binary,
        "q_table_shape": list(sample_q_table.shape),
        "schema_version": 2
    }

    # Mock async cursor
    async def mock_cursor():
        yield mock_doc

    mock_mongodb.species_knowledge.find = MagicMock(return_value=mock_cursor())

    await store._async_load()

    assert "goblin" in store.records
    record = store.records["goblin"]
    assert record.generation == 5
    assert record.encounters == 100
    assert record.q_table.shape == sample_q_table.shape


@pytest.mark.asyncio
async def test_async_load_with_schema_mismatch(mock_mongodb):
    """Test loading with schema version mismatch."""
    store = MongoDBSpeciesKnowledgeStore()

    # Mock document with old schema version
    mock_doc = {
        "monster_type": "goblin",
        "schema_version": 1,  # Old version
        "generation": 5
    }

    async def mock_cursor():
        yield mock_doc

    mock_mongodb.species_knowledge.find = MagicMock(return_value=mock_cursor())
    mock_mongodb.species_knowledge.delete_one = AsyncMock()

    await store._async_load()

    # Should delete old schema documents
    mock_mongodb.species_knowledge.delete_one.assert_called()
    assert "goblin" not in store.records


@pytest.mark.asyncio
async def test_save_history(mock_mongodb):
    """Test saving species learning history."""
    store = MongoDBSpeciesKnowledgeStore()

    q_table = np.zeros((10, 5), dtype=np.float32)
    record = SpeciesKnowledgeRecord(
        monster_type="goblin",
        generation=1,
        q_table=q_table
    )

    # Add history entry
    record.add_history_entry(
        reward=10.0,
        state_index=0,
        action="ATTACK",
        q_value_before=0.5,
        q_value_after=0.6
    )

    store.records["goblin"] = record
    mock_mongodb.species_history.update_one = AsyncMock()

    await store._async_save_history(record)

    assert mock_mongodb.species_history.update_one.called


@pytest.mark.asyncio
async def test_load_history(mock_mongodb):
    """Test loading species learning history."""
    store = MongoDBSpeciesKnowledgeStore()

    q_table = np.zeros((10, 5), dtype=np.float32)
    record = SpeciesKnowledgeRecord(
        monster_type="goblin",
        generation=1,
        q_table=q_table
    )
    store.records["goblin"] = record

    # Mock history document
    mock_history = {
        "monster_type": "goblin",
        "schema_version": 2,
        "history": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "generation": 1,
                "reward": 10.0,
                "state_index": 0,
                "action": "ATTACK",
                "q_value_before": 0.5,
                "q_value_after": 0.6
            }
        ]
    }

    mock_mongodb.species_history.find_one = AsyncMock(return_value=mock_history)

    await store._async_load_history(record)

    assert record._history_loaded
    assert len(record.history) == 1
    assert record.history[0].action == "ATTACK"


def test_get_or_create():
    """Test get_or_create method."""
    store = MongoDBSpeciesKnowledgeStore()

    record = store.get_or_create("goblin", state_space=100, action_count=10)

    assert record.monster_type == "goblin"
    assert record.q_table.shape == (100, 10)
    assert "goblin" in store.records


def test_get_or_create_with_resize():
    """Test Q-table resizing when dimensions change."""
    store = MongoDBSpeciesKnowledgeStore()

    # Create initial record
    old_table = np.ones((50, 5), dtype=np.float32)
    store.records["goblin"] = SpeciesKnowledgeRecord(
        monster_type="goblin",
        generation=1,
        q_table=old_table
    )

    # Get with new dimensions
    record = store.get_or_create("goblin", state_space=100, action_count=10)

    # Should be resized
    assert record.q_table.shape == (100, 10)
    # Old values should be preserved
    assert record.q_table[0, 0] == 1.0


def test_bump_generation():
    """Test bumping generation counter."""
    store = MongoDBSpeciesKnowledgeStore()

    q_table = np.zeros((10, 5), dtype=np.float32)
    store.records["goblin"] = SpeciesKnowledgeRecord(
        monster_type="goblin",
        generation=0,
        q_table=q_table
    )

    store.bump_generation("goblin")

    assert store.records["goblin"].generation == 1

    # Test with max generation cap
    store.bump_generation("goblin", max_generation=1)

    assert store.records["goblin"].generation == 1  # Should be capped
