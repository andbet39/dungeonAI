"""
Room entity for DungeonAI.
"""
from dataclasses import dataclass, field
from typing import Optional


# Room types for thematic furniture placement
ROOM_TYPES = [
    "chamber",
    "library", 
    "armory",
    "bedroom",
    "storage",
    "throne_room",
    "dining_hall",
    "crypt",
    "treasury",
    "dungeon_cell",
    "alchemy_lab",
    "guard_post"
]


@dataclass
class Room:
    """Represents a room in the dungeon."""
    id: str
    x: int  # top-left corner (floor area, not wall)
    y: int
    width: int
    height: int
    room_type: str = "chamber"
    name: str = ""
    description: str = ""
    furniture: list[tuple[int, int, int]] = field(default_factory=list)  # (x, y, tile_type)
    connected_rooms: list[str] = field(default_factory=list)
    visited: bool = False  # Track if room has been visited (for monster spawning)
    
    # Future expansion
    locked: bool = False
    required_key: Optional[str] = None
    trap_type: Optional[str] = None
    light_level: int = 100  # 0-100, for future lighting system
    
    @property
    def center_x(self) -> int:
        """Get center X coordinate."""
        return self.x + self.width // 2
    
    @property
    def center_y(self) -> int:
        """Get center Y coordinate."""
        return self.y + self.height // 2
    
    @property
    def center(self) -> tuple[int, int]:
        """Get center coordinates."""
        return (self.center_x, self.center_y)
    
    @property
    def area(self) -> int:
        """Get room area in tiles."""
        return self.width * self.height
    
    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Get room bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)
    
    def contains(self, px: int, py: int) -> bool:
        """Check if a point is inside this room."""
        return (self.x <= px < self.x + self.width and 
                self.y <= py < self.y + self.height)
    
    def to_dict(self) -> dict:
        """Serialize room to dictionary."""
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "room_type": self.room_type,
            "name": self.name,
            "description": self.description,
            "furniture": self.furniture,
            "connected_rooms": self.connected_rooms,
            "visited": self.visited,
            "locked": self.locked,
            "required_key": self.required_key,
            "trap_type": self.trap_type,
            "light_level": self.light_level,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        """Deserialize room from dictionary."""
        return cls(
            id=data["id"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            room_type=data.get("room_type", "chamber"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            furniture=data.get("furniture", []),
            connected_rooms=data.get("connected_rooms", []),
            visited=data.get("visited", False),
            locked=data.get("locked", False),
            required_key=data.get("required_key"),
            trap_type=data.get("trap_type"),
            light_level=data.get("light_level", 100),
        )
    
    def get_info(self) -> dict:
        """Get room info for sending to client."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.room_type,
            "description": self.description,
        }
