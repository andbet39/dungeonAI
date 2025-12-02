"""
Tests for Monster entity and MonsterStats.

Tests cover:
- Monster creation and serialization
- MonsterStats D&D-style modifiers
- Damage mechanics
- MonsterIntelligenceState tracking
- MonsterBehavior enum
"""
import pytest
from app.domain.entities import (
    Monster, MonsterStats, MonsterBehavior, MonsterIntelligenceState
)


class TestMonsterStatsCreation:
    """Tests for MonsterStats instantiation and defaults."""
    
    def test_create_monster_stats_with_required_fields(self):
        """Creating MonsterStats with all required fields should work."""
        stats = MonsterStats(
            hp=10, max_hp=10, ac=12,
            str=10, dex=10, con=10, int=10, wis=10, cha=10
        )
        
        assert stats.hp == 10
        assert stats.max_hp == 10
        assert stats.ac == 12
        assert stats.speed == 30  # default
        assert stats.challenge_rating == 0.25  # default
    
    def test_monster_stats_with_custom_challenge_rating(self):
        """MonsterStats should accept custom challenge rating."""
        stats = MonsterStats(
            hp=50, max_hp=50, ac=16,
            str=18, dex=10, con=16, int=6, wis=10, cha=6,
            challenge_rating=3.0
        )
        
        assert stats.challenge_rating == 3.0


class TestMonsterStatsModifiers:
    """Tests for D&D-style stat modifiers."""
    
    @pytest.mark.parametrize("stat_value,expected_mod", [
        (6, -2),
        (8, -1),
        (10, 0),
        (12, 1),
        (14, 2),
        (16, 3),
        (18, 4),
    ])
    def test_get_modifier_calculation(self, stat_value, expected_mod):
        """Modifier should follow (stat - 10) // 2 formula."""
        stats = MonsterStats(
            hp=10, max_hp=10, ac=10,
            str=10, dex=10, con=10, int=10, wis=10, cha=10
        )
        assert stats.get_modifier(stat_value) == expected_mod


class TestMonsterStatsSerialization:
    """Tests for MonsterStats serialization."""
    
    def test_to_dict_includes_all_stats(self):
        """to_dict should include all stat fields."""
        stats = MonsterStats(
            hp=15, max_hp=20, ac=14,
            str=16, dex=12, con=14, int=8, wis=10, cha=6,
            speed=40, challenge_rating=1.0
        )
        data = stats.to_dict()
        
        assert data["hp"] == 15
        assert data["max_hp"] == 20
        assert data["ac"] == 14
        assert data["str"] == 16
        assert data["speed"] == 40
        assert data["challenge_rating"] == 1.0
    
    def test_from_dict_restores_stats(self):
        """from_dict should restore MonsterStats correctly."""
        data = {
            "hp": 25, "max_hp": 30, "ac": 15,
            "str": 18, "dex": 10, "con": 16, "int": 6, "wis": 8, "cha": 6,
            "speed": 35, "challenge_rating": 2.0
        }
        stats = MonsterStats.from_dict(data)
        
        assert stats.hp == 25
        assert stats.max_hp == 30
        assert stats.challenge_rating == 2.0
    
    def test_from_dict_handles_missing_fields(self):
        """from_dict should use defaults for missing fields."""
        minimal_data = {"hp": 10, "ac": 12}
        stats = MonsterStats.from_dict(minimal_data)
        
        assert stats.hp == 10
        assert stats.max_hp == 10  # defaults to hp
        assert stats.ac == 12
        assert stats.speed == 30
        assert stats.challenge_rating == 0.25


class TestMonsterBehaviorEnum:
    """Tests for MonsterBehavior enumeration."""
    
    def test_all_behavior_types_exist(self):
        """All expected behavior types should be defined."""
        behaviors = [
            MonsterBehavior.STATIC,
            MonsterBehavior.PATROL,
            MonsterBehavior.SEARCHING,
            MonsterBehavior.AGGRESSIVE,
            MonsterBehavior.FLEEING,
            MonsterBehavior.AMBUSH,
            MonsterBehavior.WANDER,
            MonsterBehavior.HAUNT,
            MonsterBehavior.RITUAL,
        ]
        assert len(behaviors) == 9
    
    def test_behavior_values_are_strings(self):
        """Behavior values should be lowercase strings."""
        assert MonsterBehavior.PATROL.value == "patrol"
        assert MonsterBehavior.AGGRESSIVE.value == "aggressive"


class TestMonsterIntelligenceState:
    """Tests for MonsterIntelligenceState tracking."""
    
    def test_default_state_is_empty(self):
        """Default intelligence state should have empty/zero values."""
        state = MonsterIntelligenceState()
        
        assert state.memory_events == []
        assert state.last_state_index is None
        assert state.last_action is None
        assert state.last_reward == 0.0
        assert state.generation == 0
    
    def test_to_dict_serialization(self):
        """to_dict should serialize all fields."""
        state = MonsterIntelligenceState(
            last_state_index=42,
            last_action="ATTACK_AGGRESSIVE",
            last_reward=10.0,
            generation=3,
            last_world_state={"nearby_enemies": 1}
        )
        data = state.to_dict()
        
        assert data["last_state_index"] == 42
        assert data["last_action"] == "ATTACK_AGGRESSIVE"
        assert data["last_reward"] == 10.0
        assert data["generation"] == 3
        assert data["last_world_state"]["nearby_enemies"] == 1
    
    def test_from_dict_deserialization(self):
        """from_dict should restore state correctly."""
        data = {
            "last_state_index": 100,
            "last_action": "FLEE",
            "last_reward": -50.0,
            "generation": 5,
            "memory_events": [{"source": "p1"}]
        }
        state = MonsterIntelligenceState.from_dict(data)
        
        assert state.last_state_index == 100
        assert state.last_action == "FLEE"
        assert state.last_reward == -50.0
        assert state.generation == 5
    
    def test_from_dict_handles_none(self):
        """from_dict should handle None input."""
        state = MonsterIntelligenceState.from_dict(None)
        
        assert state.last_state_index is None
        assert state.memory_events == []


class TestMonsterCreation:
    """Tests for Monster entity creation."""
    
    def test_create_monster_with_required_fields(self, basic_monster):
        """Creating a monster with required fields should work."""
        assert basic_monster.id == "monster-001"
        assert basic_monster.monster_type == "goblin"
        assert basic_monster.name == "Test Goblin"
        assert basic_monster.x == 5
        assert basic_monster.y == 5
    
    def test_monster_position_property(self, basic_monster):
        """Position property should return (x, y) tuple."""
        assert basic_monster.position == (5, 5)
    
    def test_monster_behavior_is_set(self, basic_monster, strong_monster):
        """Monster behavior should be set correctly."""
        assert basic_monster.behavior == MonsterBehavior.PATROL
        assert strong_monster.behavior == MonsterBehavior.AGGRESSIVE


class TestMonsterDamage:
    """Tests for monster damage mechanics."""
    
    def test_take_damage_reduces_hp(self, basic_monster):
        """Taking damage should reduce monster HP."""
        initial_hp = basic_monster.stats.hp
        actual = basic_monster.take_damage(5)
        
        assert actual == 5
        assert basic_monster.stats.hp == initial_hp - 5
    
    def test_take_damage_cannot_exceed_current_hp(self, basic_monster):
        """Damage cannot exceed current HP."""
        basic_monster.stats.hp = 3
        actual = basic_monster.take_damage(100)
        
        assert actual == 3
        assert basic_monster.stats.hp == 0
    
    def test_is_alive_when_hp_positive(self, basic_monster):
        """Monster is alive when HP > 0."""
        assert basic_monster.is_alive is True
    
    def test_is_alive_when_hp_zero(self, basic_monster):
        """Monster is dead when HP = 0."""
        basic_monster.stats.hp = 0
        assert basic_monster.is_alive is False
    
    def test_is_alive_after_lethal_damage(self, basic_monster):
        """Monster should be dead after lethal damage."""
        basic_monster.take_damage(100)
        assert basic_monster.is_alive is False


class TestMonsterSerialization:
    """Tests for Monster serialization."""
    
    def test_to_dict_includes_all_fields(self, basic_monster):
        """to_dict should include all monster fields."""
        data = basic_monster.to_dict()
        
        assert data["id"] == "monster-001"
        assert data["monster_type"] == "goblin"
        assert data["name"] == "Test Goblin"
        assert data["x"] == 5
        assert data["y"] == 5
        assert data["room_id"] == "room-1"
        assert data["symbol"] == "g"
        assert data["color"] == "#0f0"
        assert data["behavior"] == "patrol"
        assert data["description"] == "A sneaky goblin"
        assert "stats" in data
        assert "intelligence_state" in data
    
    def test_from_dict_restores_monster(self, basic_monster):
        """from_dict should create equivalent monster."""
        data = basic_monster.to_dict()
        restored = Monster.from_dict(data)
        
        assert restored.id == basic_monster.id
        assert restored.monster_type == basic_monster.monster_type
        assert restored.name == basic_monster.name
        assert restored.x == basic_monster.x
        assert restored.y == basic_monster.y
        assert restored.behavior == basic_monster.behavior
        assert restored.stats.hp == basic_monster.stats.hp
    
    def test_serialization_preserves_intelligence_state(self, basic_monster):
        """Intelligence state should be preserved through serialization."""
        basic_monster.intelligence_state.last_action = "FLEE"
        basic_monster.intelligence_state.generation = 7
        
        data = basic_monster.to_dict()
        restored = Monster.from_dict(data)
        
        assert restored.intelligence_state.last_action == "FLEE"
        assert restored.intelligence_state.generation == 7
    
    def test_serialization_roundtrip(self, strong_monster):
        """Full serialization roundtrip should preserve all data."""
        strong_monster.patrol_target = (10, 10)
        strong_monster.last_move_tick = 500
        
        data = strong_monster.to_dict()
        restored = Monster.from_dict(data)
        
        assert restored.patrol_target == (10, 10)
        assert restored.last_move_tick == 500
        assert restored.stats.challenge_rating == 0.5


class TestMonsterChallengeRating:
    """Tests for challenge rating integration."""
    
    def test_low_cr_monster(self, basic_monster):
        """Low CR monster should have appropriate stats."""
        assert basic_monster.stats.challenge_rating == 0.25
        assert basic_monster.stats.hp == 10
    
    def test_higher_cr_monster(self, strong_monster):
        """Higher CR monster should have better stats."""
        assert strong_monster.stats.challenge_rating == 0.5
        assert strong_monster.stats.hp == 15
        assert strong_monster.stats.str == 16
