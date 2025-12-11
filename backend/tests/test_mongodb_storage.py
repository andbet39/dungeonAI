"""
Unit tests for MongoDB storage service.

Run with: pytest backend/tests/test_mongodb_storage.py
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.mongodb_storage_service import MongoDBStorageService


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB database."""
    with patch('app.services.mongodb_storage_service.mongodb_manager') as mock_manager:
        mock_db = MagicMock()
        mock_manager.db = mock_db
        yield mock_db


@pytest.mark.asyncio
async def test_save_game_by_id(mock_mongodb):
    """Test saving a game to MongoDB."""
    storage = MongoDBStorageService()

    game_state = {
        "name": "Test Game",
        "map": {"width": 80, "height": 50},
        "rooms": [],
        "players": {},
        "monsters": {}
    }

    # Mock the update_one method
    mock_mongodb.games.update_one = AsyncMock(return_value=MagicMock())

    success = await storage.save_game_by_id("test_game_1", game_state)

    assert success is True
    mock_mongodb.games.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_load_game_by_id(mock_mongodb):
    """Test loading a game from MongoDB."""
    storage = MongoDBStorageService()

    # Mock game data
    mock_game_data = {
        "_id": "some_object_id",
        "game_id": "test_game_1",
        "name": "Test Game",
        "saved_at": datetime.now(),
        "save_reason": "test",
        "map": {"width": 80, "height": 50}
    }

    mock_mongodb.games.find_one = AsyncMock(return_value=mock_game_data)

    loaded = await storage.load_game_by_id("test_game_1")

    assert loaded is not None
    assert loaded["name"] == "Test Game"
    assert "_id" not in loaded  # MongoDB-specific fields should be removed
    assert "game_id" not in loaded


@pytest.mark.asyncio
async def test_load_game_not_found(mock_mongodb):
    """Test loading a non-existent game."""
    storage = MongoDBStorageService()
    mock_mongodb.games.find_one = AsyncMock(return_value=None)

    loaded = await storage.load_game_by_id("nonexistent_game")

    assert loaded is None


@pytest.mark.asyncio
async def test_delete_game_save(mock_mongodb):
    """Test deleting a game save."""
    storage = MongoDBStorageService()

    # Mock successful deletion
    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_mongodb.games.delete_one = AsyncMock(return_value=mock_result)

    success = await storage.delete_game_save("test_game_1")

    assert success is True
    mock_mongodb.games.delete_one.assert_called_once_with({"game_id": "test_game_1"})


@pytest.mark.asyncio
async def test_save_player_registry(mock_mongodb):
    """Test saving player registry."""
    storage = MongoDBStorageService()

    registry_data = {
        "players": {
            "token1": {"display_name": "Player1", "nickname": "P1"},
            "token2": {"display_name": "Player2", "nickname": "P2"}
        },
        "stats": {
            "token1": {"experience_earned": 100, "kills_by_type": {}},
            "token2": {"experience_earned": 200, "kills_by_type": {}}
        }
    }

    mock_mongodb.players.bulk_write = AsyncMock()
    mock_mongodb.player_stats.bulk_write = AsyncMock()

    success = await storage.save_player_registry(registry_data)

    assert success is True
    assert mock_mongodb.players.bulk_write.called
    assert mock_mongodb.player_stats.bulk_write.called


@pytest.mark.asyncio
async def test_load_player_registry(mock_mongodb):
    """Test loading player registry."""
    storage = MongoDBStorageService()

    # Mock players data
    mock_players = [
        {"_id": "id1", "token": "token1", "display_name": "Player1"},
        {"_id": "id2", "token": "token2", "display_name": "Player2"}
    ]

    # Mock stats data
    mock_stats = [
        {"_id": "id1", "token": "token1", "experience_earned": 100},
        {"_id": "id2", "token": "token2", "experience_earned": 200}
    ]

    # Mock async cursors
    async def players_cursor():
        for player in mock_players:
            yield player

    async def stats_cursor():
        for stat in mock_stats:
            yield stat

    mock_mongodb.players.find = MagicMock(return_value=players_cursor())
    mock_mongodb.player_stats.find = MagicMock(return_value=stats_cursor())

    registry = await storage.load_player_registry()

    assert registry is not None
    assert len(registry["players"]) == 2
    assert len(registry["stats"]) == 2
    assert "token1" in registry["players"]
    assert "token2" in registry["stats"]
