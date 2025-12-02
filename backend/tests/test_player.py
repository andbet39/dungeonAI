"""
Tests for Player entity.

Tests cover:
- Player creation and serialization
- Stat modifiers calculation (D&D style)
- Damage/healing mechanics
- Respawn functionality
- Defensive stance and AC calculation
- Fight immunity system
"""
import pytest
import time
from app.domain.entities import Player


class TestPlayerCreation:
    """Tests for Player instantiation and default values."""
    
    def test_create_basic_player_with_required_fields(self):
        """Creating a player with minimal required fields should work."""
        player = Player(id="p1", x=0, y=0)
        
        assert player.id == "p1"
        assert player.x == 0
        assert player.y == 0
        assert player.symbol == "@"
        assert player.hp == 30
        assert player.max_hp == 30
    
    def test_create_player_with_all_fields(self):
        """Creating a player with all fields should set them correctly."""
        player = Player(
            id="hero-1",
            x=10,
            y=20,
            symbol="H",
            color="#00ff00",
            current_room_id="room-5",
            name="Brave Hero",
            hp=25,
            max_hp=35,
            ac=15,
            str=14,
            dex=16,
            con=12,
            damage_dice="1d8+2"
        )
        
        assert player.id == "hero-1"
        assert player.x == 10
        assert player.y == 20
        assert player.name == "Brave Hero"
        assert player.hp == 25
        assert player.max_hp == 35
        assert player.ac == 15
        assert player.str == 14
        assert player.dex == 16
        assert player.con == 12
        assert player.damage_dice == "1d8+2"
    
    def test_player_position_property(self, basic_player):
        """Position property should return (x, y) tuple."""
        assert basic_player.position == (5, 5)


class TestPlayerStatModifiers:
    """Tests for D&D-style ability score modifiers."""
    
    @pytest.mark.parametrize("stat_value,expected_mod", [
        (1, -5),
        (6, -2),
        (8, -1),
        (10, 0),
        (11, 0),
        (12, 1),
        (14, 2),
        (16, 3),
        (18, 4),
        (20, 5),
    ])
    def test_get_modifier_formula(self, stat_value, expected_mod):
        """Modifier should be (stat - 10) // 2."""
        player = Player(id="test", x=0, y=0)
        assert player.get_modifier(stat_value) == expected_mod
    
    def test_str_mod_property(self):
        """Strength modifier should be calculated from str stat."""
        player = Player(id="test", x=0, y=0, str=14)
        assert player.str_mod == 2
    
    def test_dex_mod_property(self):
        """Dexterity modifier should be calculated from dex stat."""
        player = Player(id="test", x=0, y=0, dex=16)
        assert player.dex_mod == 3
    
    def test_con_mod_property(self):
        """Constitution modifier should be calculated from con stat."""
        player = Player(id="test", x=0, y=0, con=8)
        assert player.con_mod == -1


class TestPlayerEffectiveAC:
    """Tests for Armor Class calculations including defensive stance."""
    
    def test_effective_ac_without_defending(self):
        """Base effective AC equals AC when not defending."""
        player = Player(id="test", x=0, y=0, ac=14)
        player.is_defending = False
        
        assert player.effective_ac == 14
    
    def test_effective_ac_with_defending(self):
        """Defending adds +2 to effective AC."""
        player = Player(id="test", x=0, y=0, ac=14)
        player.is_defending = True
        
        assert player.effective_ac == 16
    
    def test_defending_player_fixture_has_bonus(self, defending_player):
        """The defending_player fixture should have +2 AC bonus."""
        # Base AC is 14, defending adds +2
        assert defending_player.effective_ac == 16


class TestPlayerDamageAndHealing:
    """Tests for combat damage and healing mechanics."""
    
    def test_take_damage_reduces_hp(self, basic_player):
        """Taking damage should reduce HP."""
        initial_hp = basic_player.hp
        actual = basic_player.take_damage(10)
        
        assert actual == 10
        assert basic_player.hp == initial_hp - 10
    
    def test_take_damage_cannot_exceed_current_hp(self, wounded_player):
        """Damage taken cannot exceed current HP."""
        # Wounded player has 5 HP
        actual = wounded_player.take_damage(100)
        
        assert actual == 5
        assert wounded_player.hp == 0
    
    def test_take_damage_returns_actual_damage(self, basic_player):
        """take_damage should return the actual damage dealt."""
        basic_player.hp = 3
        actual = basic_player.take_damage(10)
        
        assert actual == 3
    
    def test_heal_increases_hp(self, wounded_player):
        """Healing should increase HP."""
        initial_hp = wounded_player.hp
        actual = wounded_player.heal(10)
        
        assert actual == 10
        assert wounded_player.hp == initial_hp + 10
    
    def test_heal_cannot_exceed_max_hp(self, wounded_player):
        """Healing cannot raise HP above max_hp."""
        # Wounded player: hp=5, max_hp=30, so can heal max 25
        actual = wounded_player.heal(100)
        
        assert actual == 25
        assert wounded_player.hp == wounded_player.max_hp
    
    def test_heal_returns_actual_amount_healed(self, basic_player):
        """heal should return the actual amount healed."""
        basic_player.hp = basic_player.max_hp - 3
        actual = basic_player.heal(10)
        
        assert actual == 3
    
    def test_heal_at_full_hp_returns_zero(self, basic_player):
        """Healing at full HP should return 0."""
        actual = basic_player.heal(10)
        
        assert actual == 0
        assert basic_player.hp == basic_player.max_hp


class TestPlayerIsAlive:
    """Tests for the is_alive property."""
    
    def test_is_alive_when_hp_positive(self, basic_player):
        """Player is alive when HP > 0."""
        assert basic_player.is_alive is True
    
    def test_is_alive_when_hp_zero(self, basic_player):
        """Player is dead when HP = 0."""
        basic_player.hp = 0
        assert basic_player.is_alive is False
    
    def test_is_alive_after_lethal_damage(self, basic_player):
        """Player should be dead after taking lethal damage."""
        basic_player.take_damage(100)
        assert basic_player.is_alive is False


class TestPlayerRespawn:
    """Tests for player respawn mechanics."""
    
    def test_respawn_sets_position(self, wounded_player):
        """Respawn should move player to new position."""
        wounded_player.respawn(100, 200)
        
        assert wounded_player.x == 100
        assert wounded_player.y == 200
    
    def test_respawn_restores_full_hp(self, wounded_player):
        """Respawn should restore HP to max."""
        assert wounded_player.hp < wounded_player.max_hp
        wounded_player.respawn(0, 0)
        
        assert wounded_player.hp == wounded_player.max_hp
    
    def test_respawn_clears_defending_status(self, defending_player):
        """Respawn should clear defensive stance."""
        assert defending_player.is_defending is True
        defending_player.respawn(0, 0)
        
        assert defending_player.is_defending is False
    
    def test_respawn_clears_room_id(self, basic_player):
        """Respawn should clear current room reference."""
        assert basic_player.current_room_id is not None
        basic_player.respawn(0, 0)
        
        assert basic_player.current_room_id is None


class TestPlayerFightImmunity:
    """Tests for the post-combat immunity system."""
    
    def test_no_immunity_by_default(self):
        """New players should not have fight immunity."""
        player = Player(id="test", x=0, y=0)
        assert player.has_fight_immunity is False
    
    def test_grant_fight_immunity(self):
        """Granting immunity should make has_fight_immunity True."""
        player = Player(id="test", x=0, y=0)
        player.grant_fight_immunity(duration=2.0)
        
        assert player.has_fight_immunity is True
    
    def test_fight_immunity_expires(self):
        """Fight immunity should expire after duration."""
        player = Player(id="test", x=0, y=0)
        player.grant_fight_immunity(duration=0.01)  # Very short duration
        
        time.sleep(0.02)  # Wait for expiration
        
        assert player.has_fight_immunity is False
    
    def test_fight_immunity_default_duration(self):
        """Default immunity duration should be 2 seconds."""
        player = Player(id="test", x=0, y=0)
        before = time.time()
        player.grant_fight_immunity()
        
        # Should be immune for ~2 seconds
        assert player.fight_immunity_until > before + 1.5
        assert player.fight_immunity_until < before + 3.0


class TestPlayerSerialization:
    """Tests for Player to_dict and from_dict methods."""
    
    def test_to_dict_includes_all_fields(self, basic_player):
        """to_dict should include all relevant player fields."""
        data = basic_player.to_dict()
        
        assert data["id"] == basic_player.id
        assert data["x"] == basic_player.x
        assert data["y"] == basic_player.y
        assert data["hp"] == basic_player.hp
        assert data["max_hp"] == basic_player.max_hp
        assert data["ac"] == basic_player.ac
        assert data["str"] == basic_player.str
        assert data["dex"] == basic_player.dex
        assert data["con"] == basic_player.con
        assert data["effective_ac"] == basic_player.effective_ac
        assert data["str_mod"] == basic_player.str_mod
        assert data["dex_mod"] == basic_player.dex_mod
        assert data["con_mod"] == basic_player.con_mod
    
    def test_from_dict_creates_equivalent_player(self, basic_player):
        """from_dict should create an equivalent player."""
        data = basic_player.to_dict()
        restored = Player.from_dict(data)
        
        assert restored.id == basic_player.id
        assert restored.x == basic_player.x
        assert restored.y == basic_player.y
        assert restored.hp == basic_player.hp
        assert restored.max_hp == basic_player.max_hp
        assert restored.ac == basic_player.ac
        assert restored.str == basic_player.str
    
    def test_from_dict_handles_missing_optional_fields(self):
        """from_dict should handle missing optional fields with defaults."""
        minimal_data = {"id": "p1", "x": 0, "y": 0}
        player = Player.from_dict(minimal_data)
        
        assert player.hp == 30
        assert player.max_hp == 30
        assert player.ac == 12
        assert player.symbol == "@"
    
    def test_serialization_roundtrip(self, defending_player):
        """Serializing and deserializing should preserve state."""
        data = defending_player.to_dict()
        restored = Player.from_dict(data)
        
        assert restored.is_defending == defending_player.is_defending
        assert restored.color == defending_player.color
        assert restored.damage_dice == defending_player.damage_dice
