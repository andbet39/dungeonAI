"""
Tests for Player Stats Tracker service.

Tests cover:
- PlayerStats creation and serialization
- Stat incrementing
- Monster kill recording with XP
- XP calculation by Challenge Rating
- Nickname refresh threshold
- Event-driven stat tracking
- Leaderboard generation
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.player_stats import (
    PlayerStats, StatType, PlayerStatsTracker,
    get_xp_for_cr, XP_BY_CHALLENGE_RATING
)
from app.core.events import GameEvent, EventType


# ============================================================================
# XP CALCULATION TESTS
# ============================================================================

class TestXPCalculation:
    """Tests for XP by Challenge Rating."""
    
    def test_exact_cr_match(self):
        """Should return exact XP for matching CR."""
        assert get_xp_for_cr(0.25) == 50
        assert get_xp_for_cr(0.5) == 100
        assert get_xp_for_cr(1.0) == 200
        assert get_xp_for_cr(5.0) == 1800
    
    def test_zero_cr(self):
        """CR 0 should return 10 XP."""
        assert get_xp_for_cr(0.0) == 10
    
    def test_intermediate_cr(self):
        """CR between defined values should use lower bound."""
        # 0.3 is between 0.25 (50) and 0.5 (100)
        xp = get_xp_for_cr(0.3)
        assert xp == 50  # Uses 0.25's XP
    
    def test_high_cr(self):
        """High CR should use highest defined value."""
        # 8.0 is the highest in table
        assert get_xp_for_cr(8.0) == 3900
        # Anything higher should also return 3900
        assert get_xp_for_cr(10.0) == 3900


# ============================================================================
# PLAYERSTATS TESTS
# ============================================================================

class TestPlayerStatsCreation:
    """Tests for PlayerStats dataclass."""
    
    def test_create_with_token(self):
        """Creating stats should set token and defaults."""
        stats = PlayerStats(token="player-token-123")
        
        assert stats.token == "player-token-123"
        assert stats.monsters_killed == 0
        assert stats.experience_earned == 0
        assert stats.damage_dealt == 0
    
    def test_default_kills_by_type(self):
        """kills_by_type should default to empty dict."""
        stats = PlayerStats(token="t1")
        
        assert stats.kills_by_type == {}
    
    def test_to_dict(self):
        """to_dict should serialize all fields."""
        stats = PlayerStats(
            token="t1",
            monsters_killed=10,
            experience_earned=500
        )
        
        data = stats.to_dict()
        
        assert data["token"] == "t1"
        assert data["monsters_killed"] == 10
        assert data["experience_earned"] == 500
        assert "first_game_at" in data
        assert "last_updated" in data
    
    def test_from_dict(self):
        """from_dict should deserialize correctly."""
        data = {
            "token": "t2",
            "monsters_killed": 25,
            "damage_dealt": 500,
            "kills_by_type": {"goblin": 15, "orc": 10}
        }
        
        stats = PlayerStats.from_dict(data)
        
        assert stats.token == "t2"
        assert stats.monsters_killed == 25
        assert stats.kills_by_type["goblin"] == 15


class TestPlayerStatsIncrement:
    """Tests for stat incrementing."""
    
    def test_increment_monsters_killed(self):
        """Should increment monsters_killed."""
        stats = PlayerStats(token="t1")
        
        stats.increment(StatType.MONSTERS_KILLED)
        
        assert stats.monsters_killed == 1
    
    def test_increment_by_amount(self):
        """Should increment by specified amount."""
        stats = PlayerStats(token="t1")
        
        stats.increment(StatType.DAMAGE_DEALT, 25)
        
        assert stats.damage_dealt == 25
    
    def test_increment_multiple_stats(self):
        """Should track multiple stats independently."""
        stats = PlayerStats(token="t1")
        
        stats.increment(StatType.MONSTERS_KILLED, 5)
        stats.increment(StatType.DAMAGE_DEALT, 100)
        stats.increment(StatType.ROOMS_VISITED, 3)
        stats.increment(StatType.DEATHS, 2)
        
        assert stats.monsters_killed == 5
        assert stats.damage_dealt == 100
        assert stats.rooms_visited == 3
        assert stats.deaths == 2
    
    def test_increment_updates_last_updated(self):
        """Incrementing should update timestamp."""
        stats = PlayerStats(token="t1")
        original = stats.last_updated
        
        import time
        time.sleep(0.01)
        
        stats.increment(StatType.CRITICAL_HITS)
        
        assert stats.last_updated >= original


class TestPlayerStatsMonsterKill:
    """Tests for record_monster_kill."""
    
    def test_record_kill_increments_total(self):
        """Should increment total kills."""
        stats = PlayerStats(token="t1")
        
        stats.record_monster_kill("goblin", 0.25)
        
        assert stats.monsters_killed == 1
    
    def test_record_kill_tracks_by_type(self):
        """Should track kills by monster type."""
        stats = PlayerStats(token="t1")
        
        stats.record_monster_kill("goblin", 0.25)
        stats.record_monster_kill("goblin", 0.25)
        stats.record_monster_kill("orc", 0.5)
        
        assert stats.kills_by_type["goblin"] == 2
        assert stats.kills_by_type["orc"] == 1
    
    def test_record_kill_awards_xp(self):
        """Should award XP based on CR."""
        stats = PlayerStats(token="t1")
        
        xp = stats.record_monster_kill("goblin", 0.25)
        
        assert xp == 50
        assert stats.experience_earned == 50
    
    def test_record_kill_cumulative_xp(self):
        """XP should accumulate."""
        stats = PlayerStats(token="t1")
        
        stats.record_monster_kill("goblin", 0.25)  # 50
        stats.record_monster_kill("orc", 0.5)      # 100
        stats.record_monster_kill("ogre", 2.0)     # 450
        
        assert stats.experience_earned == 600


class TestPlayerStatsNickname:
    """Tests for nickname refresh threshold."""
    
    def test_no_nickname_refresh_at_zero_kills(self):
        """Should not refresh until 5 kills."""
        stats = PlayerStats(token="t1")
        
        assert stats.needs_nickname_refresh() is False
    
    def test_needs_nickname_at_5_kills(self):
        """Should need nickname after 5 kills."""
        stats = PlayerStats(token="t1", monsters_killed=5)
        
        assert stats.needs_nickname_refresh() is True
    
    def test_needs_refresh_at_50_percent_increase(self):
        """Should need refresh when kills increase by 50%."""
        stats = PlayerStats(
            token="t1",
            monsters_killed=15,
            kills_at_last_nickname=10
        )
        
        assert stats.needs_nickname_refresh() is True
    
    def test_no_refresh_before_threshold(self):
        """Should not refresh before 50% increase."""
        stats = PlayerStats(
            token="t1",
            monsters_killed=12,  # Less than 15 (10 * 1.5)
            kills_at_last_nickname=10
        )
        
        assert stats.needs_nickname_refresh() is False


class TestPlayerStatsTopKill:
    """Tests for get_top_kill_type."""
    
    def test_no_kills(self):
        """Should return None if no kills."""
        stats = PlayerStats(token="t1")
        
        assert stats.get_top_kill_type() is None
    
    def test_single_type(self):
        """Should return the only type."""
        stats = PlayerStats(
            token="t1",
            kills_by_type={"goblin": 10}
        )
        
        top = stats.get_top_kill_type()
        assert top == ("goblin", 10)
    
    def test_multiple_types(self):
        """Should return type with most kills."""
        stats = PlayerStats(
            token="t1",
            kills_by_type={"goblin": 5, "orc": 15, "skeleton": 3}
        )
        
        top = stats.get_top_kill_type()
        assert top == ("orc", 15)


# ============================================================================
# PLAYERSTATSTRACKER TESTS
# ============================================================================

@pytest.fixture
def fresh_tracker():
    """Create a fresh PlayerStatsTracker for testing."""
    tracker = object.__new__(PlayerStatsTracker)
    tracker._stats = {}
    tracker._handlers = {}
    tracker._lock = asyncio.Lock()
    tracker._dirty = False
    tracker._save_task = None
    tracker._initialized = True
    return tracker


@pytest.fixture
def populated_tracker(fresh_tracker):
    """Create a tracker with some player stats."""
    fresh_tracker._stats = {
        "token-1": PlayerStats(
            token="token-1",
            monsters_killed=10,
            experience_earned=500,
            damage_dealt=200
        ),
        "token-2": PlayerStats(
            token="token-2",
            monsters_killed=25,
            experience_earned=1200,
            damage_dealt=500
        ),
        "token-3": PlayerStats(
            token="token-3",
            monsters_killed=5,
            experience_earned=250,
            damage_dealt=100
        )
    }
    return fresh_tracker


class TestTrackerGetOrCreate:
    """Tests for get_or_create_stats."""
    
    def test_create_new_stats(self, fresh_tracker):
        """Should create stats for new token."""
        stats = fresh_tracker.get_or_create_stats("new-token")
        
        assert stats.token == "new-token"
        assert stats.monsters_killed == 0
        assert fresh_tracker._dirty is True
    
    def test_get_existing_stats(self, populated_tracker):
        """Should return existing stats."""
        stats = populated_tracker.get_or_create_stats("token-1")
        
        assert stats.monsters_killed == 10


class TestTrackerGetStats:
    """Tests for get_stats."""
    
    def test_get_existing(self, populated_tracker):
        """Should return stats if exists."""
        stats = populated_tracker.get_stats("token-1")
        
        assert stats is not None
        assert stats.experience_earned == 500
    
    def test_get_nonexistent(self, populated_tracker):
        """Should return None if not exists."""
        stats = populated_tracker.get_stats("nonexistent")
        
        assert stats is None


class TestTrackerIncrementStat:
    """Tests for increment_stat."""
    
    def test_increment_existing_player(self, populated_tracker):
        """Should increment stat for existing player."""
        populated_tracker.increment_stat("token-1", StatType.DAMAGE_DEALT, 50)
        
        stats = populated_tracker.get_stats("token-1")
        assert stats.damage_dealt == 250  # 200 + 50
    
    def test_increment_creates_stats_if_needed(self, fresh_tracker):
        """Should create stats if player doesn't exist."""
        fresh_tracker.increment_stat("new-token", StatType.ROOMS_VISITED)
        
        stats = fresh_tracker.get_stats("new-token")
        assert stats is not None
        assert stats.rooms_visited == 1


class TestTrackerRecordMethods:
    """Tests for convenience recording methods."""
    
    def test_record_death(self, populated_tracker):
        """Should record a death."""
        populated_tracker.record_death("token-1")
        
        stats = populated_tracker.get_stats("token-1")
        assert stats.deaths == 1
    
    def test_record_game_completed(self, populated_tracker):
        """Should record game completion."""
        populated_tracker.record_game_completed("token-1")
        
        stats = populated_tracker.get_stats("token-1")
        assert stats.games_completed == 1


class TestTrackerLeaderboard:
    """Tests for leaderboard generation."""
    
    def test_get_leaderboard_by_kills(self, populated_tracker):
        """Should return players sorted by kills."""
        leaderboard = populated_tracker.get_leaderboard(StatType.MONSTERS_KILLED)
        
        assert len(leaderboard) == 3
        assert leaderboard[0]["token"] == "token-2"  # 25 kills
        assert leaderboard[1]["token"] == "token-1"  # 10 kills
        assert leaderboard[2]["token"] == "token-3"  # 5 kills
    
    def test_get_leaderboard_respects_limit(self, populated_tracker):
        """Should respect limit parameter."""
        leaderboard = populated_tracker.get_leaderboard(
            StatType.EXPERIENCE_EARNED,
            limit=2
        )
        
        assert len(leaderboard) == 2
    
    def test_get_xp_leaderboard(self, populated_tracker):
        """Should return XP leaderboard with full stats."""
        leaderboard = populated_tracker.get_xp_leaderboard()
        
        assert len(leaderboard) == 3
        top_player = leaderboard[0]
        assert top_player["token"] == "token-2"
        assert top_player["experience"] == 1200
        assert top_player["kills"] == 25
        assert "nickname" in top_player


class TestTrackerNicknameUpdate:
    """Tests for nickname updating."""
    
    @pytest.mark.asyncio
    async def test_update_nickname(self, populated_tracker):
        """Should update nickname and reset threshold."""
        stats = populated_tracker.get_stats("token-1")
        original_kills = stats.monsters_killed
        
        await populated_tracker.update_nickname("token-1", "The Brave")
        
        assert stats.nickname == "The Brave"
        assert stats.kills_at_last_nickname == original_kills


class TestTrackerSingleton:
    """Tests for singleton behavior."""
    
    def test_tracker_is_singleton(self):
        """Multiple PlayerStatsTracker() calls should return same instance."""
        tracker1 = PlayerStatsTracker()
        tracker2 = PlayerStatsTracker()
        
        assert tracker1 is tracker2


# ============================================================================
# EVENT HANDLER TESTS
# ============================================================================

class TestTrackerEventHandlers:
    """Tests for event-driven stat tracking."""
    
    def test_handle_monster_killed(self, fresh_tracker):
        """Should record kill when monster dies."""
        # Register the handler
        fresh_tracker._register_default_handlers = lambda: None
        
        event = GameEvent(
            type=EventType.MONSTER_DIED,
            data={
                "player_token": "token-1",
                "monster_type": "goblin",
                "challenge_rating": 0.25
            }
        )
        
        # Simulate handler call
        fresh_tracker._handle_monster_killed("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.monsters_killed == 1
        assert stats.experience_earned == 50
        assert stats.kills_by_type["goblin"] == 1
    
    def test_handle_room_entered_first_visit(self, fresh_tracker):
        """Should count first room visit."""
        event = GameEvent(
            type=EventType.PLAYER_ENTERED_ROOM,
            data={"player_token": "token-1", "first_visit": True}
        )
        
        fresh_tracker._handle_room_entered("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.rooms_visited == 1
    
    def test_handle_room_entered_revisit_not_counted(self, fresh_tracker):
        """Should not count revisits."""
        event = GameEvent(
            type=EventType.PLAYER_ENTERED_ROOM,
            data={"player_token": "token-1", "first_visit": False}
        )
        
        fresh_tracker._handle_room_entered("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats is None  # Not created because not first visit
    
    def test_handle_damage_dealt_as_player(self, fresh_tracker):
        """Should track damage dealt by player."""
        event = GameEvent(
            type=EventType.DAMAGE_DEALT,
            data={
                "player_token": "token-1",
                "damage": 15,
                "is_player_source": True,
                "is_critical": False
            }
        )
        
        fresh_tracker._handle_damage_dealt("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.damage_dealt == 15
    
    def test_handle_damage_dealt_critical(self, fresh_tracker):
        """Should track critical hits."""
        event = GameEvent(
            type=EventType.DAMAGE_DEALT,
            data={
                "player_token": "token-1",
                "damage": 20,
                "is_player_source": True,
                "is_critical": True
            }
        )
        
        fresh_tracker._handle_damage_dealt("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.critical_hits == 1
    
    def test_handle_damage_taken(self, fresh_tracker):
        """Should track damage taken."""
        event = GameEvent(
            type=EventType.DAMAGE_DEALT,
            data={
                "player_token": "token-1",
                "damage": 10,
                "is_player_source": False
            }
        )
        
        fresh_tracker._handle_damage_dealt("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.damage_taken == 10
    
    def test_handle_player_died(self, fresh_tracker):
        """Should track player deaths."""
        event = GameEvent(
            type=EventType.PLAYER_DIED,
            data={"player_token": "token-1"}
        )
        
        fresh_tracker._handle_player_died("token-1", event)
        
        stats = fresh_tracker.get_stats("token-1")
        assert stats.deaths == 1
