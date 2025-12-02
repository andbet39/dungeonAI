"""
Monster entity and related types for DungeonAI.
"""
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional


class MonsterBehavior(Enum):
    """Monster behavior types."""
    STATIC = "static"          # Stays in place
    PATROL = "patrol"          # Moves randomly within room
    SEARCHING = "searching"    # Moves toward last known player position
    AGGRESSIVE = "aggressive"  # Actively chases players
    FLEEING = "fleeing"        # Runs away when hurt
    AMBUSH = "ambush"          # Waits hidden, attacks when player is close
    WANDER = "wander"          # Moves aimlessly
    HAUNT = "haunt"            # Ghostly movement patterns
    RITUAL = "ritual"          # Stays in place performing rituals


@dataclass
class MonsterStats:
    """D&D-style monster statistics."""
    hp: int
    max_hp: int
    ac: int  # Armor Class
    str: int  # Strength
    dex: int  # Dexterity
    con: int  # Constitution
    int: int  # Intelligence
    wis: int  # Wisdom
    cha: int  # Charisma
    speed: int = 30
    challenge_rating: float = 0.25
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MonsterStats":
        return cls(
            hp=data.get("hp", 10),
            max_hp=data.get("max_hp", data.get("hp", 10)),
            ac=data.get("ac", 10),
            str=data.get("str", 10),
            dex=data.get("dex", 10),
            con=data.get("con", 10),
            int=data.get("int", 10),
            wis=data.get("wis", 10),
            cha=data.get("cha", 10),
            speed=data.get("speed", 30),
            challenge_rating=data.get("challenge_rating", 0.25)
        )
    
    def get_modifier(self, stat_value: int) -> int:
        """Calculate D&D ability modifier."""
        return (stat_value - 10) // 2

@dataclass
class MonsterIntelligenceState:
    """Serializable snapshot of per-monster AI state."""

    memory_events: list[dict] = field(default_factory=list)
    last_state_index: Optional[int] = None
    last_action: Optional[str] = None
    last_reward: float = 0.0
    last_decision_tick: int = 0
    generation: int = 0
    q_table_version: int = 0
    last_world_state: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "memory_events": self.memory_events,
            "last_state_index": self.last_state_index,
            "last_action": self.last_action,
            "last_reward": self.last_reward,
            "last_decision_tick": self.last_decision_tick,
            "generation": self.generation,
            "q_table_version": self.q_table_version,
            "last_world_state": self.last_world_state,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "MonsterIntelligenceState":
        if not data:
            return cls()
        return cls(
            memory_events=list(data.get("memory_events", [])),
            last_state_index=data.get("last_state_index"),
            last_action=data.get("last_action"),
            last_reward=float(data.get("last_reward", 0.0)),
            last_decision_tick=int(data.get("last_decision_tick", 0)),
            generation=int(data.get("generation", 0)),
            q_table_version=int(data.get("q_table_version", 0)),
            last_world_state=dict(data.get("last_world_state", {})),
        )


@dataclass
class Monster:
    """Represents a monster in the dungeon."""
    id: str
    monster_type: str
    name: str
    x: int
    y: int
    room_id: str
    symbol: str
    color: str
    stats: MonsterStats
    behavior: MonsterBehavior
    description: str = ""
    patrol_target: Optional[tuple[int, int]] = None
    last_move_tick: int = 0
    intelligence_state: MonsterIntelligenceState = field(default_factory=MonsterIntelligenceState)
    
    # Future expansion
    target_player_id: Optional[str] = None
    last_seen_player_pos: Optional[tuple[int, int]] = None
    
    def to_dict(self) -> dict:
        """Serialize monster to dictionary."""
        return {
            "id": self.id,
            "monster_type": self.monster_type,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "room_id": self.room_id,
            "symbol": self.symbol,
            "color": self.color,
            "stats": self.stats.to_dict(),
            "behavior": self.behavior.value,
            "description": self.description,
            "patrol_target": self.patrol_target,
            "last_move_tick": self.last_move_tick,
            "target_player_id": self.target_player_id,
            "last_seen_player_pos": self.last_seen_player_pos,
            "intelligence_state": self.intelligence_state.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Monster":
        """Deserialize monster from dictionary."""
        return cls(
            id=data["id"],
            monster_type=data["monster_type"],
            name=data["name"],
            x=data["x"],
            y=data["y"],
            room_id=data["room_id"],
            symbol=data["symbol"],
            color=data["color"],
            stats=MonsterStats.from_dict(data["stats"]),
            behavior=MonsterBehavior(data.get("behavior", "static")),
            description=data.get("description", ""),
            patrol_target=tuple(data["patrol_target"]) if data.get("patrol_target") else None,
            last_move_tick=data.get("last_move_tick", 0),
            target_player_id=data.get("target_player_id"),
            last_seen_player_pos=tuple(data["last_seen_player_pos"]) if data.get("last_seen_player_pos") else None,
            intelligence_state=MonsterIntelligenceState.from_dict(data.get("intelligence_state")),
        )
    
    def take_damage(self, amount: int) -> int:
        """Apply damage to monster. Returns actual damage taken."""
        actual_damage = min(amount, self.stats.hp)
        self.stats.hp -= actual_damage
        return actual_damage
    
    @property
    def is_alive(self) -> bool:
        """Check if monster is alive."""
        return self.stats.hp > 0
    
    @property
    def position(self) -> tuple[int, int]:
        """Get monster position as tuple."""
        return (self.x, self.y)
