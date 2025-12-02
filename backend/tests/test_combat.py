"""
Tests for Combat system (Fight, Dice).

Tests cover:
- Fight creation and lifecycle
- Turn order management
- Player joining/leaving fights
- Turn advancement and timing
- Combat logging
- Dice rolling mechanics
- Attack rolls with criticals
- Damage rolls
"""
import pytest
import time
from app.domain.combat import (
    Fight, FightStatus,
    DiceRoll, roll_dice, roll_d20, roll_attack, roll_damage
)


# ============================================================================
# FIGHT ENTITY TESTS
# ============================================================================

class TestFightCreation:
    """Tests for Fight instantiation."""
    
    def test_create_fight_with_valid_params(self):
        """Creating a fight should set up initial state correctly."""
        fight = Fight.create(
            monster_id="m1",
            initiator_player_id="p1",
            turn_duration=60
        )
        
        assert fight.monster_id == "m1"
        assert "p1" in fight.player_ids
        assert fight.status == FightStatus.ACTIVE
        assert fight.turn_duration == 60
    
    def test_fight_generates_unique_id(self):
        """Each fight should have a unique ID."""
        fight1 = Fight.create("m1", "p1")
        fight2 = Fight.create("m1", "p1")
        
        assert fight1.id != fight2.id
    
    def test_initial_turn_order(self):
        """Turn order should include player and monster."""
        fight = Fight.create("m1", "p1")
        
        assert "p1" in fight.turn_order
        assert "m1" in fight.turn_order
        assert len(fight.turn_order) == 2
    
    def test_initiator_goes_first(self):
        """Player who initiated fight should go first."""
        fight = Fight.create("m1", "p1")
        
        assert fight.current_turn_id == "p1"


class TestFightTurnManagement:
    """Tests for turn order and progression."""
    
    def test_current_turn_id(self, active_fight):
        """current_turn_id should return the current actor."""
        # Initiator (player) goes first
        assert active_fight.current_turn_id == "player-001"
    
    def test_is_monster_turn_false_for_player_turn(self, active_fight):
        """is_monster_turn should be False when it's a player's turn."""
        assert active_fight.is_monster_turn is False
    
    def test_advance_turn_moves_to_next(self, active_fight):
        """advance_turn should move to the next actor in order."""
        first_turn = active_fight.current_turn_id
        active_fight.advance_turn()
        second_turn = active_fight.current_turn_id
        
        assert first_turn != second_turn
    
    def test_advance_turn_wraps_around(self, active_fight):
        """advance_turn should wrap back to first actor."""
        initial = active_fight.current_turn_id
        
        # Advance through all turns
        for _ in range(len(active_fight.turn_order)):
            active_fight.advance_turn()
        
        # Should be back to initial
        assert active_fight.current_turn_id == initial
    
    def test_is_monster_turn_after_player_acts(self, active_fight):
        """is_monster_turn should be True after player's turn."""
        active_fight.advance_turn()
        
        assert active_fight.is_monster_turn is True


class TestFightPlayerManagement:
    """Tests for adding/removing players from fights."""
    
    def test_add_player_to_fight(self, active_fight):
        """Adding a player should insert them in turn order."""
        result = active_fight.add_player("p2")
        
        assert result is True
        assert "p2" in active_fight.player_ids
        assert "p2" in active_fight.turn_order
    
    def test_cannot_add_duplicate_player(self, active_fight):
        """Cannot add the same player twice."""
        result = active_fight.add_player("player-001")
        
        assert result is False
    
    def test_new_player_added_before_monster(self, active_fight):
        """New players should be added before the monster in turn order."""
        active_fight.add_player("p2")
        
        monster_idx = active_fight.turn_order.index("monster-001")
        player_idx = active_fight.turn_order.index("p2")
        
        assert player_idx < monster_idx
    
    def test_remove_player_from_fight(self, multiplayer_fight):
        """Removing a player should update player list and turn order."""
        result = multiplayer_fight.remove_player("player-002")
        
        assert result is True
        assert "player-002" not in multiplayer_fight.player_ids
        assert "player-002" not in multiplayer_fight.turn_order
    
    def test_cannot_remove_nonexistent_player(self, active_fight):
        """Cannot remove a player not in the fight."""
        result = active_fight.remove_player("nonexistent")
        
        assert result is False
    
    def test_fight_ends_when_all_players_leave(self, active_fight):
        """Fight status should be FLED when all players leave."""
        active_fight.remove_player("player-001")
        
        assert active_fight.status == FightStatus.FLED
        assert active_fight.is_active is False


class TestFightStatus:
    """Tests for fight status and lifecycle."""
    
    def test_is_active_for_active_fight(self, active_fight):
        """is_active should be True for ACTIVE fights."""
        assert active_fight.is_active is True
    
    def test_is_active_false_after_end(self, active_fight):
        """is_active should be False after fight ends."""
        active_fight.end_fight("victory")
        
        assert active_fight.is_active is False
        assert active_fight.status == FightStatus.ENDED
    
    def test_end_fight_with_victory(self, active_fight):
        """end_fight should set status and log the result."""
        active_fight.end_fight("victory")
        
        assert active_fight.status == FightStatus.ENDED
        # Check combat log has the end entry
        assert any("victory" in entry["message"].lower() 
                   for entry in active_fight.combat_log)


class TestFightTiming:
    """Tests for turn timing mechanics."""
    
    def test_time_remaining_starts_positive(self, active_fight):
        """time_remaining should start positive."""
        assert active_fight.time_remaining > 0
    
    def test_time_remaining_decreases(self, active_fight):
        """time_remaining should decrease over time."""
        initial = active_fight.time_remaining
        time.sleep(0.1)
        
        assert active_fight.time_remaining < initial
    
    def test_time_remaining_never_negative(self, active_fight):
        """time_remaining should never be negative."""
        # Force turn end time to past
        active_fight.turn_end_time = time.time() - 100
        
        assert active_fight.time_remaining == 0
    
    def test_advance_turn_resets_timer(self, active_fight):
        """advance_turn should reset the turn timer."""
        # Wait a bit
        time.sleep(0.1)
        old_remaining = active_fight.time_remaining
        
        active_fight.advance_turn()
        
        # Should have full time again
        assert active_fight.time_remaining > old_remaining


class TestFightCombatLog:
    """Tests for combat logging."""
    
    def test_add_log_entry(self, active_fight):
        """add_log_entry should add entries to combat log."""
        initial_count = len(active_fight.combat_log)
        
        active_fight.add_log_entry("hit", "Player attacks!", source_id="p1")
        
        assert len(active_fight.combat_log) == initial_count + 1
    
    def test_log_entry_structure(self, active_fight):
        """Log entries should have proper structure."""
        active_fight.add_log_entry("damage", "10 damage dealt", source_id="p1")
        
        entry = active_fight.combat_log[-1]
        assert entry["type"] == "damage"
        assert entry["message"] == "10 damage dealt"
        assert entry["source_id"] == "p1"
        assert "timestamp" in entry


class TestFightSerialization:
    """Tests for Fight serialization."""
    
    def test_to_dict_includes_all_fields(self, active_fight):
        """to_dict should include all relevant fields."""
        data = active_fight.to_dict()
        
        assert "id" in data
        assert "monster_id" in data
        assert "player_ids" in data
        assert "turn_order" in data
        assert "current_turn_id" in data
        assert "is_monster_turn" in data
        assert "status" in data
        assert "time_remaining" in data
        assert "combat_log" in data
    
    def test_combat_log_truncated(self, active_fight):
        """to_dict should only return last 20 log entries."""
        for i in range(30):
            active_fight.add_log_entry("test", f"Entry {i}")
        
        data = active_fight.to_dict()
        
        assert len(data["combat_log"]) == 20


# ============================================================================
# DICE ROLLING TESTS
# ============================================================================

class TestDiceRoll:
    """Tests for the DiceRoll dataclass."""
    
    def test_dice_roll_string_representation(self):
        """DiceRoll __str__ should format nicely."""
        roll = DiceRoll(
            dice_notation="1d20+5",
            rolls=[15],
            modifier=5,
            total=20
        )
        
        result = str(roll)
        assert "15" in result
        assert "5" in result
        assert "20" in result
    
    def test_dice_roll_to_dict(self):
        """DiceRoll to_dict should include all fields."""
        roll = DiceRoll(
            dice_notation="2d6+3",
            rolls=[4, 5],
            modifier=3,
            total=12
        )
        
        data = roll.to_dict()
        assert data["dice"] == "2d6+3"
        assert data["rolls"] == [4, 5]
        assert data["modifier"] == 3
        assert data["total"] == 12


class TestRollDice:
    """Tests for roll_dice function."""
    
    def test_roll_single_die(self):
        """Rolling a single die should work."""
        for _ in range(10):
            roll = roll_dice("1d6")
            assert 1 <= roll.total <= 6
            assert len(roll.rolls) == 1
    
    def test_roll_multiple_dice(self):
        """Rolling multiple dice should sum them."""
        for _ in range(10):
            roll = roll_dice("2d6")
            assert 2 <= roll.total <= 12
            assert len(roll.rolls) == 2
    
    def test_roll_with_positive_modifier(self):
        """Positive modifier should be added."""
        roll = roll_dice("1d6+5")
        
        assert roll.modifier == 5
        assert roll.total == roll.rolls[0] + 5
    
    def test_roll_with_negative_modifier(self):
        """Negative modifier should be subtracted."""
        roll = roll_dice("1d6-2")
        
        assert roll.modifier == -2
        # Total can be 0 if roll is low
        assert roll.total >= 0
    
    def test_roll_minimum_is_zero(self):
        """Total should never be negative."""
        roll = roll_dice("1d4-10")
        
        assert roll.total >= 0
    
    def test_invalid_notation_defaults_to_d20(self):
        """Invalid notation should default to 1d20."""
        roll = roll_dice("invalid")
        
        assert roll.dice_notation == "1d20"
        assert 1 <= roll.total <= 20


class TestRollD20:
    """Tests for roll_d20 function."""
    
    def test_d20_range(self):
        """d20 should roll 1-20 plus modifier."""
        for _ in range(20):
            roll = roll_d20(0)
            assert 1 <= roll.total <= 20
    
    def test_d20_with_modifier(self):
        """d20 should add modifier to total."""
        roll = roll_d20(5)
        
        assert roll.modifier == 5
        assert roll.total == roll.rolls[0] + 5
    
    def test_d20_negative_modifier(self):
        """d20 should handle negative modifiers."""
        roll = roll_d20(-3)
        
        assert roll.modifier == -3


class TestRollAttack:
    """Tests for roll_attack function."""
    
    def test_attack_returns_tuple(self):
        """roll_attack should return (roll, hit, is_critical)."""
        result = roll_attack(attack_bonus=5, target_ac=15)
        
        assert len(result) == 3
        roll, hit, is_crit = result
        assert isinstance(roll, DiceRoll)
        assert isinstance(hit, bool)
        assert isinstance(is_crit, bool)
    
    def test_natural_20_always_crits(self):
        """Natural 20 should always be a critical hit."""
        # We can't force a natural 20, but we can verify the logic
        # by creating many rolls and checking any natural 20s
        crits_found = False
        for _ in range(1000):
            roll, hit, is_crit = roll_attack(0, 25)  # AC 25 = should miss normally
            if roll.rolls[0] == 20:
                assert hit is True  # Natural 20 always hits
                assert is_crit is True
                crits_found = True
        
        # Statistically should find at least one in 1000 rolls
        # (probability of 0 in 1000 rolls is tiny: 0.95^1000 ≈ 0)
    
    def test_natural_1_always_misses(self):
        """Natural 1 should always miss regardless of bonuses."""
        for _ in range(1000):
            roll, hit, is_crit = roll_attack(100, 5)  # Huge bonus, low AC
            if roll.rolls[0] == 1:
                assert hit is False
                assert is_crit is False
    
    def test_hit_determination(self):
        """Hit should be determined by total >= AC."""
        # Test with modifier that guarantees hit or miss
        # This is probabilistic but should work most of the time
        hits = 0
        for _ in range(100):
            roll, hit, _ = roll_attack(10, 15)  # +10 vs AC 15
            if hit:
                hits += 1
        
        # With +10 vs AC 15, we need 5+ on d20, so 80% should hit
        assert hits > 50  # Should be around 80


class TestRollDamage:
    """Tests for roll_damage function."""
    
    def test_normal_damage_roll(self):
        """Normal damage should roll specified dice."""
        for _ in range(10):
            roll = roll_damage("1d6")
            assert 1 <= roll.total <= 6
    
    def test_critical_doubles_dice(self):
        """Critical hit should double the number of dice."""
        for _ in range(10):
            roll = roll_damage("1d6", is_critical=True)
            # 2d6 = 2-12
            assert 2 <= roll.total <= 12
            assert len(roll.rolls) == 2
    
    def test_critical_preserves_modifier(self):
        """Critical should double dice but not modifier."""
        roll = roll_damage("1d6+2", is_critical=True)
        
        # Should be 2d6+2 (not 2d6+4)
        assert roll.modifier == 2
        assert roll.total >= 4  # 2 dice min 1 each + 2 mod
