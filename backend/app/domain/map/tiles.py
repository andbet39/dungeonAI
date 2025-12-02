"""
Tile type constants and utilities for DungeonAI.
"""

# Tile type constants
TILE_FLOOR = 0
TILE_WALL = 1
TILE_DOOR_CLOSED = 2
TILE_DOOR_OPEN = 3
TILE_CHEST = 4
TILE_TABLE = 5
TILE_CHAIR = 6
TILE_BED = 7
TILE_BOOKSHELF = 8
TILE_BARREL = 9
TILE_TORCH = 10
TILE_VOID = 11  # Empty black space (not walkable, not visible as wall)

# Furniture tile types for random placement
FURNITURE_TILES = [TILE_TABLE, TILE_CHAIR, TILE_BED, TILE_BOOKSHELF, TILE_BARREL]

# Tile type dictionary for client
TILE_TYPES = {
    "floor": TILE_FLOOR,
    "wall": TILE_WALL,
    "doorClosed": TILE_DOOR_CLOSED,
    "doorOpen": TILE_DOOR_OPEN,
    "chest": TILE_CHEST,
    "table": TILE_TABLE,
    "chair": TILE_CHAIR,
    "bed": TILE_BED,
    "bookshelf": TILE_BOOKSHELF,
    "barrel": TILE_BARREL,
    "torch": TILE_TORCH,
    "void": TILE_VOID,
}

# Walkable tiles
WALKABLE_TILES = {TILE_FLOOR, TILE_DOOR_OPEN}

# Door tiles
DOOR_TILES = {TILE_DOOR_CLOSED, TILE_DOOR_OPEN}

# Blocking tiles (for line of sight, etc.)
BLOCKING_TILES = {TILE_WALL, TILE_DOOR_CLOSED, TILE_VOID}


def is_walkable(tile: int) -> bool:
    """Check if a tile type is walkable."""
    return tile in WALKABLE_TILES


def is_door(tile: int) -> bool:
    """Check if a tile type is a door."""
    return tile in DOOR_TILES


def is_blocking(tile: int) -> bool:
    """Check if a tile type blocks movement and vision."""
    return tile in BLOCKING_TILES


def get_tile_name(tile: int) -> str:
    """Get human-readable name for a tile type."""
    for name, value in TILE_TYPES.items():
        if value == tile:
            return name
    return "unknown"
