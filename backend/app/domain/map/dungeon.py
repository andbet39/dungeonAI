"""
Dungeon map data structures.
"""
from dataclasses import dataclass
from typing import Optional

from ..entities.room import Room


@dataclass
class GeneratedMap:
    """Result of map generation."""
    width: int
    height: int
    tiles: list[list[int]]
    rooms: list[Room]
    spawn_x: int
    spawn_y: int
    seed: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Serialize map to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "rooms": [r.to_dict() for r in self.rooms],
            "spawn_x": self.spawn_x,
            "spawn_y": self.spawn_y,
            "seed": self.seed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GeneratedMap":
        """Deserialize map from dictionary."""
        return cls(
            width=data["width"],
            height=data["height"],
            tiles=data["tiles"],
            rooms=[Room.from_dict(r) for r in data["rooms"]],
            spawn_x=data["spawn_x"],
            spawn_y=data["spawn_y"],
            seed=data.get("seed")
        )
    
    def get_tile(self, x: int, y: int) -> int:
        """Get tile at coordinates, returning TILE_VOID for out of bounds."""
        from .tiles import TILE_VOID
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return TILE_VOID
    
    def set_tile(self, x: int, y: int, tile: int) -> bool:
        """Set tile at coordinates. Returns True if successful."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile
            return True
        return False
    
    def find_room_at(self, x: int, y: int) -> Optional[Room]:
        """Find which room contains the given coordinates."""
        for room in self.rooms:
            if room.contains(x, y):
                return room
        return None
