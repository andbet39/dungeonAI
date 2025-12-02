"""
Map generation and tile management.
"""
from .tiles import (
    TILE_FLOOR, TILE_WALL, TILE_DOOR_CLOSED, TILE_DOOR_OPEN,
    TILE_CHEST, TILE_TABLE, TILE_CHAIR, TILE_BED,
    TILE_BOOKSHELF, TILE_BARREL, TILE_TORCH, TILE_VOID,
    FURNITURE_TILES, TILE_TYPES, WALKABLE_TILES, is_walkable, is_door
)
from .dungeon import GeneratedMap
from .generator import generate_dungeon, DungeonGenerator
from .pathfinding import (
    Direction,
    AStar,
    get_direction_to_target,
    get_corridor_positions,
    is_in_corridor,
    find_nearest_corridor,
)

__all__ = [
    # Tile constants
    "TILE_FLOOR", "TILE_WALL", "TILE_DOOR_CLOSED", "TILE_DOOR_OPEN",
    "TILE_CHEST", "TILE_TABLE", "TILE_CHAIR", "TILE_BED",
    "TILE_BOOKSHELF", "TILE_BARREL", "TILE_TORCH", "TILE_VOID",
    "FURNITURE_TILES", "TILE_TYPES", "WALKABLE_TILES",
    # Tile utilities
    "is_walkable", "is_door",
    # Pathfinding
    "Direction",
    "AStar",
    "get_direction_to_target",
    "get_corridor_positions",
    "is_in_corridor",
    "find_nearest_corridor",
    # Map structures
    "GeneratedMap",
    # Generator
    "generate_dungeon", "DungeonGenerator",
]
