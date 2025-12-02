"""
Procedural dungeon map generator using random room placement.
Generates rooms, corridors, doors, chests, and torches.

Rules:
- Rooms cannot be adjacent (minimum 5 tiles apart for corridors)
- Corridors are 1 tile wide
- Doors are placed on walls connecting to corridors
- All rooms are guaranteed to be reachable
"""
import random
from typing import Optional

from ..entities.room import Room, ROOM_TYPES
from .tiles import (
    TILE_FLOOR, TILE_WALL, TILE_DOOR_CLOSED, TILE_DOOR_OPEN,
    TILE_CHEST, TILE_TORCH, TILE_VOID
)
from .dungeon import GeneratedMap


class DungeonGenerator:
    """
    Generates procedural dungeons with:
    - Non-adjacent rooms (minimum gap for corridors)
    - 1-tile wide corridors
    - Doors on walls connecting to corridors
    - All rooms guaranteed to be reachable
    """
    
    MAX_SIZE = 5000
    CORRIDOR_WIDTH = 1
    MIN_ROOM_GAP = 10  # Minimum gap between rooms (for corridor + walls)
    
    def __init__(
        self,
        width: int = 100,
        height: int = 60,
        min_room_size: int = 8,
        max_room_size: int = 14,
        room_count: int = 20,
        seed: Optional[int] = None
    ):
        self.width = min(max(width, 40), self.MAX_SIZE)
        self.height = min(max(height, 30), self.MAX_SIZE)
        self.min_room_size = max(min_room_size, 6)
        self.max_room_size = min(max_room_size, 20)
        self.room_count = max(room_count, 10)
        self.seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        
        self.rng = random.Random(self.seed)
        self.tiles: list[list[int]] = []
        self.rooms: list[Room] = []
        self.room_id_counter = 0
        self.corridor_tiles: set[tuple[int, int]] = set()
        
    def generate(self) -> GeneratedMap:
        """Generate a complete dungeon map."""
        # Initialize all tiles as void
        self.tiles = [[TILE_VOID for _ in range(self.width)] for _ in range(self.height)]
        self.rooms = []
        self.room_id_counter = 0
        self.corridor_tiles = set()
        
        # Step 1: Place rooms with gaps (no adjacency)
        self._place_rooms()
        
        # Step 2: Connect rooms with 1-tile wide corridors
        self._connect_rooms()
        
        # Step 3: Add walls around all floor tiles
        self._add_walls()
        
        # Step 4: Place doors at corridor-room junctions
        self._place_doors()
        
        # Step 5: Verify all rooms are reachable
        self._ensure_all_rooms_connected()
        
        # Step 6: Place chests in some rooms
        self._place_chests()
        
        # Step 7: Place torches on walls
        self._place_torches()
        
        # Find spawn point
        spawn_x, spawn_y = self.rooms[0].center_x, self.rooms[0].center_y
        
        return GeneratedMap(
            width=self.width,
            height=self.height,
            tiles=self.tiles,
            rooms=self.rooms,
            spawn_x=spawn_x,
            spawn_y=spawn_y,
            seed=self.seed
        )
    
    def _place_rooms(self) -> None:
        """Place rooms ensuring they are not adjacent (minimum gap between them)."""
        attempts = 0
        max_attempts = self.room_count * 100
        
        while len(self.rooms) < self.room_count and attempts < max_attempts:
            attempts += 1
            
            # Generate random room dimensions
            room_width = self.rng.randint(self.min_room_size, self.max_room_size)
            room_height = self.rng.randint(self.min_room_size, self.max_room_size)
            
            # Random position (leaving margin for walls and corridors)
            margin = self.MIN_ROOM_GAP + 2
            max_x = self.width - room_width - margin
            max_y = self.height - room_height - margin
            
            if max_x <= margin or max_y <= margin:
                continue
                
            room_x = self.rng.randint(margin, max_x)
            room_y = self.rng.randint(margin, max_y)
            
            # Check if room overlaps or is too close to existing rooms
            if self._room_fits(room_x, room_y, room_width, room_height):
                self.room_id_counter += 1
                room_type = self.rng.choice(ROOM_TYPES)
                room = Room(
                    id=f"room_{self.room_id_counter}",
                    x=room_x,
                    y=room_y,
                    width=room_width,
                    height=room_height,
                    room_type=room_type,
                    name=self._generate_room_name(room_type)
                )
                
                # Carve floor tiles
                for y in range(room_y, room_y + room_height):
                    for x in range(room_x, room_x + room_width):
                        self.tiles[y][x] = TILE_FLOOR
                
                self.rooms.append(room)
    
    def _room_fits(self, x: int, y: int, w: int, h: int) -> bool:
        """Check if a room fits without being adjacent to other rooms."""
        check_x1 = x - self.MIN_ROOM_GAP
        check_y1 = y - self.MIN_ROOM_GAP
        check_x2 = x + w + self.MIN_ROOM_GAP
        check_y2 = y + h + self.MIN_ROOM_GAP
        
        for room in self.rooms:
            room_x2 = room.x + room.width
            room_y2 = room.y + room.height
            
            if not (check_x2 <= room.x or 
                    check_x1 >= room_x2 or
                    check_y2 <= room.y or 
                    check_y1 >= room_y2):
                return False
        return True
    
    def _connect_rooms(self) -> None:
        """Connect all rooms with corridors using MST approach."""
        if len(self.rooms) < 2:
            return
        
        connected = {0}
        unconnected = set(range(1, len(self.rooms)))
        
        while unconnected:
            best_dist = float('inf')
            best_pair = None
            
            for ci in connected:
                for ui in unconnected:
                    dist = self._room_distance(self.rooms[ci], self.rooms[ui])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (ci, ui)
            
            if best_pair:
                ci, ui = best_pair
                self._carve_corridor(self.rooms[ci], self.rooms[ui])
                self.rooms[ci].connected_rooms.append(self.rooms[ui].id)
                self.rooms[ui].connected_rooms.append(self.rooms[ci].id)
                connected.add(ui)
                unconnected.remove(ui)
    
    def _room_distance(self, room1: Room, room2: Room) -> float:
        """Calculate distance between room centers."""
        dx = room1.center_x - room2.center_x
        dy = room1.center_y - room2.center_y
        return (dx * dx + dy * dy) ** 0.5
    
    def _carve_corridor(self, room1: Room, room2: Room) -> None:
        """Carve a 1-tile wide L-shaped corridor between two rooms."""
        x1, y1 = room1.center_x, room1.center_y
        x2, y2 = room2.center_x, room2.center_y
        
        if self.rng.random() < 0.5:
            self._carve_h_corridor(x1, x2, y1)
            self._carve_v_corridor(y1, y2, x2)
        else:
            self._carve_v_corridor(y1, y2, x1)
            self._carve_h_corridor(x1, x2, y2)
    
    def _is_inside_room(self, x: int, y: int) -> bool:
        """Check if a position is inside any room's floor area."""
        for room in self.rooms:
            if room.x <= x < room.x + room.width and room.y <= y < room.y + room.height:
                return True
        return False
    
    def _is_adjacent_to_room_floor(self, x: int, y: int) -> bool:
        """Check if position is cardinally adjacent to any room floor tile."""
        for room in self.rooms:
            if x == room.x - 1 and room.y <= y < room.y + room.height:
                return True
            if x == room.x + room.width and room.y <= y < room.y + room.height:
                return True
            if y == room.y - 1 and room.x <= x < room.x + room.width:
                return True
            if y == room.y + room.height and room.x <= x < room.x + room.width:
                return True
        return False
    
    def _is_at_room_corner(self, x: int, y: int) -> bool:
        """Check if position is at or diagonally adjacent to any room corner."""
        for room in self.rooms:
            corners = [
                (room.x - 1, room.y - 1),
                (room.x + room.width, room.y - 1),
                (room.x - 1, room.y + room.height),
                (room.x + room.width, room.y + room.height),
            ]
            
            for cx, cy in corners:
                if abs(x - cx) <= 1 and abs(y - cy) <= 1:
                    return True
        return False
    
    def _carve_h_corridor(self, x1: int, x2: int, y: int) -> None:
        """Carve a horizontal corridor."""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                if (not self._is_inside_room(x, y) and 
                    not self._is_adjacent_to_room_floor(x, y) and
                    not self._is_at_room_corner(x, y)):
                    if self.tiles[y][x] == TILE_VOID:
                        self.tiles[y][x] = TILE_FLOOR
                        self.corridor_tiles.add((x, y))
    
    def _carve_v_corridor(self, y1: int, y2: int, x: int) -> None:
        """Carve a vertical corridor."""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                if (not self._is_inside_room(x, y) and 
                    not self._is_adjacent_to_room_floor(x, y) and
                    not self._is_at_room_corner(x, y)):
                    if self.tiles[y][x] == TILE_VOID:
                        self.tiles[y][x] = TILE_FLOOR
                        self.corridor_tiles.add((x, y))
    
    def _add_walls(self) -> None:
        """Add single-line walls around all floor tiles."""
        wall_positions = set()
        
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_FLOOR:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.tiles[ny][nx] == TILE_VOID:
                                    wall_positions.add((nx, ny))
        
        for x, y in wall_positions:
            self.tiles[y][x] = TILE_WALL
    
    def _is_corridor_floor(self, x: int, y: int) -> bool:
        """Check if a position is a corridor floor tile."""
        return (x, y) in self.corridor_tiles
    
    def _place_doors(self) -> None:
        """Place doors where corridors meet room walls."""
        for room in self.rooms:
            # Top wall
            wall_y = room.y - 1
            if wall_y >= 0:
                for x in range(room.x, room.x + room.width):
                    if self.tiles[wall_y][x] == TILE_WALL:
                        room_below = self.tiles[wall_y + 1][x] == TILE_FLOOR
                        corridor_above = wall_y > 0 and self._is_corridor_floor(x, wall_y - 1)
                        if room_below and corridor_above:
                            self.tiles[wall_y][x] = TILE_DOOR_CLOSED
            
            # Bottom wall
            wall_y = room.y + room.height
            if wall_y < self.height:
                for x in range(room.x, room.x + room.width):
                    if self.tiles[wall_y][x] == TILE_WALL:
                        room_above = self.tiles[wall_y - 1][x] == TILE_FLOOR
                        corridor_below = wall_y < self.height - 1 and self._is_corridor_floor(x, wall_y + 1)
                        if room_above and corridor_below:
                            self.tiles[wall_y][x] = TILE_DOOR_CLOSED
            
            # Left wall
            wall_x = room.x - 1
            if wall_x >= 0:
                for y in range(room.y, room.y + room.height):
                    if self.tiles[y][wall_x] == TILE_WALL:
                        room_right = self.tiles[y][wall_x + 1] == TILE_FLOOR
                        corridor_left = wall_x > 0 and self._is_corridor_floor(wall_x - 1, y)
                        if room_right and corridor_left:
                            self.tiles[y][wall_x] = TILE_DOOR_CLOSED
            
            # Right wall
            wall_x = room.x + room.width
            if wall_x < self.width:
                for y in range(room.y, room.y + room.height):
                    if self.tiles[y][wall_x] == TILE_WALL:
                        room_left = self.tiles[y][wall_x - 1] == TILE_FLOOR
                        corridor_right = wall_x < self.width - 1 and self._is_corridor_floor(wall_x + 1, y)
                        if room_left and corridor_right:
                            self.tiles[y][wall_x] = TILE_DOOR_CLOSED
    
    def _ensure_all_rooms_connected(self) -> None:
        """
        Verify all rooms are reachable using flood fill.
        If any room is unreachable, force a direct corridor connection.
        """
        if len(self.rooms) < 2:
            return
        
        # Use flood fill from spawn room to find all reachable tiles
        start_room = self.rooms[0]
        start_x, start_y = start_room.center_x, start_room.center_y
        
        reachable = self._flood_fill(start_x, start_y)
        
        # Check which rooms are reachable
        unreachable_rooms = []
        for room in self.rooms:
            room_center = (room.center_x, room.center_y)
            if room_center not in reachable:
                unreachable_rooms.append(room)
        
        # Force connect any unreachable rooms
        for unreachable_room in unreachable_rooms:
            # Find the nearest reachable room
            best_dist = float('inf')
            best_room = None
            
            for room in self.rooms:
                if room.id == unreachable_room.id:
                    continue
                if (room.center_x, room.center_y) in reachable:
                    dist = self._room_distance(room, unreachable_room)
                    if dist < best_dist:
                        best_dist = dist
                        best_room = room
            
            if best_room:
                # Force carve a direct corridor
                self._force_corridor(best_room, unreachable_room)
                
                # Update walls after new corridor
                self._add_walls()
                
                # Place door for the new connection
                self._place_room_doors(unreachable_room)
                
                # Update reachable set
                reachable = self._flood_fill(start_x, start_y)
    
    def _flood_fill(self, start_x: int, start_y: int) -> set[tuple[int, int]]:
        """Flood fill to find all walkable tiles reachable from a starting point."""
        reachable = set()
        walkable_tiles = {TILE_FLOOR, TILE_DOOR_CLOSED, TILE_DOOR_OPEN, TILE_CHEST, TILE_TORCH}
        
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in reachable:
                continue
            
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            
            if self.tiles[y][x] not in walkable_tiles:
                continue
            
            reachable.add((x, y))
            
            # Add cardinal neighbors
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        
        return reachable
    
    def _force_corridor(self, room1: Room, room2: Room) -> None:
        """
        Force carve a corridor between two rooms, ignoring adjacency checks.
        This ensures connectivity even if normal corridor placement failed.
        """
        x1, y1 = room1.center_x, room1.center_y
        x2, y2 = room2.center_x, room2.center_y
        
        # Horizontal then vertical
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y1 < self.height:
                if self.tiles[y1][x] in (TILE_VOID, TILE_WALL):
                    self.tiles[y1][x] = TILE_FLOOR
                    if not self._is_inside_room(x, y1):
                        self.corridor_tiles.add((x, y1))
        
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x2 < self.width and 0 <= y < self.height:
                if self.tiles[y][x2] in (TILE_VOID, TILE_WALL):
                    self.tiles[y][x2] = TILE_FLOOR
                    if not self._is_inside_room(x2, y):
                        self.corridor_tiles.add((x2, y))
    
    def _place_room_doors(self, room: Room) -> None:
        """Place doors for a specific room where corridors meet walls."""
        # Top wall
        wall_y = room.y - 1
        if wall_y >= 0:
            for x in range(room.x, room.x + room.width):
                if self.tiles[wall_y][x] == TILE_WALL:
                    room_below = self.tiles[wall_y + 1][x] == TILE_FLOOR
                    corridor_above = wall_y > 0 and self._is_corridor_floor(x, wall_y - 1)
                    if room_below and corridor_above:
                        self.tiles[wall_y][x] = TILE_DOOR_CLOSED
        
        # Bottom wall
        wall_y = room.y + room.height
        if wall_y < self.height:
            for x in range(room.x, room.x + room.width):
                if self.tiles[wall_y][x] == TILE_WALL:
                    room_above = self.tiles[wall_y - 1][x] == TILE_FLOOR
                    corridor_below = wall_y < self.height - 1 and self._is_corridor_floor(x, wall_y + 1)
                    if room_above and corridor_below:
                        self.tiles[wall_y][x] = TILE_DOOR_CLOSED
        
        # Left wall
        wall_x = room.x - 1
        if wall_x >= 0:
            for y in range(room.y, room.y + room.height):
                if self.tiles[y][wall_x] == TILE_WALL:
                    room_right = self.tiles[y][wall_x + 1] == TILE_FLOOR
                    corridor_left = wall_x > 0 and self._is_corridor_floor(wall_x - 1, y)
                    if room_right and corridor_left:
                        self.tiles[y][wall_x] = TILE_DOOR_CLOSED
        
        # Right wall
        wall_x = room.x + room.width
        if wall_x < self.width:
            for y in range(room.y, room.y + room.height):
                if self.tiles[y][wall_x] == TILE_WALL:
                    room_left = self.tiles[y][wall_x - 1] == TILE_FLOOR
                    corridor_right = wall_x < self.width - 1 and self._is_corridor_floor(wall_x + 1, y)
                    if room_left and corridor_right:
                        self.tiles[y][wall_x] = TILE_DOOR_CLOSED
    
    def _place_chests(self) -> None:
        """Place treasure chests in some rooms."""
        num_chests = max(1, len(self.rooms) // 4)
        rooms_with_chests = self.rng.sample(self.rooms, k=min(num_chests, len(self.rooms)))
        
        for room in rooms_with_chests:
            valid_positions = []
            for y in range(room.y + 1, room.y + room.height - 1):
                for x in range(room.x + 1, room.x + room.width - 1):
                    if self.tiles[y][x] == TILE_FLOOR:
                        valid_positions.append((x, y))
            
            if valid_positions:
                x, y = self.rng.choice(valid_positions)
                self.tiles[y][x] = TILE_CHEST
                room.furniture.append((x, y, TILE_CHEST))
    
    def _place_torches(self) -> None:
        """Place torches on walls for atmosphere (1 per room)."""
        for room in self.rooms:
            wall_positions = []
            
            for x in range(room.x, room.x + room.width):
                wy = room.y - 1
                if 0 <= wy < self.height and self.tiles[wy][x] == TILE_WALL:
                    wall_positions.append((x, wy))
                wy = room.y + room.height
                if 0 <= wy < self.height and self.tiles[wy][x] == TILE_WALL:
                    wall_positions.append((x, wy))
            
            for y in range(room.y, room.y + room.height):
                wx = room.x - 1
                if 0 <= wx < self.width and self.tiles[y][wx] == TILE_WALL:
                    wall_positions.append((wx, y))
                wx = room.x + room.width
                if 0 <= wx < self.width and self.tiles[y][wx] == TILE_WALL:
                    wall_positions.append((wx, y))
            
            if wall_positions:
                pos = self.rng.choice(wall_positions)
                x, y = pos
                self.tiles[y][x] = TILE_TORCH
    
    def _generate_room_name(self, room_type: str) -> str:
        """Generate a thematic name for a room."""
        prefixes = {
            "chamber": ["Ancient", "Dusty", "Forgotten", "Hidden", "Dark"],
            "library": ["Ruined", "Arcane", "Silent", "Forbidden", "Lost"],
            "armory": ["Old", "Royal", "Abandoned", "Guard's", "Knight's"],
            "bedroom": ["Noble's", "Servant's", "Guest", "Master", "Dusty"],
            "storage": ["Supply", "Old", "Forgotten", "Cluttered", "Dark"],
            "throne_room": ["Grand", "Fallen", "Ancient", "Cursed", "Royal"],
            "dining_hall": ["Great", "Abandoned", "Noble", "Feasting", "Old"],
            "crypt": ["Silent", "Haunted", "Ancient", "Forgotten", "Dark"],
            "treasury": ["Empty", "Looted", "Hidden", "Royal", "Forgotten"],
            "dungeon_cell": ["Dark", "Damp", "Forgotten", "Torture", "Prison"],
            "alchemy_lab": ["Abandoned", "Mysterious", "Arcane", "Ruined", "Secret"],
            "guard_post": ["Abandoned", "Old", "Watchtower", "Patrol", "Empty"]
        }
        
        type_names = {
            "chamber": "Chamber",
            "library": "Library",
            "armory": "Armory",
            "bedroom": "Bedroom",
            "storage": "Storage Room",
            "throne_room": "Throne Room",
            "dining_hall": "Dining Hall",
            "crypt": "Crypt",
            "treasury": "Treasury",
            "dungeon_cell": "Cell",
            "alchemy_lab": "Laboratory",
            "guard_post": "Guard Post"
        }
        
        prefix = self.rng.choice(prefixes.get(room_type, ["Mysterious"]))
        type_name = type_names.get(room_type, "Room")
        return f"{prefix} {type_name}"


def generate_dungeon(
    width: int = 200,
    height: int = 200,
    room_count: int = 30,
    seed: Optional[int] = None
) -> GeneratedMap:
    """
    Convenience function to generate a dungeon map.
    
    Args:
        width: Map width (max 1000)
        height: Map height (max 1000)
        room_count: Approximate number of rooms to generate
        seed: Random seed for reproducibility
    
    Returns:
        GeneratedMap containing tiles, rooms, and spawn point
    """
    generator = DungeonGenerator(
        width=width,
        height=height,
        room_count=room_count,
        seed=seed
    )
    return generator.generate()
