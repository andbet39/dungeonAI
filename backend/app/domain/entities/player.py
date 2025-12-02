"""
Player entity for DungeonAI.
"""
from dataclasses import dataclass, asdict
from typing import Optional
import time


@dataclass
class Player:
    """Represents a player in the game."""
    id: str
    x: int
    y: int
    symbol: str = "@"
    color: str = "#ff0"
    current_room_id: Optional[str] = None
    
    # Character name
    name: Optional[str] = None
    
    # Combat stats
    hp: int = 30
    max_hp: int = 30
    ac: int = 12  # Armor Class
    
    # D&D ability scores (default 10 = +0 modifier)
    str: int = 12  # Strength - melee attack/damage
    dex: int = 12  # Dexterity - ranged attack, AC
    con: int = 12  # Constitution - HP
    
    # Damage dice (e.g., "1d6" for sword)
    damage_dice: str = "1d6"
    
    # Defending status (bonus AC until next turn)
    is_defending: bool = False
    
    # Fight immunity timestamp - prevents immediate re-engagement after combat
    fight_immunity_until: float = 0.0
    
    def get_modifier(self, stat_value: int) -> int:
        """Calculate D&D ability modifier: (stat - 10) // 2"""
        return (stat_value - 10) // 2
    
    @property
    def str_mod(self) -> int:
        return self.get_modifier(self.str)
    
    @property
    def dex_mod(self) -> int:
        return self.get_modifier(self.dex)
    
    @property
    def con_mod(self) -> int:
        return self.get_modifier(self.con)
    
    @property
    def effective_ac(self) -> int:
        """AC with defending bonus."""
        return self.ac + (2 if self.is_defending else 0)
    
    @property
    def has_fight_immunity(self) -> bool:
        """Check if player is immune to being pulled into new fights."""
        return time.time() < self.fight_immunity_until
    
    def grant_fight_immunity(self, duration: float = 2.0) -> None:
        """Grant temporary immunity from being auto-engaged in combat."""
        self.fight_immunity_until = time.time() + duration
    
    def to_dict(self) -> dict:
        """Serialize player to dictionary."""
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "symbol": self.symbol,
            "color": self.color,
            "current_room_id": self.current_room_id,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "effective_ac": self.effective_ac,
            "str": self.str,
            "dex": self.dex,
            "con": self.con,
            "str_mod": self.str_mod,
            "dex_mod": self.dex_mod,
            "con_mod": self.con_mod,
            "damage_dice": self.damage_dice,
            "is_defending": self.is_defending,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Deserialize player from dictionary."""
        return cls(
            id=data["id"],
            x=data["x"],
            y=data["y"],
            symbol=data.get("symbol", "@"),
            color=data.get("color", "#ff0"),
            current_room_id=data.get("current_room_id"),
            name=data.get("name"),
            hp=data.get("hp", 30),
            max_hp=data.get("max_hp", 30),
            ac=data.get("ac", 12),
            str=data.get("str", 12),
            dex=data.get("dex", 12),
            con=data.get("con", 12),
            damage_dice=data.get("damage_dice", "1d6"),
            is_defending=data.get("is_defending", False),
        )
    
    def take_damage(self, amount: int) -> int:
        """Apply damage to player. Returns actual damage taken."""
        actual_damage = min(amount, self.hp)
        self.hp -= actual_damage
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Heal player. Returns actual amount healed."""
        actual_heal = min(amount, self.max_hp - self.hp)
        self.hp += actual_heal
        return actual_heal
    
    def respawn(self, x: int, y: int) -> None:
        """Respawn player at given position with full HP."""
        self.x = x
        self.y = y
        self.hp = self.max_hp
        self.is_defending = False
        self.current_room_id = None
    
    @property
    def is_alive(self) -> bool:
        """Check if player is alive."""
        return self.hp > 0
    
    @property
    def position(self) -> tuple[int, int]:
        """Get player position as tuple."""
        return (self.x, self.y)
