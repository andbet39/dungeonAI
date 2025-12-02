"""
Tests for Storage Service.

Tests cover:
- Per-game save/load operations
- Legacy save/load operations
- Player registry persistence
- Atomic write with temp files
- Save listing and metadata
- Backup creation
- Delete operations
"""
import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================================================
# STORAGE SERVICE FIXTURES
# ============================================================================

@pytest.fixture
def temp_storage_service(tmp_path):
    """
    Create a StorageService instance with temporary directories.
    Bypasses the singleton pattern for isolated testing.
    """
    from app.services.storage_service import StorageService
    
    # Create temporary directories
    save_path = tmp_path / "saves"
    games_path = save_path / "games"
    players_file = save_path / "players.json"
    save_path.mkdir(parents=True, exist_ok=True)
    games_path.mkdir(parents=True, exist_ok=True)
    
    # Create a fresh instance bypassing singleton
    service = object.__new__(StorageService)
    service.save_path = save_path
    service.games_path = games_path
    service.players_file = players_file
    service._save_lock = asyncio.Lock()
    service._initialized = True
    
    return service


@pytest.fixture
def sample_game_state():
    """Sample game state for testing."""
    return {
        "game_id": "test-game-001",
        "name": "Test Dungeon",
        "map": {
            "width": 50,
            "height": 40,
            "tiles": [[0] * 50 for _ in range(40)],
            "spawn_x": 5,
            "spawn_y": 5,
            "seed": 12345
        },
        "rooms": [{"id": "room-1", "x": 2, "y": 2, "width": 10, "height": 8}],
        "players": {"p1": {"id": "p1", "x": 5, "y": 5}},
        "monsters": {"m1": {"id": "m1", "x": 7, "y": 7}}
    }


@pytest.fixture
def sample_player_registry():
    """Sample player registry for testing."""
    return {
        "players": {
            "p1": {
                "id": "p1",
                "nickname": "The Hero",
                "total_kills": 10,
                "total_xp": 500
            }
        },
        "tokens": {
            "token-abc": "p1"
        }
    }


# ============================================================================
# PER-GAME SAVE TESTS
# ============================================================================

class TestSaveGameById:
    """Tests for per-game save operations."""
    
    @pytest.mark.asyncio
    async def test_save_game_creates_file(self, temp_storage_service, sample_game_state):
        """Saving a game should create a JSON file."""
        result = await temp_storage_service.save_game_by_id(
            "game-001",
            sample_game_state,
            reason="test"
        )
        
        assert result is True
        save_file = temp_storage_service.games_path / "game-001.json"
        assert save_file.exists()
    
    @pytest.mark.asyncio
    async def test_save_game_content(self, temp_storage_service, sample_game_state):
        """Saved file should contain correct data structure."""
        await temp_storage_service.save_game_by_id(
            "game-001",
            sample_game_state,
            reason="test_save"
        )
        
        save_file = temp_storage_service.games_path / "game-001.json"
        with open(save_file) as f:
            data = json.load(f)
        
        assert data["version"] == "2.0"
        assert data["game_id"] == "game-001"
        assert data["save_reason"] == "test_save"
        assert data["game_state"] == sample_game_state
        assert "saved_at" in data
    
    @pytest.mark.asyncio
    async def test_save_game_overwrites_existing(self, temp_storage_service, sample_game_state):
        """Saving to same game_id should overwrite."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        
        modified_state = {**sample_game_state, "name": "Modified Dungeon"}
        await temp_storage_service.save_game_by_id("game-001", modified_state)
        
        save_file = temp_storage_service.games_path / "game-001.json"
        with open(save_file) as f:
            data = json.load(f)
        
        assert data["game_state"]["name"] == "Modified Dungeon"


class TestLoadGameById:
    """Tests for per-game load operations."""
    
    @pytest.mark.asyncio
    async def test_load_existing_game(self, temp_storage_service, sample_game_state):
        """Loading an existing game should return the state."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        
        loaded = await temp_storage_service.load_game_by_id("game-001")
        
        assert loaded is not None
        assert loaded["game_id"] == sample_game_state["game_id"]
        assert loaded["name"] == sample_game_state["name"]
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_game(self, temp_storage_service):
        """Loading a non-existent game should return None."""
        loaded = await temp_storage_service.load_game_by_id("nonexistent")
        
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_load_corrupted_file(self, temp_storage_service):
        """Loading corrupted JSON should return None and not raise."""
        # Create corrupted file
        corrupted_file = temp_storage_service.games_path / "corrupted.json"
        with open(corrupted_file, "w") as f:
            f.write("not valid json {{{")
        
        loaded = await temp_storage_service.load_game_by_id("corrupted")
        
        assert loaded is None


class TestDeleteGameSave:
    """Tests for game deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_game(self, temp_storage_service, sample_game_state):
        """Deleting existing game should remove the file."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        
        result = await temp_storage_service.delete_game_save("game-001")
        
        assert result is True
        save_file = temp_storage_service.games_path / "game-001.json"
        assert not save_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_game(self, temp_storage_service):
        """Deleting non-existent game should return False."""
        result = await temp_storage_service.delete_game_save("nonexistent")
        
        assert result is False


class TestListGameSaves:
    """Tests for listing game saves."""
    
    @pytest.mark.asyncio
    async def test_list_empty(self, temp_storage_service):
        """Empty directory should return empty list."""
        saves = temp_storage_service.list_game_saves()
        
        assert saves == []
    
    @pytest.mark.asyncio
    async def test_list_multiple_games(self, temp_storage_service, sample_game_state):
        """Should list all saved games."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        await temp_storage_service.save_game_by_id("game-002", {**sample_game_state, "name": "Another Dungeon"})
        
        saves = temp_storage_service.list_game_saves()
        
        assert len(saves) == 2
        game_ids = [s["game_id"] for s in saves]
        assert "game-001" in game_ids
        assert "game-002" in game_ids
    
    @pytest.mark.asyncio
    async def test_list_includes_metadata(self, temp_storage_service, sample_game_state):
        """Listed saves should include metadata."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        
        saves = temp_storage_service.list_game_saves()
        
        assert len(saves) == 1
        save = saves[0]
        assert save["game_id"] == "game-001"
        assert save["version"] == "2.0"
        assert save["name"] == "Test Dungeon"
        assert "saved_at" in save


# ============================================================================
# PLAYER REGISTRY TESTS
# ============================================================================

class TestPlayerRegistry:
    """Tests for player registry persistence."""
    
    @pytest.mark.asyncio
    async def test_save_player_registry(self, temp_storage_service, sample_player_registry):
        """Saving player registry should create file."""
        result = await temp_storage_service.save_player_registry(sample_player_registry)
        
        assert result is True
        assert temp_storage_service.players_file.exists()
    
    @pytest.mark.asyncio
    async def test_load_player_registry(self, temp_storage_service, sample_player_registry):
        """Loading player registry should return saved data."""
        await temp_storage_service.save_player_registry(sample_player_registry)
        
        loaded = await temp_storage_service.load_player_registry()
        
        assert loaded is not None
        assert "players" in loaded
        assert "tokens" in loaded
        assert loaded["players"]["p1"]["nickname"] == "The Hero"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_registry(self, temp_storage_service):
        """Loading non-existent registry should return None."""
        loaded = await temp_storage_service.load_player_registry()
        
        assert loaded is None


# ============================================================================
# LEGACY SAVE TESTS
# ============================================================================

class TestLegacySave:
    """Tests for legacy save/load operations."""
    
    @pytest.mark.asyncio
    async def test_save_game_legacy(self, temp_storage_service, sample_game_state):
        """Legacy save should create file with correct format."""
        result = await temp_storage_service.save_game(
            sample_game_state,
            save_id="test_save",
            reason="legacy_test"
        )
        
        assert result is True
        save_file = temp_storage_service.save_path / "test_save.json"
        assert save_file.exists()
    
    @pytest.mark.asyncio
    async def test_load_game_legacy(self, temp_storage_service, sample_game_state):
        """Legacy load should return saved state."""
        await temp_storage_service.save_game(sample_game_state, save_id="test_save")
        
        loaded = await temp_storage_service.load_game(save_id="test_save")
        
        assert loaded is not None
        assert loaded["game_id"] == sample_game_state["game_id"]
    
    @pytest.mark.asyncio
    async def test_default_save_id_is_current(self, temp_storage_service, sample_game_state):
        """Default save_id should be 'current'."""
        await temp_storage_service.save_game(sample_game_state)
        
        save_file = temp_storage_service.save_path / "current.json"
        assert save_file.exists()


class TestListSaves:
    """Tests for listing legacy saves."""
    
    @pytest.mark.asyncio
    async def test_list_saves(self, temp_storage_service, sample_game_state):
        """Should list all legacy saves."""
        await temp_storage_service.save_game(sample_game_state, save_id="save1")
        await temp_storage_service.save_game(sample_game_state, save_id="save2")
        
        saves = temp_storage_service.list_saves()
        
        save_ids = [s["id"] for s in saves]
        assert "save1" in save_ids
        assert "save2" in save_ids
    
    @pytest.mark.asyncio
    async def test_list_saves_includes_metadata(self, temp_storage_service, sample_game_state):
        """Save list should include metadata."""
        await temp_storage_service.save_game(
            sample_game_state,
            save_id="test",
            reason="testing"
        )
        
        saves = temp_storage_service.list_saves()
        save = next(s for s in saves if s["id"] == "test")
        
        assert save["version"] == "1.0"
        assert save["save_reason"] == "testing"
        assert save["map_width"] == 50
        assert save["map_height"] == 40


class TestDeleteSave:
    """Tests for legacy save deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_save(self, temp_storage_service, sample_game_state):
        """Deleting existing save should remove file."""
        await temp_storage_service.save_game(sample_game_state, save_id="to_delete")
        
        result = await temp_storage_service.delete_save("to_delete")
        
        assert result is True
        assert not (temp_storage_service.save_path / "to_delete.json").exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_save(self, temp_storage_service):
        """Deleting non-existent save should return False."""
        result = await temp_storage_service.delete_save("nonexistent")
        
        assert result is False


class TestBackup:
    """Tests for backup creation."""
    
    @pytest.mark.asyncio
    async def test_create_backup(self, temp_storage_service, sample_game_state):
        """Creating backup should create new save file."""
        await temp_storage_service.save_game(sample_game_state, save_id="original")
        
        backup_id = await temp_storage_service.create_backup("original")
        
        assert backup_id is not None
        assert backup_id.startswith("backup_original_")
        
        # Verify backup file exists
        backup_file = temp_storage_service.save_path / f"{backup_id}.json"
        assert backup_file.exists()
    
    @pytest.mark.asyncio
    async def test_backup_contains_same_data(self, temp_storage_service, sample_game_state):
        """Backup should contain same game state."""
        await temp_storage_service.save_game(sample_game_state, save_id="original")
        
        backup_id = await temp_storage_service.create_backup("original")
        backup_state = await temp_storage_service.load_game(backup_id)
        
        assert backup_state["game_id"] == sample_game_state["game_id"]
        assert backup_state["name"] == sample_game_state["name"]
    
    @pytest.mark.asyncio
    async def test_backup_nonexistent_save(self, temp_storage_service):
        """Backing up non-existent save should return None."""
        backup_id = await temp_storage_service.create_backup("nonexistent")
        
        assert backup_id is None


# ============================================================================
# ATOMIC WRITE TESTS
# ============================================================================

class TestAtomicWrite:
    """Tests for atomic write safety."""
    
    @pytest.mark.asyncio
    async def test_no_temp_file_left_behind(self, temp_storage_service, sample_game_state):
        """After successful save, no .tmp files should remain."""
        await temp_storage_service.save_game_by_id("game-001", sample_game_state)
        
        tmp_files = list(temp_storage_service.games_path.glob("*.tmp"))
        assert len(tmp_files) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_saves(self, temp_storage_service, sample_game_state):
        """Concurrent saves should not corrupt data."""
        # Create multiple concurrent save operations
        async def save_task(game_id, name):
            state = {**sample_game_state, "name": name}
            return await temp_storage_service.save_game_by_id(game_id, state)
        
        results = await asyncio.gather(
            save_task("game-001", "Dungeon A"),
            save_task("game-002", "Dungeon B"),
            save_task("game-003", "Dungeon C"),
        )
        
        assert all(results)
        
        # Verify all saves are valid
        for game_id in ["game-001", "game-002", "game-003"]:
            loaded = await temp_storage_service.load_game_by_id(game_id)
            assert loaded is not None


# ============================================================================
# SINGLETON TESTS
# ============================================================================

class TestStorageServiceSingleton:
    """Tests for singleton behavior."""
    
    def test_storage_service_is_singleton(self):
        """Multiple StorageService() calls should return same instance."""
        from app.services.storage_service import StorageService
        
        service1 = StorageService()
        service2 = StorageService()
        
        assert service1 is service2
