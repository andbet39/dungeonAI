"""
Fight entity for DungeonAI combat system.
Tracks turn-based combat between players and monsters.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid


class FightStatus(Enum):
    """Status of a fight."""
    PENDING = "pending"      # Fight requested but not yet started
    ACTIVE = "active"        # Fight in progress
    ENDED = "ended"          # Fight concluded
    FLED = "fled"            # All players fled


@dataclass
class Fight:
    """
    Represents an active combat encounter.
    Multiple players can participate against a single monster.
    """
    id: str
    monster_id: str
    player_ids: list[str] = field(default_factory=list)
    turn_order: list[str] = field(default_factory=list)  # player_ids + monster_id
    current_turn_index: int = 0
    status: FightStatus = FightStatus.PENDING
    started_at: float = 0.0
    turn_end_time: float = 0.0
    turn_duration: int = 30  # 30 seconds per turn
    combat_log: list[dict] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        monster_id: str,
        initiator_player_id: str,
        turn_duration: int = 30
    ) -> "Fight":
        """Create a new fight encounter."""
        fight_id = str(uuid.uuid4())[:8]
        now = time.time()
        
        fight = cls(
            id=fight_id,
            monster_id=monster_id,
            player_ids=[initiator_player_id],
            turn_order=[initiator_player_id, monster_id],
            current_turn_index=0,
            status=FightStatus.ACTIVE,
            started_at=now,
            turn_end_time=now + turn_duration,
            turn_duration=turn_duration,
            combat_log=[]
        )
        
        fight.add_log_entry(
            "system",
            f"Combat initiated!"
        )
        
        return fight
    
    @property
    def current_turn_id(self) -> str:
        """Get the ID of who has the current turn (player_id or monster_id)."""
        if not self.turn_order:
            return ""
        return self.turn_order[self.current_turn_index % len(self.turn_order)]
    
    @property
    def is_monster_turn(self) -> bool:
        """Check if it's the monster's turn."""
        return self.current_turn_id == self.monster_id
    
    @property
    def is_active(self) -> bool:
        """Check if fight is currently active."""
        return self.status == FightStatus.ACTIVE
    
    @property
    def time_remaining(self) -> float:
        """Get remaining time in current turn (seconds)."""
        remaining = self.turn_end_time - time.time()
        return max(0, remaining)
    
    def add_player(self, player_id: str) -> bool:
        """Add a player to the fight. Returns True if added."""
        if player_id in self.player_ids:
            return False
        
        self.player_ids.append(player_id)
        # Insert before monster in turn order
        monster_index = self.turn_order.index(self.monster_id)
        self.turn_order.insert(monster_index, player_id)
        
        self.add_log_entry("system", f"A new ally joins the fight!")
        return True
    
    def remove_player(self, player_id: str) -> bool:
        """
        Remove a player from the fight (flee).
        Returns True if removed, False if player wasn't in fight.
        """
        if player_id not in self.player_ids:
            return False
        
        self.player_ids.remove(player_id)
        
        # Adjust turn order
        if player_id in self.turn_order:
            player_turn_index = self.turn_order.index(player_id)
            self.turn_order.remove(player_id)
            
            # Adjust current turn index if needed
            if player_turn_index < self.current_turn_index:
                self.current_turn_index -= 1
            elif player_turn_index == self.current_turn_index:
                # It was this player's turn, advance to next
                self.current_turn_index = self.current_turn_index % len(self.turn_order)
                self._reset_turn_timer()
        
        self.add_log_entry("system", f"A combatant has fled!")
        
        # Check if all players fled
        if not self.player_ids:
            self.status = FightStatus.FLED
            self.add_log_entry("system", "All players have fled. Combat ends.")
        
        return True
    
    def advance_turn(self) -> str:
        """
        Advance to the next turn.
        Returns the ID of who has the new turn.
        """
        if not self.turn_order:
            return ""
        
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        self._reset_turn_timer()
        
        return self.current_turn_id
    
    def _reset_turn_timer(self) -> None:
        """Reset the turn timer."""
        self.turn_end_time = time.time() + self.turn_duration
    
    def add_log_entry(self, entry_type: str, message: str, source_id: str = None) -> None:
        """Add an entry to the combat log."""
        self.combat_log.append({
            "type": entry_type,
            "message": message,
            "source_id": source_id,
            "timestamp": time.time()
        })
    
    def end_fight(self, result: str = "victory") -> None:
        """End the fight with a result."""
        self.status = FightStatus.ENDED
        self.add_log_entry("system", f"Combat ended: {result}")
    
    def to_dict(self) -> dict:
        """Serialize fight to dictionary for WebSocket transmission."""
        return {
            "id": self.id,
            "monster_id": self.monster_id,
            "player_ids": self.player_ids,
            "turn_order": self.turn_order,
            "current_turn_id": self.current_turn_id,
            "current_turn_index": self.current_turn_index,
            "is_monster_turn": self.is_monster_turn,
            "status": self.status.value,
            "started_at": self.started_at,
            "turn_end_time": self.turn_end_time,
            "turn_duration": self.turn_duration,
            "time_remaining": self.time_remaining,
            "combat_log": self.combat_log[-20:]  # Last 20 entries
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Fight":
        """Deserialize fight from dictionary."""
        fight = cls(
            id=data["id"],
            monster_id=data["monster_id"],
            player_ids=data.get("player_ids", []),
            turn_order=data.get("turn_order", []),
            current_turn_index=data.get("current_turn_index", 0),
            status=FightStatus(data.get("status", "active")),
            started_at=data.get("started_at", 0.0),
            turn_end_time=data.get("turn_end_time", 0.0),
            turn_duration=data.get("turn_duration", 30),
            combat_log=data.get("combat_log", [])
        )
        return fight
