"""
Tests for Player Registry service.

Tests cover:
- PlayerProfile creation and serialization
- Token generation
- Player registration (get_or_create)
- Game assignment tracking
- Display name and nickname updates
- Persistence operations
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.player_registry import PlayerProfile, PlayerRegistry


# ============================================================================
# PLAYERPROFILE TESTS
# ============================================================================

class TestPlayerProfileCreation:
    """Tests for PlayerProfile dataclass."""
    
    def test_create_profile_with_required_fields(self):
        """Creating a profile should set token and display_name."""
        profile = PlayerProfile(
            token="test-token-123",
            display_name="TestHero"
        )
        
        assert profile.token == "test-token-123"
        assert profile.display_name == "TestHero"
    
    def test_default_values(self):
        """Profile should have sensible defaults."""
        profile = PlayerProfile(token="abc", display_name="Hero")
        
        assert profile.current_game_id is None
        assert profile.current_player_id is None
        assert profile.total_games_played == 0
        assert profile.nickname is None
        assert profile.created_at is not None
        assert profile.last_seen is not None
    
    def test_to_dict(self):
        """to_dict should serialize all fields."""
        profile = PlayerProfile(
            token="token-xyz",
            display_name="HeroName",
            nickname="The Brave"
        )
        
        data = profile.to_dict()
        
        assert data["token"] == "token-xyz"
        assert data["display_name"] == "HeroName"
        assert data["nickname"] == "The Brave"
        assert "created_at" in data
        assert "last_seen" in data
    
    def test_from_dict(self):
        """from_dict should deserialize correctly."""
        data = {
            "token": "token-abc",
            "display_name": "LoadedHero",
            "nickname": "The Strong",
            "total_games_played": 5,
            "current_game_id": "game-001"
        }
        
        profile = PlayerProfile.from_dict(data)
        
        assert profile.token == "token-abc"
        assert profile.display_name == "LoadedHero"
        assert profile.nickname == "The Strong"
        assert profile.total_games_played == 5
    
    def test_from_dict_ignores_unknown_fields(self):
        """from_dict should ignore unknown fields for forward compatibility."""
        data = {
            "token": "token-1",
            "display_name": "Hero",
            "unknown_future_field": "some_value"
        }
        
        # Should not raise
        profile = PlayerProfile.from_dict(data)
        assert profile.token == "token-1"


class TestPlayerProfileMethods:
    """Tests for PlayerProfile methods."""
    
    def test_update_last_seen(self):
        """update_last_seen should update the timestamp."""
        profile = PlayerProfile(token="t1", display_name="Hero")
        original_last_seen = profile.last_seen
        
        # Wait a tiny bit to ensure different timestamp
        import time
        time.sleep(0.01)
        
        profile.update_last_seen()
        
        assert profile.last_seen >= original_last_seen
    
    def test_get_full_title_with_nickname(self):
        """get_full_title should combine name and nickname."""
        profile = PlayerProfile(
            token="t1",
            display_name="John",
            nickname="The Goblin Slayer"
        )
        
        title = profile.get_full_title()
        
        assert title == "John The Goblin Slayer"
    
    def test_get_full_title_without_nickname(self):
        """get_full_title should return just name when no nickname."""
        profile = PlayerProfile(token="t1", display_name="John")
        
        title = profile.get_full_title()
        
        assert title == "John"


# ============================================================================
# PLAYERREGISTRY FIXTURES
# ============================================================================

@pytest.fixture
def fresh_registry():
    """Create a fresh PlayerRegistry for testing."""
    registry = object.__new__(PlayerRegistry)
    registry._players = {}
    registry._lock = asyncio.Lock()
    registry._dirty = False
    registry._save_task = None
    registry._initialized = True
    return registry


@pytest.fixture
def populated_registry(fresh_registry):
    """Create a registry with some players."""
    fresh_registry._players = {
        "token-1": PlayerProfile(
            token="token-1",
            display_name="Player1",
            current_game_id="game-001",
            current_player_id="p1"
        ),
        "token-2": PlayerProfile(
            token="token-2",
            display_name="Player2",
            current_game_id="game-001",
            current_player_id="p2"
        ),
        "token-3": PlayerProfile(
            token="token-3",
            display_name="Player3",
            current_game_id=None  # Not in any game
        )
    }
    return fresh_registry


# ============================================================================
# PLAYERREGISTRY TESTS
# ============================================================================

class TestPlayerRegistryTokenGeneration:
    """Tests for token generation."""
    
    def test_generate_token_returns_string(self, fresh_registry):
        """generate_token should return a string."""
        token = fresh_registry.generate_token()
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_is_unique(self, fresh_registry):
        """Each generated token should be unique."""
        tokens = {fresh_registry.generate_token() for _ in range(100)}
        
        assert len(tokens) == 100


class TestPlayerRegistryGetOrCreate:
    """Tests for get_or_create_player."""
    
    @pytest.mark.asyncio
    async def test_create_new_player(self, fresh_registry):
        """Should create new player if token not exists."""
        profile = await fresh_registry.get_or_create_player(
            token="new-token",
            display_name="NewHero"
        )
        
        assert profile.token == "new-token"
        assert profile.display_name == "NewHero"
        assert fresh_registry._dirty is True
    
    @pytest.mark.asyncio
    async def test_get_existing_player(self, populated_registry):
        """Should return existing player if token exists."""
        profile = await populated_registry.get_or_create_player(
            token="token-1",
            display_name="Different Name"  # Should be ignored
        )
        
        assert profile.display_name == "Player1"  # Original name preserved
    
    @pytest.mark.asyncio
    async def test_updates_last_seen_on_get(self, populated_registry):
        """Getting existing player should update last_seen."""
        original = populated_registry._players["token-1"].last_seen
        
        import time
        time.sleep(0.01)
        
        await populated_registry.get_or_create_player("token-1")
        
        new_last_seen = populated_registry._players["token-1"].last_seen
        assert new_last_seen >= original
    
    @pytest.mark.asyncio
    async def test_default_display_name(self, fresh_registry):
        """Should generate default name if none provided."""
        profile = await fresh_registry.get_or_create_player(token="abc-123")
        
        assert "Hero_" in profile.display_name


class TestPlayerRegistryGet:
    """Tests for get_player."""
    
    def test_get_existing_player(self, populated_registry):
        """Should return player if exists."""
        profile = populated_registry.get_player("token-1")
        
        assert profile is not None
        assert profile.display_name == "Player1"
    
    def test_get_nonexistent_player(self, populated_registry):
        """Should return None if not exists."""
        profile = populated_registry.get_player("nonexistent")
        
        assert profile is None


class TestPlayerRegistryGameTracking:
    """Tests for game assignment tracking."""
    
    @pytest.mark.asyncio
    async def test_update_player_game(self, populated_registry):
        """Should update current game assignment."""
        await populated_registry.update_player_game(
            token="token-3",
            game_id="game-002",
            player_id="p3"
        )
        
        player = populated_registry.get_player("token-3")
        assert player.current_game_id == "game-002"
        assert player.current_player_id == "p3"
    
    @pytest.mark.asyncio
    async def test_update_increments_games_played(self, populated_registry):
        """Joining a game should increment total_games_played."""
        player = populated_registry.get_player("token-3")
        original_count = player.total_games_played
        
        await populated_registry.update_player_game("token-3", "game-002")
        
        assert player.total_games_played == original_count + 1
    
    @pytest.mark.asyncio
    async def test_clear_player_game(self, populated_registry):
        """Should clear game assignment."""
        await populated_registry.clear_player_game("token-1")
        
        player = populated_registry.get_player("token-1")
        assert player.current_game_id is None
        assert player.current_player_id is None
    
    def test_find_player_game(self, populated_registry):
        """Should find which game a player is in."""
        game_id = populated_registry.find_player_game("token-1")
        
        assert game_id == "game-001"
    
    def test_find_player_game_returns_none_if_not_in_game(self, populated_registry):
        """Should return None if player not in any game."""
        game_id = populated_registry.find_player_game("token-3")
        
        assert game_id is None
    
    def test_get_players_in_game(self, populated_registry):
        """Should return all players in a game."""
        players = populated_registry.get_players_in_game("game-001")
        
        assert len(players) == 2
        tokens = {p.token for p in players}
        assert "token-1" in tokens
        assert "token-2" in tokens


class TestPlayerRegistryUpdates:
    """Tests for update operations."""
    
    @pytest.mark.asyncio
    async def test_update_display_name(self, populated_registry):
        """Should update display name."""
        result = await populated_registry.update_display_name(
            token="token-1",
            display_name="NewName"
        )
        
        assert result is True
        player = populated_registry.get_player("token-1")
        assert player.display_name == "NewName"
    
    @pytest.mark.asyncio
    async def test_update_display_name_nonexistent(self, populated_registry):
        """Should return False for nonexistent player."""
        result = await populated_registry.update_display_name(
            token="nonexistent",
            display_name="Name"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_nickname(self, populated_registry):
        """Should update nickname."""
        result = await populated_registry.update_nickname(
            token="token-1",
            nickname="The Brave"
        )
        
        assert result is True
        player = populated_registry.get_player("token-1")
        assert player.nickname == "The Brave"


class TestPlayerRegistryProperties:
    """Tests for registry properties."""
    
    def test_player_count(self, populated_registry):
        """player_count should return total players."""
        assert populated_registry.player_count == 3
    
    def test_active_player_count(self, populated_registry):
        """active_player_count should return players in games."""
        assert populated_registry.active_player_count == 2  # token-1 and token-2
    
    def test_players_property(self, populated_registry):
        """players property should return dict."""
        players = populated_registry.players
        
        assert isinstance(players, dict)
        assert len(players) == 3


class TestPlayerRegistrySingleton:
    """Tests for singleton behavior."""
    
    def test_registry_is_singleton(self):
        """Multiple PlayerRegistry() calls should return same instance."""
        registry1 = PlayerRegistry()
        registry2 = PlayerRegistry()
        
        assert registry1 is registry2
