"""
A* Pathfinding and corridor detection for DungeonAI.

This module provides pathfinding utilities for monster movement AI:
- A* algorithm for finding optimal paths between positions
- Runtime corridor detection (floor tiles not inside any room)
- Direction calculation utilities

USAGE
-----
from app.domain.map.pathfinding import AStar, get_direction_to_target, is_corridor

astar = AStar(tiles, occupied_positions)
path = astar.find_path(start=(5, 5), goal=(10, 10))

if path:
    next_step = path[0]  # First step toward goal
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from .tiles import WALKABLE_TILES

if TYPE_CHECKING:
    from ..entities import Room


class Direction(IntEnum):
    """
    8 compass directions plus NONE for no threat visible.
    
    Used in state space to encode direction to nearest threat.
    Values 0-7 represent compass directions, 8 means no threat.
    """
    NORTH = 0       # (0, -1)
    NORTHEAST = 1   # (1, -1)
    EAST = 2        # (1, 0)
    SOUTHEAST = 3   # (1, 1)
    SOUTH = 4       # (0, 1)
    SOUTHWEST = 5   # (-1, 1)
    WEST = 6        # (-1, 0)
    NORTHWEST = 7   # (-1, -1)
    NONE = 8        # No threat visible

    @classmethod
    def from_delta(cls, dx: int, dy: int) -> "Direction":
        """
        Convert a delta (dx, dy) to a Direction.
        
        Args:
            dx: X delta (-1, 0, or 1)
            dy: Y delta (-1, 0, or 1)
        
        Returns:
            Direction enum value
        """
        if dx == 0 and dy == 0:
            return cls.NONE
        
        # Normalize to -1, 0, or 1
        dx = 0 if dx == 0 else (1 if dx > 0 else -1)
        dy = 0 if dy == 0 else (1 if dy > 0 else -1)
        
        direction_map = {
            (0, -1): cls.NORTH,
            (1, -1): cls.NORTHEAST,
            (1, 0): cls.EAST,
            (1, 1): cls.SOUTHEAST,
            (0, 1): cls.SOUTH,
            (-1, 1): cls.SOUTHWEST,
            (-1, 0): cls.WEST,
            (-1, -1): cls.NORTHWEST,
        }
        return direction_map.get((dx, dy), cls.NONE)

    def to_delta(self) -> Tuple[int, int]:
        """Convert Direction to (dx, dy) delta."""
        delta_map = {
            Direction.NORTH: (0, -1),
            Direction.NORTHEAST: (1, -1),
            Direction.EAST: (1, 0),
            Direction.SOUTHEAST: (1, 1),
            Direction.SOUTH: (0, 1),
            Direction.SOUTHWEST: (-1, 1),
            Direction.WEST: (-1, 0),
            Direction.NORTHWEST: (-1, -1),
            Direction.NONE: (0, 0),
        }
        return delta_map[self]

    def opposite(self) -> "Direction":
        """Get the opposite direction (for fleeing)."""
        if self == Direction.NONE:
            return Direction.NONE
        # Opposite is +4 mod 8
        return Direction((self.value + 4) % 8)


@dataclass
class AStarNode:
    """Node in A* search graph."""
    x: int
    y: int
    g: float = 0.0  # Cost from start
    h: float = 0.0  # Heuristic to goal
    parent: Optional["AStarNode"] = None

    @property
    def f(self) -> float:
        """Total estimated cost (g + h)."""
        return self.g + self.h

    def __lt__(self, other: "AStarNode") -> bool:
        """For heap comparison."""
        return self.f < other.f

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AStarNode):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


class AStar:
    """
    A* pathfinding algorithm for dungeon navigation.
    
    Uses Manhattan distance heuristic (appropriate for grid-based movement).
    Supports diagonal movement and respects occupied positions.
    
    Attributes:
        tiles: 2D tile array (tiles[y][x])
        occupied: Set of (x, y) positions blocked by entities
        width: Map width
        height: Map height
        allow_diagonal: Whether diagonal movement is allowed
    """

    def __init__(
        self,
        tiles: List[List[int]],
        occupied: Optional[Set[Tuple[int, int]]] = None,
        *,
        allow_diagonal: bool = True,
    ):
        self.tiles = tiles
        self.occupied = occupied or set()
        self.height = len(tiles)
        self.width = len(tiles[0]) if tiles else 0
        self.allow_diagonal = allow_diagonal

    def _heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """
        Manhattan distance heuristic.
        
        For diagonal movement, we could use Chebyshev distance,
        but Manhattan is admissible and works well for our needs.
        """
        return abs(x1 - x2) + abs(y1 - y2)

    def _is_walkable(self, x: int, y: int, *, ignore_occupied: bool = False) -> bool:
        """Check if a position is walkable."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        if self.tiles[y][x] not in WALKABLE_TILES:
            return False
        if not ignore_occupied and (x, y) in self.occupied:
            return False
        return True

    def _get_neighbors(self, node: AStarNode) -> List[Tuple[int, int, float]]:
        """
        Get walkable neighbors with movement costs.
        
        Returns list of (x, y, cost) tuples.
        Cardinal moves cost 1.0, diagonal moves cost 1.414.
        """
        neighbors = []
        # Cardinal directions
        cardinals = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        # Diagonal directions
        diagonals = [(-1, -1), (1, -1), (-1, 1), (1, 1)]

        for dx, dy in cardinals:
            nx, ny = node.x + dx, node.y + dy
            if self._is_walkable(nx, ny):
                neighbors.append((nx, ny, 1.0))

        if self.allow_diagonal:
            for dx, dy in diagonals:
                nx, ny = node.x + dx, node.y + dy
                if self._is_walkable(nx, ny):
                    # Check that we can actually move diagonally
                    # (both cardinal neighbors must be walkable to prevent corner cutting)
                    if self._is_walkable(node.x + dx, node.y) and self._is_walkable(node.x, node.y + dy):
                        neighbors.append((nx, ny, 1.414))

        return neighbors

    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        *,
        max_iterations: int = 1000,
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find shortest path from start to goal using A*.
        
        Args:
            start: Starting position (x, y)
            goal: Goal position (x, y)
            max_iterations: Maximum search iterations (prevents infinite loops)
        
        Returns:
            List of (x, y) positions from start to goal (excluding start),
            or None if no path exists.
        """
        start_x, start_y = start
        goal_x, goal_y = goal

        # Quick validity checks
        if not self._is_walkable(start_x, start_y, ignore_occupied=True):
            return None
        if not self._is_walkable(goal_x, goal_y, ignore_occupied=True):
            return None

        # Initialize
        start_node = AStarNode(
            x=start_x,
            y=start_y,
            g=0.0,
            h=self._heuristic(start_x, start_y, goal_x, goal_y),
        )

        open_set: List[AStarNode] = [start_node]
        heapq.heapify(open_set)
        
        # Track visited positions and their best g-scores
        g_scores: Dict[Tuple[int, int], float] = {(start_x, start_y): 0.0}
        closed_set: Set[Tuple[int, int]] = set()

        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)
            current_pos = (current.x, current.y)

            # Goal reached
            if current.x == goal_x and current.y == goal_y:
                return self._reconstruct_path(current)

            if current_pos in closed_set:
                continue
            closed_set.add(current_pos)

            for nx, ny, cost in self._get_neighbors(current):
                if (nx, ny) in closed_set:
                    continue

                tentative_g = current.g + cost

                # Skip if we've found a better path to this neighbor
                if (nx, ny) in g_scores and tentative_g >= g_scores[(nx, ny)]:
                    continue

                g_scores[(nx, ny)] = tentative_g
                neighbor = AStarNode(
                    x=nx,
                    y=ny,
                    g=tentative_g,
                    h=self._heuristic(nx, ny, goal_x, goal_y),
                    parent=current,
                )
                heapq.heappush(open_set, neighbor)

        return None  # No path found

    def _reconstruct_path(self, node: AStarNode) -> List[Tuple[int, int]]:
        """Reconstruct path from goal node back to start."""
        path = []
        current: Optional[AStarNode] = node
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        path.reverse()
        # Remove the starting position (monster is already there)
        return path[1:] if len(path) > 1 else []

    def find_flee_position(
        self,
        start: Tuple[int, int],
        threat: Tuple[int, int],
        *,
        search_radius: int = 5,
    ) -> Optional[Tuple[int, int]]:
        """
        Find the best position to flee from a threat.
        
        Searches positions within radius that maximize distance from threat.
        
        Args:
            start: Current position (x, y)
            threat: Threat position (x, y)
            search_radius: How far to search for flee positions
        
        Returns:
            Best flee position (x, y), or None if trapped.
        """
        start_x, start_y = start
        threat_x, threat_y = threat
        
        best_pos = None
        best_distance = 0
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                    
                nx, ny = start_x + dx, start_y + dy
                if not self._is_walkable(nx, ny):
                    continue
                
                # Calculate distance from threat
                dist = abs(nx - threat_x) + abs(ny - threat_y)
                
                # Prefer positions farther from threat
                if dist > best_distance:
                    # Verify we can actually reach this position
                    path = self.find_path(start, (nx, ny), max_iterations=100)
                    if path:
                        best_distance = dist
                        best_pos = (nx, ny)
        
        return best_pos


def get_direction_to_target(
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
) -> Direction:
    """
    Calculate compass direction from one point to another.
    
    Args:
        from_x, from_y: Source position
        to_x, to_y: Target position
    
    Returns:
        Direction enum indicating compass direction to target
    """
    dx = to_x - from_x
    dy = to_y - from_y
    return Direction.from_delta(dx, dy)


def get_corridor_positions(
    tiles: List[List[int]],
    rooms: List["Room"],
) -> Set[Tuple[int, int]]:
    """
    Detect corridor positions at runtime.
    
    Corridors are defined as walkable floor tiles that are not
    inside any room's bounds.
    
    Args:
        tiles: 2D tile array
        rooms: List of Room objects
    
    Returns:
        Set of (x, y) positions that are corridors
    """
    corridors: Set[Tuple[int, int]] = set()
    height = len(tiles)
    width = len(tiles[0]) if tiles else 0

    for y in range(height):
        for x in range(width):
            if tiles[y][x] not in WALKABLE_TILES:
                continue
            
            # Check if this position is inside any room
            in_room = False
            for room in rooms:
                if room.contains(x, y):
                    in_room = True
                    break
            
            if not in_room:
                corridors.add((x, y))

    return corridors


def is_in_corridor(
    x: int,
    y: int,
    tiles: List[List[int]],
    rooms: List["Room"],
) -> bool:
    """
    Check if a specific position is in a corridor.
    
    More efficient than get_corridor_positions for single checks.
    
    Args:
        x, y: Position to check
        tiles: 2D tile array
        rooms: List of Room objects
    
    Returns:
        True if position is a corridor tile
    """
    if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[0]):
        return False
    
    if tiles[y][x] not in WALKABLE_TILES:
        return False
    
    for room in rooms:
        if room.contains(x, y):
            return False
    
    return True


def find_nearest_corridor(
    x: int,
    y: int,
    tiles: List[List[int]],
    rooms: List["Room"],
    *,
    max_search: int = 10,
) -> Optional[Tuple[int, int]]:
    """
    Find the nearest corridor position from a given point.
    
    Uses BFS to find closest corridor for patrol waypoints.
    
    Args:
        x, y: Starting position
        tiles: 2D tile array
        rooms: List of Room objects
        max_search: Maximum search distance
    
    Returns:
        Nearest corridor position (x, y), or None if not found
    """
    from collections import deque
    
    height = len(tiles)
    width = len(tiles[0]) if tiles else 0
    
    visited: Set[Tuple[int, int]] = {(x, y)}
    queue = deque([(x, y, 0)])  # (x, y, distance)
    
    while queue:
        cx, cy, dist = queue.popleft()
        
        if dist > max_search:
            break
        
        if is_in_corridor(cx, cy, tiles, rooms):
            return (cx, cy)
        
        # Expand to neighbors
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in visited:
                continue
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            if tiles[ny][nx] not in WALKABLE_TILES:
                continue
            
            visited.add((nx, ny))
            queue.append((nx, ny, dist + 1))
    
    return None
