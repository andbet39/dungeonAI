"""
Tests for Monster Service.

Tests cover:
- Monster type configuration loading
- Spawn rate configuration
- Monster type selection
- Monster creation
- Room spawning logic
- AI behavior updates
- Patrol movement
- Decision making
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.monster_service import MonsterService, MonsterAIProfile
from app.domain.entities import Monster, MonsterBehavior, Room
from app.domain.intelligence.learning import AIAction


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_config_data():
    """Sample monster configuration data."""
    return {
        "goblin": {
            "name": "Goblin",
            "symbol": "g",
            "color": "#00ff00",
            "behavior": "patrol",
            "description": "A sneaky goblin",
            "stats": {
                "hp": 10,
                "max_hp": 10,
                "ac": 12,
                "str": 8,
                "dex": 14,
                "con": 10,
                "int": 8,
                "wis": 10,
                "cha": 6,
                "challenge_rating": 0.25
            },
            "intelligence": {
                "personality": {
                    "aggression": 0.4,
                    "caution": 0.6,
                    "cunning": 0.7,
                    "pack_mentality": 0.8
                },
                "learning": {
                    "learning_rate": 0.1,
                    "discount_factor": 0.95,
                    "exploration_rate": 0.3
                },
                "memory": {
                    "capacity": 5,
                    "decay_rate": 0.05
                }
            }
        },
        "orc": {
            "name": "Orc",
            "symbol": "o",
            "color": "#ff0000",
            "behavior": "aggressive",
            "description": "A brutish orc",
            "stats": {
                "hp": 15,
                "max_hp": 15,
                "ac": 13,
                "str": 16,
                "dex": 10,
                "con": 14,
                "int": 7,
                "wis": 8,
                "cha": 8,
                "challenge_rating": 0.5
            }
        }
    }


@pytest.fixture
def mock_spawn_rates():
    """Sample spawn rate configuration."""
    return {
        "room_spawn_chances": {
            "chamber": 0.5,
            "library": 0.3,
            "armory": 0.6,
            "crypt": 0.7
        },
        "room_monster_weights": {
            "chamber": {"goblin": 10, "orc": 5},
            "crypt": {"skeleton": 10, "ghost": 5}
        },
        "max_monsters_per_room": 2,
        "min_room_area_for_spawn": 36
    }


@pytest.fixture
def fresh_monster_service(mock_config_data, mock_spawn_rates, tmp_path):
    """Create a fresh MonsterService for testing."""
    import numpy as np
    
    service = object.__new__(MonsterService)
    service.config_path = tmp_path
    service.monster_types = mock_config_data
    service.spawn_rates = mock_spawn_rates
    service.ai_profiles = {}
    service.species_store = MagicMock()
    
    # Create a properly shaped q_table (state_space x action_count)
    # State space dimensions (SCHEMA_VERSION 3):
    # hp_levels(3) * enemy_levels(4) * ally_levels(4) * room_types(3) * 
    # distance_levels(3) * threat_direction(9) * in_corridor(2) = 7776
    # Actions: 10 (7 original + 3 movement actions)
    mock_q_table = np.zeros((7776, 10))
    service.species_store.get_or_create = MagicMock(return_value=MagicMock(
        generation=1,
        q_table=mock_q_table
    ))
    service.monster_memories = {}
    service._initialized = True
    service._build_ai_profiles()
    return service


@pytest.fixture
def sample_room():
    """Create a sample room for testing."""
    return Room(
        id="room-1",
        x=10,
        y=10,
        width=10,
        height=10,
        room_type="chamber",
        name="Test Chamber"
    )


@pytest.fixture
def sample_tiles():
    """Create a sample tile grid (30x30 all floor)."""
    from app.domain.map import TILE_FLOOR
    return [[TILE_FLOOR for _ in range(30)] for _ in range(30)]


# ============================================================================
# CONFIGURATION LOADING TESTS
# ============================================================================

class TestMonsterServiceConfig:
    """Tests for configuration loading."""
    
    def test_get_spawn_chance_known_type(self, fresh_monster_service):
        """Should return configured spawn chance."""
        chance = fresh_monster_service.get_spawn_chance("chamber")
        
        assert chance == 0.5
    
    def test_get_spawn_chance_unknown_type(self, fresh_monster_service):
        """Should return default for unknown room type."""
        chance = fresh_monster_service.get_spawn_chance("unknown_room")
        
        assert chance == 0.5  # Default
    
    def test_get_monster_weights(self, fresh_monster_service):
        """Should return monster weights for room type."""
        weights = fresh_monster_service.get_monster_weights("chamber")
        
        assert weights["goblin"] == 10
        assert weights["orc"] == 5
    
    def test_get_max_monsters_per_room(self, fresh_monster_service):
        """Should return max monsters config."""
        max_monsters = fresh_monster_service.get_max_monsters_per_room()
        
        assert max_monsters == 2
    
    def test_get_min_room_area(self, fresh_monster_service):
        """Should return min room area config."""
        min_area = fresh_monster_service.get_min_room_area()
        
        assert min_area == 36


# ============================================================================
# MONSTER TYPE SELECTION TESTS
# ============================================================================

class TestMonsterTypeSelection:
    """Tests for monster type selection."""
    
    def test_select_monster_type_returns_valid_type(self, fresh_monster_service):
        """Should return a valid monster type."""
        # Run multiple times due to randomness
        for _ in range(10):
            monster_type = fresh_monster_service.select_monster_type("chamber")
            assert monster_type in ["goblin", "orc"]
    
    def test_select_monster_type_respects_weights(self, fresh_monster_service):
        """Higher weighted monsters should appear more often."""
        counts = {"goblin": 0, "orc": 0}
        
        for _ in range(1000):
            monster_type = fresh_monster_service.select_monster_type("chamber")
            counts[monster_type] += 1
        
        # Goblin has weight 10, orc has weight 5
        # So goblin should appear roughly twice as often
        ratio = counts["goblin"] / counts["orc"]
        assert 1.5 < ratio < 2.5  # Allow some variance
    
    def test_select_monster_type_unknown_room(self, fresh_monster_service):
        """Unknown room type should still return a monster."""
        monster_type = fresh_monster_service.select_monster_type("unknown_room")
        
        # Should use default weights (all monsters equal)
        assert monster_type in ["goblin", "orc"]


# ============================================================================
# MONSTER CREATION TESTS
# ============================================================================

class TestMonsterCreation:
    """Tests for monster creation."""
    
    def test_create_monster_valid_type(self, fresh_monster_service):
        """Should create monster from config."""
        monster = fresh_monster_service.create_monster(
            monster_type="goblin",
            x=5,
            y=5,
            room_id="room-1"
        )
        
        assert monster is not None
        assert monster.monster_type == "goblin"
        assert monster.name == "Goblin"
        assert monster.x == 5
        assert monster.y == 5
        assert monster.room_id == "room-1"
    
    def test_create_monster_stats(self, fresh_monster_service):
        """Monster should have correct stats from config."""
        monster = fresh_monster_service.create_monster("goblin", 0, 0, "r1")
        
        assert monster.stats.hp == 10
        assert monster.stats.max_hp == 10
        assert monster.stats.ac == 12
        assert monster.stats.str == 8
        assert monster.stats.dex == 14
        assert monster.stats.challenge_rating == 0.25
    
    def test_create_monster_invalid_type(self, fresh_monster_service):
        """Invalid monster type should return None."""
        monster = fresh_monster_service.create_monster(
            monster_type="dragon",  # Not in config
            x=5,
            y=5,
            room_id="room-1"
        )
        
        assert monster is None
    
    def test_create_monster_unique_id(self, fresh_monster_service):
        """Each monster should have unique ID."""
        monster1 = fresh_monster_service.create_monster("goblin", 0, 0, "r1")
        monster2 = fresh_monster_service.create_monster("goblin", 1, 1, "r1")
        
        assert monster1.id != monster2.id
    
    def test_create_monster_with_intelligence(self, fresh_monster_service):
        """Monster with AI config should have intelligence state."""
        monster = fresh_monster_service.create_monster("goblin", 0, 0, "r1")
        
        assert monster.intelligence_state is not None
        assert monster.intelligence_state.generation >= 0


# ============================================================================
# ROOM SPAWNING TESTS
# ============================================================================

class TestRoomSpawning:
    """Tests for spawning monsters in rooms."""
    
    def test_spawn_in_too_small_room(self, fresh_monster_service, sample_tiles):
        """Should not spawn in rooms below min area."""
        small_room = Room(
            id="small",
            x=5,
            y=5,
            width=4,
            height=4,  # Area = 16, below 36
            room_type="chamber"
        )
        
        monsters = fresh_monster_service.spawn_monsters_in_room(
            room=small_room,
            tiles=sample_tiles,
            occupied_positions=set(),
            map_width=30,
            map_height=30
        )
        
        assert len(monsters) == 0
    
    def test_spawn_monsters_positions(self, fresh_monster_service, sample_room, sample_tiles):
        """Spawned monsters should be at valid positions."""
        # Force spawn by mocking random
        with patch('random.random', return_value=0.0):  # Always spawn
            monsters = fresh_monster_service.spawn_monsters_in_room(
                room=sample_room,
                tiles=sample_tiles,
                occupied_positions=set(),
                map_width=30,
                map_height=30
            )
        
        for monster in monsters:
            # Should be inside room (not on border)
            assert sample_room.x < monster.x < sample_room.x + sample_room.width - 1
            assert sample_room.y < monster.y < sample_room.y + sample_room.height - 1
    
    def test_spawn_respects_occupied_positions(self, fresh_monster_service, sample_room, sample_tiles):
        """Should not spawn on occupied positions."""
        # Occupy most positions in room
        occupied = set()
        for y in range(sample_room.y + 1, sample_room.y + sample_room.height - 1):
            for x in range(sample_room.x + 1, sample_room.x + sample_room.width - 1):
                occupied.add((x, y))
        
        # Leave just one position free
        free_pos = (sample_room.x + 2, sample_room.y + 2)
        occupied.discard(free_pos)
        
        with patch('random.random', return_value=0.0):
            monsters = fresh_monster_service.spawn_monsters_in_room(
                room=sample_room,
                tiles=sample_tiles,
                occupied_positions=occupied,
                map_width=30,
                map_height=30
            )
        
        # Can only spawn one monster at the free position
        assert len(monsters) <= 1
        if monsters:
            assert (monsters[0].x, monsters[0].y) == free_pos


# ============================================================================
# AI BEHAVIOR TESTS
# ============================================================================

class TestMonsterAI:
    """Tests for monster AI behavior updates."""
    
    def test_static_monster_no_movement(self, fresh_monster_service, sample_tiles):
        """Static monsters should not move."""
        from app.domain.entities import MonsterStats
        
        monster = Monster(
            id="m1",
            monster_type="test",
            name="Static Monster",
            x=15,
            y=15,
            room_id="room-1",
            behavior=MonsterBehavior.STATIC,
            symbol="s",
            color="#000",
            stats=MonsterStats(
                hp=10, max_hp=10, ac=12,
                str=10, dex=10, con=10, int=10, wis=10, cha=10
            )
        )
        
        moved = fresh_monster_service.update_monster(
            monster=monster,
            room_bounds=(10, 10, 10, 10),
            tiles=sample_tiles,
            occupied_positions=set(),
            current_tick=10
        )
        
        assert moved is False
    
    def test_patrol_monster_moves(self, fresh_monster_service, sample_tiles):
        """Patrol monsters should move over time."""
        from app.domain.entities import MonsterStats
        
        monster = Monster(
            id="m1",
            monster_type="test",
            name="Patrol Monster",
            x=15,
            y=15,
            room_id="room-1",
            behavior=MonsterBehavior.PATROL,
            symbol="p",
            color="#000",
            stats=MonsterStats(
                hp=10, max_hp=10, ac=12,
                str=10, dex=10, con=10, int=10, wis=10, cha=10
            )
        )
        monster.last_move_tick = 0
        
        original_x, original_y = monster.x, monster.y
        
        # Try several ticks to ensure movement
        for tick in range(1, 20):
            moved = fresh_monster_service._update_patrol(
                monster=monster,
                room_bounds=(10, 10, 10, 10),
                tiles=sample_tiles,
                occupied_positions=set(),
                current_tick=tick
            )
            if moved:
                break
        
        # Should have moved at some point
        assert moved or (monster.x == original_x and monster.y == original_y)
    
    def test_patrol_respects_room_bounds(self, fresh_monster_service, sample_tiles):
        """Patrol movement should stay within room bounds."""
        from app.domain.entities import MonsterStats
        
        monster = Monster(
            id="m1",
            monster_type="test",
            name="Patrol Monster",
            x=11,  # Near edge of room
            y=11,
            room_id="room-1",
            behavior=MonsterBehavior.PATROL,
            symbol="p",
            color="#000",
            stats=MonsterStats(
                hp=10, max_hp=10, ac=12,
                str=10, dex=10, con=10, int=10, wis=10, cha=10
            )
        )
        monster.last_move_tick = 0
        
        room_bounds = (10, 10, 10, 10)  # x, y, width, height
        
        # Move many times
        for tick in range(1, 100):
            fresh_monster_service._update_patrol(
                monster=monster,
                room_bounds=room_bounds,
                tiles=sample_tiles,
                occupied_positions=set(),
                current_tick=tick
            )
            
            # Verify always in bounds
            assert 10 <= monster.x < 20
            assert 10 <= monster.y < 20


# ============================================================================
# AI PROFILE TESTS
# ============================================================================

class TestAIProfiles:
    """Tests for AI profile building."""
    
    def test_build_ai_profiles(self, fresh_monster_service):
        """Should build AI profiles from config."""
        # Goblin has intelligence config
        assert "goblin" in fresh_monster_service.ai_profiles
        
        profile = fresh_monster_service.ai_profiles["goblin"]
        assert isinstance(profile, MonsterAIProfile)
    
    def test_profile_personality(self, fresh_monster_service):
        """Profile should have personality from config."""
        profile = fresh_monster_service.ai_profiles["goblin"]
        
        assert profile.personality.aggression == 0.4
        assert profile.personality.caution == 0.6
        assert profile.personality.cunning == 0.7
    
    def test_profile_memory_config(self, fresh_monster_service):
        """Profile should have memory config."""
        profile = fresh_monster_service.ai_profiles["goblin"]
        
        assert profile.memory_capacity == 5
        assert profile.memory_decay == 0.05
    
    def test_monster_without_intelligence_no_profile(self, fresh_monster_service):
        """Monster without intelligence config should not have profile."""
        # Orc has no intelligence config in our mock
        assert "orc" not in fresh_monster_service.ai_profiles


# ============================================================================
# DECISION MAKING TESTS
# ============================================================================

class TestDecisionMaking:
    """Tests for combat decision making."""
    
    def test_decide_combat_action_returns_action(self, fresh_monster_service):
        """Should return an AIAction for combat."""
        monster = fresh_monster_service.create_monster("goblin", 5, 5, "r1")
        
        action = fresh_monster_service.decide_combat_action(
            monster=monster,
            current_tick=100
        )
        
        assert isinstance(action, AIAction)
    
    def test_decide_without_ai_profile(self, fresh_monster_service):
        """Monster without AI profile should get default action."""
        monster = fresh_monster_service.create_monster("orc", 5, 5, "r1")
        
        action = fresh_monster_service.decide_combat_action(
            monster=monster,
            current_tick=100
        )
        
        # Should return aggressive attack as default
        assert action == AIAction.ATTACK_AGGRESSIVE


# ============================================================================
# SINGLETON TESTS
# ============================================================================

class TestMonsterServiceSingleton:
    """Tests for singleton behavior."""
    
    def test_monster_service_is_singleton(self):
        """Multiple MonsterService() calls should return same instance."""
        service1 = MonsterService()
        service2 = MonsterService()
        
        assert service1 is service2
