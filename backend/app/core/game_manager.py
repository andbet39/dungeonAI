"""
Central game state manager for DungeonAI multiplayer.
Orchestrates all game systems and manages WebSocket connections.
"""
import asyncio
import json
import time
import uuid
from typing import Optional
from fastapi import WebSocket

from ..config import settings
from ..domain import (
    Player, Monster, Room, Fight, FightStatus,
    TILE_FLOOR, TILE_WALL, TILE_DOOR_CLOSED, TILE_DOOR_OPEN,
    TILE_TYPES, generate_dungeon
)
from ..domain.combat import roll_attack, roll_damage, roll_d20
from ..domain.intelligence.learning import AIAction
from ..services import ai_service, storage_service, monster_service
from ..services.player_stats import get_xp_for_cr
from .events import event_bus, GameEvent, EventType


class GameManager:
    """
    Singleton class managing the game state and WebSocket connections.
    Handles player actions, state updates, and broadcasting to all clients.
    """
    _instance: Optional["GameManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self) -> None:
        """Async initialization - must be called after creating instance."""
        if self._initialized:
            return
        
        # Map state
        self.width = settings.game.default_map_width
        self.height = settings.game.default_map_height
        self.tiles: list[list[int]] = []
        self.rooms: list[Room] = []
        self.spawn_x = 1
        self.spawn_y = 1
        self.map_seed: Optional[int] = None
        
        # Entity state
        self.players: dict[str, Player] = {}
        self.monsters: dict[str, Monster] = {}
        
        # Combat state
        self.active_fights: dict[str, Fight] = {}
        
        # Connection state
        self.connections: dict[str, WebSocket] = {}
        
        # Internal state
        self._lock = asyncio.Lock()
        self._save_task: Optional[asyncio.Task] = None
        self._dirty = False
        
        # Try to load existing game, or generate new one
        loaded = await self._load_game()
        if not loaded:
            await self._generate_new_map()
        
        # Start periodic save task
        self._start_periodic_save()
        
        self._initialized = True
        print(f"[GameManager] Initialized with {len(self.rooms)} rooms, map size {self.width}x{self.height}")

    def _sync_initialize(self) -> None:
        """Synchronous fallback initialization for import time."""
        if self._initialized:
            return
        
        from ..domain.map import TILE_WALL
        
        self.width = settings.game.default_map_width
        self.height = settings.game.default_map_height
        self.tiles = [[TILE_WALL for _ in range(self.width)] for _ in range(self.height)]
        self.rooms = []
        self.players = {}
        self.monsters = {}
        self.active_fights = {}
        self.connections = {}
        self.spawn_x = 1
        self.spawn_y = 1
        self.map_seed = None
        self._lock = asyncio.Lock()
        self._save_task = None
        self._dirty = False

    # ============== State Loading/Saving ==============
    
    async def _load_game(self) -> bool:
        """Attempt to load game state from disk."""
        try:
            game_state = await storage_service.load_game()
            if not game_state:
                return False
            
            # Restore map data
            map_data = game_state.get("map", {})
            self.width = map_data.get("width", settings.game.default_map_width)
            self.height = map_data.get("height", settings.game.default_map_height)
            self.tiles = map_data.get("tiles", [])
            self.spawn_x = map_data.get("spawn_x", 1)
            self.spawn_y = map_data.get("spawn_y", 1)
            self.map_seed = map_data.get("seed")
            
            # Restore rooms
            rooms_data = game_state.get("rooms", [])
            self.rooms = [Room.from_dict(r) for r in rooms_data]
            
            # Restore monsters
            monsters_data = game_state.get("monsters", {})
            self.monsters = {
                mid: Monster.from_dict(mdata)
                for mid, mdata in monsters_data.items()
            }
            
            # Restore players (positions only, connections are not persistent)
            players_data = game_state.get("players", {})
            self.players = {
                pid: Player.from_dict(pdata) 
                for pid, pdata in players_data.items()
            }
            
            print(f"[GameManager] Loaded game with {len(self.rooms)} rooms")
            return True
            
        except Exception as e:
            print(f"[GameManager] Failed to load game: {e}")
            return False

    async def _generate_new_map(
        self, 
        width: int = None, 
        height: int = None, 
        room_count: int = None,
        seed: Optional[int] = None
    ) -> None:
        """Generate a new dungeon map with AI descriptions."""
        width = width or settings.game.default_map_width
        height = height or settings.game.default_map_height
        room_count = room_count or settings.game.default_room_count
        
        print(f"[GameManager] Generating new map {width}x{height} with ~{room_count} rooms...")
        
        # Generate dungeon structure
        generated = generate_dungeon(
            width=width,
            height=height,
            room_count=room_count,
            seed=seed
        )
        
        # Apply generated map
        self.width = generated.width
        self.height = generated.height
        self.tiles = generated.tiles
        self.spawn_x = generated.spawn_x
        self.spawn_y = generated.spawn_y
        self.map_seed = generated.seed
        
        # Convert rooms and generate AI descriptions
        room_dicts = [r.to_dict() for r in generated.rooms]
        room_dicts = await ai_service.generate_room_descriptions(room_dicts)
        self.rooms = [Room.from_dict(r) for r in room_dicts]
        
        # Clear players and monsters on new map
        self.players = {}
        self.monsters = {}
        
        # Save the new map
        await self._save_game("new_map_generated")
        
        # Emit event
        await event_bus.emit_async(GameEvent(
            type=EventType.MAP_REGENERATED,
            data={"width": self.width, "height": self.height, "room_count": len(self.rooms)}
        ))
        
        print(f"[GameManager] Generated map with {len(self.rooms)} rooms, seed={self.map_seed}")

    async def regenerate_map(
        self,
        width: int = None,
        height: int = None,
        room_count: int = None,
        seed: Optional[int] = None
    ) -> dict:
        """
        Regenerate the map (admin function).
        Disconnects all players and generates a fresh dungeon.
        """
        async with self._lock:
            # Notify all players that map is being regenerated
            await self._broadcast_message({
                "type": "map_regenerating",
                "message": "The dungeon is being regenerated..."
            })
            
            # Clear all connections
            old_player_count = len(self.players)
            self.players = {}
            self.monsters = {}
            self.connections = {}
            
            # Generate new map
            await self._generate_new_map(width, height, room_count, seed)
            
            return {
                "success": True,
                "width": self.width,
                "height": self.height,
                "room_count": len(self.rooms),
                "seed": self.map_seed,
                "players_disconnected": old_player_count
            }

    def _start_periodic_save(self) -> None:
        """Start the periodic save background task."""
        if self._save_task is not None:
            return
        
        async def periodic_save():
            while True:
                await asyncio.sleep(settings.game.autosave_interval)
                if self._dirty:
                    await self._save_game("periodic_backup")
                    self._dirty = False
        
        self._save_task = asyncio.create_task(periodic_save())

    async def _save_game(self, reason: str = "manual") -> None:
        """Save current game state to disk."""
        game_state = {
            "map": {
                "width": self.width,
                "height": self.height,
                "tiles": self.tiles,
                "spawn_x": self.spawn_x,
                "spawn_y": self.spawn_y,
                "seed": self.map_seed
            },
            "rooms": [r.to_dict() for r in self.rooms],
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "monsters": {mid: m.to_dict() for mid, m in self.monsters.items()}
        }
        
        await storage_service.save_game(game_state, reason=reason)

    def _mark_dirty(self) -> None:
        """Mark game state as needing save."""
        self._dirty = True

    async def force_save(self) -> bool:
        """Force an immediate save of the game state."""
        try:
            await self._save_game("manual_save")
            self._dirty = False
            return True
        except Exception as e:
            print(f"[GameManager] Force save failed: {e}")
            return False

    # ============== State Queries ==============

    def _find_room_at(self, x: int, y: int) -> Optional[Room]:
        """Find which room contains the given coordinates."""
        for room in self.rooms:
            if room.contains(x, y):
                return room
        return None

    def _find_spawn_position(self) -> tuple[int, int]:
        """Find an unoccupied floor tile for spawning a new player."""
        occupied = {(p.x, p.y) for p in self.players.values()}
        
        # Try spawn point first
        if (self.spawn_x, self.spawn_y) not in occupied:
            if self.tiles[self.spawn_y][self.spawn_x] == TILE_FLOOR:
                return self.spawn_x, self.spawn_y
        
        # Try tiles near spawn point
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x, y = self.spawn_x + dx, self.spawn_y + dy
                if 0 <= x < self.width and 0 <= y < self.height:
                    if self.tiles[y][x] == TILE_FLOOR and (x, y) not in occupied:
                        return x, y
        
        # Fallback: search all rooms for a floor tile
        for room in self.rooms:
            for ry in range(room.y, room.y + room.height):
                for rx in range(room.x, room.x + room.width):
                    if self.tiles[ry][rx] == TILE_FLOOR and (rx, ry) not in occupied:
                        return rx, ry
        
        return self.spawn_x, self.spawn_y

    def _is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        return tile == TILE_FLOOR or tile == TILE_DOOR_OPEN

    async def _respawn_player(self, player_id: str) -> None:
        """Respawn a defeated player at spawn point with full HP."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        spawn_x, spawn_y = self._find_spawn_position()
        player.respawn(spawn_x, spawn_y)
        
        # Update room reference
        new_room = self._find_room_at(spawn_x, spawn_y)
        player.current_room_id = new_room.id if new_room else None
        
        self._mark_dirty()
        print(f"[GameManager] Player {player_id} respawned at ({spawn_x}, {spawn_y}) with full HP")
        
        # Send respawn notification to the player
        if player_id in self.connections:
            try:
                import json
                message = json.dumps({
                    "type": "player_respawned",
                    "player_id": player_id,
                    "x": spawn_x,
                    "y": spawn_y,
                    "hp": player.hp,
                    "max_hp": player.max_hp
                })
                await self.connections[player_id].send_text(message)
            except Exception:
                pass

    def _is_occupied(self, x: int, y: int, exclude_player_id: Optional[str] = None) -> bool:
        """Check if a tile is occupied by another player or monster."""
        for player_id, player in self.players.items():
            if player_id != exclude_player_id and player.x == x and player.y == y:
                return True
        for monster in self.monsters.values():
            if monster.x == x and monster.y == y:
                return True
        return False

    def _get_adjacent_monster(self, player_id: str) -> Optional[Monster]:
        """Find a monster adjacent to the player (8 directions)."""
        if player_id not in self.players:
            return None
        
        player = self.players[player_id]
        directions = [
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1)
        ]
        
        for dx, dy in directions:
            x = player.x + dx
            y = player.y + dy
            
            for monster in self.monsters.values():
                if monster.x == x and monster.y == y:
                    return monster
        
        return None

    def _get_adjacent_players(self, monster_id: str) -> list[str]:
        """Find all players adjacent to a monster."""
        if monster_id not in self.monsters:
            return []
        
        monster = self.monsters[monster_id]
        adjacent_players = []
        
        directions = [
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1)
        ]
        
        for dx, dy in directions:
            x = monster.x + dx
            y = monster.y + dy
            
            for player_id, player in self.players.items():
                if player.x == x and player.y == y:
                    adjacent_players.append(player_id)
        
        return adjacent_players

    def _get_fight_for_player(self, player_id: str) -> Optional[Fight]:
        """Get the active fight a player is participating in."""
        for fight in self.active_fights.values():
            if player_id in fight.player_ids and fight.is_active:
                return fight
        return None

    def _get_fight_for_monster(self, monster_id: str) -> Optional[Fight]:
        """Get the active fight a monster is participating in."""
        for fight in self.active_fights.values():
            if fight.monster_id == monster_id and fight.is_active:
                return fight
        return None

    def _is_player_in_fight(self, player_id: str) -> bool:
        """Check if a player is currently in an active fight."""
        return self._get_fight_for_player(player_id) is not None

    def _is_monster_in_fight(self, monster_id: str) -> bool:
        """Check if a monster is currently in an active fight."""
        return self._get_fight_for_monster(monster_id) is not None

    @property
    def has_connections(self) -> bool:
        """Check if there are any active connections."""
        return bool(self.connections)

    # ============== State Serialization ==============

    def get_state(self) -> dict:
        """Get the current game state as a dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "monsters": {mid: m.to_dict() for mid, m in self.monsters.items()},
            "rooms": [r.to_dict() for r in self.rooms],
            "tileTypes": TILE_TYPES
        }
    
    def get_viewport_state(
        self, 
        player_id: str, 
        viewport_width: int = None, 
        viewport_height: int = None
    ) -> dict:
        """Get game state with tiles cropped to viewport around player."""
        viewport_width = viewport_width or settings.game.viewport_width
        viewport_height = viewport_height or settings.game.viewport_height
        
        player = self.players.get(player_id)
        if not player:
            return self.get_state()
        
        # Calculate viewport bounds centered on player
        half_w = viewport_width // 2
        half_h = viewport_height // 2
        
        cam_x = max(0, min(player.x - half_w, self.width - viewport_width))
        cam_y = max(0, min(player.y - half_h, self.height - viewport_height))
        
        actual_width = min(viewport_width, self.width - cam_x)
        actual_height = min(viewport_height, self.height - cam_y)
        
        # Extract visible tiles
        visible_tiles = []
        for y in range(cam_y, cam_y + actual_height):
            row = []
            for x in range(cam_x, cam_x + actual_width):
                if 0 <= y < self.height and 0 <= x < self.width:
                    row.append(self.tiles[y][x])
                else:
                    row.append(TILE_WALL)
            visible_tiles.append(row)
        
        # Adjust player positions relative to viewport
        viewport_players = {}
        for pid, p in self.players.items():
            rel_x = p.x - cam_x
            rel_y = p.y - cam_y
            if 0 <= rel_x < actual_width and 0 <= rel_y < actual_height:
                viewport_players[pid] = {
                    **p.to_dict(),
                    "x": rel_x,
                    "y": rel_y,
                    "world_x": p.x,
                    "world_y": p.y
                }
        
        # Adjust monster positions relative to viewport
        viewport_monsters = {}
        for mid, m in self.monsters.items():
            rel_x = m.x - cam_x
            rel_y = m.y - cam_y
            if 0 <= rel_x < actual_width and 0 <= rel_y < actual_height:
                viewport_monsters[mid] = {
                    **m.to_dict(),
                    "x": rel_x,
                    "y": rel_y,
                    "world_x": m.x,
                    "world_y": m.y
                }
        
        return {
            "width": actual_width,
            "height": actual_height,
            "viewport_x": cam_x,
            "viewport_y": cam_y,
            "map_width": self.width,
            "map_height": self.height,
            "tiles": visible_tiles,
            "players": viewport_players,
            "monsters": viewport_monsters,
            "rooms": [r.to_dict() for r in self.rooms],
            "tileTypes": TILE_TYPES
        }

    # ============== Player Management ==============

    async def add_player(self, websocket: WebSocket, existing_player_id: str = None) -> tuple[str, bool]:
        """
        Add a new player or reconnect an existing one.
        
        Returns:
            Tuple of (player_id, is_reconnection)
        """
        async with self._lock:
            # Check if we can reconnect to an existing player
            if existing_player_id and existing_player_id in self.players:
                player = self.players[existing_player_id]
                self.connections[existing_player_id] = websocket
                print(f"Player {existing_player_id} reconnected at ({player.x}, {player.y}). Total players: {len(self.players)}")
                return existing_player_id, True
            
            # Generate new player ID
            player_id = str(uuid.uuid4())[:8]
            x, y = self._find_spawn_position()

            colors = ["#ff0", "#0ff", "#f0f", "#0f0", "#f80", "#08f", "#f08", "#8f0"]
            color_index = len(self.players) % len(colors)

            initial_room = self._find_room_at(x, y)

            player = Player(
                id=player_id,
                x=x,
                y=y,
                color=colors[color_index],
                current_room_id=initial_room.id if initial_room else None
            )

            self.players[player_id] = player
            self.connections[player_id] = websocket
            
            self._mark_dirty()
            
            await event_bus.emit_async(GameEvent(
                type=EventType.PLAYER_JOINED,
                source_id=player_id,
                data={"x": x, "y": y}
            ))

            print(f"Player {player_id} joined at ({x}, {y}). Total players: {len(self.players)}")

            # Handle initial room visit (same as when moving into a new room)
            if initial_room and not initial_room.visited:
                initial_room.visited = True
                await self._spawn_monsters_in_room(initial_room)
                self._mark_dirty()
                # Emit room entered event for stats tracking
                await event_bus.emit_async(GameEvent(
                    type=EventType.PLAYER_ENTERED_ROOM,
                    source_id=player_id,
                    data={
                        "room_id": initial_room.id,
                        "first_visit": True,
                    },
                ))

            return player_id, False

    async def remove_player(self, player_id: str, permanent: bool = False) -> None:
        """
        Handle player disconnection.
        
        By default (permanent=False), keeps player data for potential reconnection.
        Set permanent=True to fully remove player from the game.
        """
        async with self._lock:
            if player_id in self.connections:
                del self.connections[player_id]
            
            if permanent and player_id in self.players:
                del self.players[player_id]
            
            self._mark_dirty()
            
            # Force save to persist player position
            await self._save_game("player_disconnected")
            
            await event_bus.emit_async(GameEvent(
                type=EventType.PLAYER_LEFT,
                source_id=player_id
            ))

            if permanent:
                print(f"Player {player_id} permanently removed. Total players: {len(self.players)}")
            else:
                print(f"Player {player_id} disconnected (can reconnect). Total players: {len(self.players)}")

    async def move_player(self, player_id: str, dx: int, dy: int) -> dict:
        """
        Attempt to move a player by dx, dy.
        Returns dict with success status and room_entered info if applicable.
        """
        async with self._lock:
            result = {"success": False, "room_entered": None}
            
            if player_id not in self.players:
                return result

            player = self.players[player_id]
            new_x = player.x + dx
            new_y = player.y + dy

            if not self._is_walkable(new_x, new_y):
                return result

            if self._is_occupied(new_x, new_y, exclude_player_id=player_id):
                return result

            player.x = new_x
            player.y = new_y
            result["success"] = True
            
            # Mark state as dirty so player position gets saved
            self._mark_dirty()
            
            # Check for room transition
            new_room = self._find_room_at(new_x, new_y)
            new_room_id = new_room.id if new_room else None
            
            if new_room_id != player.current_room_id:
                player.current_room_id = new_room_id
                if new_room:
                    if not new_room.visited:
                        new_room.visited = True
                        await self._spawn_monsters_in_room(new_room)
                        self._mark_dirty()
                    
                    result["room_entered"] = new_room.get_info()
                    
                    await event_bus.emit_async(GameEvent(
                        type=EventType.PLAYER_ENTERED_ROOM,
                        source_id=player_id,
                        data={"room_id": new_room.id}
                    ))

            return result

    async def interact(self, player_id: str) -> dict:
        """
        Handle player interaction.
        Priority: 1) Check for adjacent monsters (fight), 2) Toggle adjacent doors.
        Returns dict with action type and relevant data.
        """
        async with self._lock:
            if player_id not in self.players:
                return {"action": None}

            player = self.players[player_id]

            # Check if player is already in a fight
            if self._is_player_in_fight(player_id):
                return {"action": "already_in_fight"}

            # Priority 1: Check for adjacent monster to fight
            adjacent_monster = self._get_adjacent_monster(player_id)
            if adjacent_monster:
                # Check if monster is already in a fight
                existing_fight = self._get_fight_for_monster(adjacent_monster.id)
                if existing_fight:
                    # Can join existing fight
                    return {
                        "action": "can_join_fight",
                        "fight_id": existing_fight.id,
                        "fight": existing_fight.to_dict(),
                        "monster": adjacent_monster.to_dict()
                    }
                else:
                    # New fight request
                    return {
                        "action": "fight_request",
                        "monster": adjacent_monster.to_dict(),
                        "monster_id": adjacent_monster.id
                    }

            # Priority 2: Toggle adjacent doors
            directions = [
                (0, -1), (0, 1), (-1, 0), (1, 0),
                (-1, -1), (1, -1), (-1, 1), (1, 1)
            ]

            for dx, dy in directions:
                x = player.x + dx
                y = player.y + dy

                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    continue

                tile = self.tiles[y][x]

                if tile == TILE_DOOR_CLOSED:
                    self.tiles[y][x] = TILE_DOOR_OPEN
                    self._mark_dirty()
                    await self._save_game("door_opened")
                    await event_bus.emit_async(GameEvent(
                        type=EventType.DOOR_OPENED,
                        source_id=player_id,
                        data={"x": x, "y": y}
                    ))
                    print(f"Player {player_id} opened door at ({x}, {y})")
                    return {"action": "door_opened", "x": x, "y": y}
                elif tile == TILE_DOOR_OPEN:
                    self.tiles[y][x] = TILE_DOOR_CLOSED
                    self._mark_dirty()
                    await self._save_game("door_closed")
                    await event_bus.emit_async(GameEvent(
                        type=EventType.DOOR_CLOSED,
                        source_id=player_id,
                        data={"x": x, "y": y}
                    ))
                    print(f"Player {player_id} closed door at ({x}, {y})")
                    return {"action": "door_closed", "x": x, "y": y}

            return {"action": None}

    # ============== Monster Management ==============

    async def _spawn_monsters_in_room(self, room: Room) -> None:
        """Spawn monsters in a room on first visit."""
        occupied = {(p.x, p.y) for p in self.players.values()}
        occupied.update((m.x, m.y) for m in self.monsters.values())
        
        spawned = monster_service.spawn_monsters_in_room(
            room=room,
            tiles=self.tiles,
            occupied_positions=occupied,
            map_width=self.width,
            map_height=self.height
        )
        
        for monster in spawned:
            self.monsters[monster.id] = monster
            await event_bus.emit_async(GameEvent(
                type=EventType.MONSTER_SPAWNED,
                source_id=monster.id,
                data={"monster_type": monster.monster_type, "room_id": room.id}
            ))

    async def update_monsters(self, current_tick: int) -> bool:
        """Update all monster AI behaviors. Called by the game loop."""
        if not self.monsters:
            return False
        
        any_moved = False
        
        occupied = {(p.x, p.y) for p in self.players.values()}
        occupied.update((m.x, m.y) for m in self.monsters.values())
        
        # First, check for monsters that should initiate combat with adjacent players
        await self._check_monster_aggro()
        
        for monster in self.monsters.values():
            # Skip monsters already in combat
            if self._is_monster_in_fight(monster.id):
                continue
                
            room = next((r for r in self.rooms if r.id == monster.room_id), None)
            if not room:
                continue
            
            occupied.discard((monster.x, monster.y))
            
            world_state = self._build_monster_world_state(monster, room)

            moved = monster_service.update_monster(
                monster=monster,
                room_bounds=room.bounds,
                tiles=self.tiles,
                occupied_positions=occupied,
                current_tick=current_tick,
                world_state=world_state,
            )
            
            if moved:
                any_moved = True
            
            occupied.add((monster.x, monster.y))
        
        if any_moved:
            self._mark_dirty()
        
        return any_moved

    def _build_monster_world_state(self, monster: Monster, room: Optional[Room]) -> dict:
        nearby_players = self._players_within_radius(monster.x, monster.y, radius=6)
        distance_to_threat = min((dist for _, dist in nearby_players), default=8)
        nearby_allies = self._count_monsters_in_room(room.id if room else None, exclude_id=monster.id)
        return {
            "room_type": room.room_type if room else "chamber",
            "nearby_enemies": len(nearby_players),
            "nearby_allies": nearby_allies,
            "distance_to_threat": distance_to_threat,
        }

    def _players_within_radius(self, x: int, y: int, radius: int) -> list[tuple[str, int]]:
        results = []
        for player_id, player in self.players.items():
            dist = abs(player.x - x) + abs(player.y - y)
            if dist <= radius:
                results.append((player_id, dist))
        return results

    def _count_monsters_in_room(self, room_id: Optional[str], exclude_id: str) -> int:
        if not room_id:
            return 0
        return sum(1 for m in self.monsters.values() if m.room_id == room_id and m.id != exclude_id)

    async def _handle_monster_flee(self, fight: Fight, monster: Monster) -> None:
        fight.add_log_entry("enemy_flee", f"🏃 {monster.name} flees the battle!", source_id=monster.id)
        fight.end_fight("victory")
        fight_data = fight.to_dict()
        player_ids = list(fight.player_ids)
        # Half XP for fleeing monster
        xp_earned = get_xp_for_cr(monster.stats.challenge_rating) // 2
        if monster.id in self.monsters:
            del self.monsters[monster.id]
            self._mark_dirty()
        fight_id = fight.id
        if fight_id in self.active_fights:
            del self.active_fights[fight_id]
        await self._broadcast_fight_ended_to_players(fight_id, "victory", fight_data, player_ids, xp_earned, monster.monster_type)

    async def _check_monster_aggro(self) -> None:
        """Check if any monsters should initiate combat with adjacent players.
        
        Uses the AI decision engine to determine if a monster should attack,
        based on personality, Q-learning, and world state.
        """
        import time
        # Create a copy of monster IDs to iterate (since we may modify active_fights)
        monster_ids = list(self.monsters.keys())
        
        for monster_id in monster_ids:
            monster = self.monsters.get(monster_id)
            if not monster:
                continue
            
            # Skip if monster is already in a fight
            if self._is_monster_in_fight(monster_id):
                continue
            
            # Find adjacent players who aren't in a fight
            adjacent_players = self._get_adjacent_players(monster_id)
            
            if not adjacent_players:
                continue
            
            # Use AI to decide whether to attack
            room = next((r for r in self.rooms if r.id == monster.room_id), None)
            world_state = self._build_monster_world_state(monster, room)
            world_state["distance_to_threat"] = 1  # Adjacent
            
            action = monster_service.decide_combat_action(
                monster,
                current_tick=int(time.time()),
                world_state=world_state,
            )
            
            # Only initiate combat if AI chooses an attack action
            attack_actions = (AIAction.ATTACK_AGGRESSIVE, AIAction.ATTACK_DEFENSIVE, AIAction.AMBUSH)
            
            if action not in attack_actions:
                # Monster chooses not to attack (defending, patrolling, calling allies, etc.)
                print(f"[GameManager] Monster {monster.name} chose {action.name} instead of attacking")
                continue
            
            for player_id in adjacent_players:
                # Skip players already in combat
                if self._is_player_in_fight(player_id):
                    continue
                
                # Monster attacks this player!
                result = await self._monster_initiate_combat(monster_id, player_id)
                if result.get("success"):
                    print(f"[GameManager] Monster {monster.name} attacks player {player_id} ({action.name})!")
                    # Only attack one player per tick
                    break

    async def _monster_initiate_combat(self, monster_id: str, player_id: str) -> dict:
        """Monster initiates combat with a player (internal, no lock)."""
        if monster_id not in self.monsters:
            return {"success": False, "error": "Monster not found"}
        
        if player_id not in self.players:
            return {"success": False, "error": "Player not found"}
        
        monster = self.monsters[monster_id]
        fight = Fight.create(
            monster_id=monster_id,
            initiator_player_id=player_id,
            turn_duration=30
        )
        
        # Monster attacks first when it initiates
        fight.current_turn_index = fight.turn_order.index(monster_id)
        fight._reset_turn_timer()
        fight.add_log_entry("system", f"{monster.name} attacks!")
        
        self.active_fights[fight.id] = fight
        
        # Send monster_attacks message to the player
        await self.send_monster_attacks(fight, monster, player_id)
        
        return {
            "success": True,
            "fight": fight.to_dict(),
            "monster": monster.to_dict(),
            "attacked_player_id": player_id
        }

    async def process_monster_combat_turns(self) -> None:
        """
        Process monster turns in all active fights.
        Called by the game loop to handle monster attacks when it's their turn.
        """
        # Get list of fight IDs to avoid modifying dict during iteration
        fight_ids = list(self.active_fights.keys())
        
        for fight_id in fight_ids:
            fight = self.active_fights.get(fight_id)
            if not fight or not fight.is_active:
                continue
            
            # Only process if it's the monster's turn
            if not fight.is_monster_turn:
                continue
            
            monster = self.monsters.get(fight.monster_id)
            if not monster:
                continue
            
            # Get a target player (first player in the fight)
            if not fight.player_ids:
                continue
            
            target_player_id = fight.player_ids[0]
            player = self.players.get(target_player_id)
            if not player:
                continue
            
            # Process the monster's attack
            fight_active = await self._process_monster_turn(fight, monster, target_player_id)
            if not fight_active:
                continue
            
            # Check if any players died - save player IDs before removing them
            original_player_ids = list(fight.player_ids)
            dead_players = [pid for pid in fight.player_ids if not self.players.get(pid, Player("",0,0)).is_alive]
            
            if dead_players:
                for dead_pid in dead_players:
                    fight.add_log_entry("death", f"💀 A hero has fallen!")
                    fight.remove_player(dead_pid)
                    # Respawn the dead player
                    await self._respawn_player(dead_pid)
            
            # Check if all players dead/fled
            if not fight.player_ids:
                fight.end_fight("defeat")
                fight.add_log_entry("defeat", f"☠️ The party has been wiped out!")
                # Notify using original player IDs (before they were removed)
                await self._broadcast_fight_ended_to_players(fight_id, "defeat", fight.to_dict(), original_player_ids)
                del self.active_fights[fight_id]
                continue
            
            # Advance past monster's turn to next player
            fight.advance_turn()
            
            # Send updated fight state to all participants
            await self.send_fight_updated(fight, monster)

    async def process_turn_timeouts(self) -> None:
        """
        Check for player turn timeouts in active fights.
        When a player's turn times out, kill and remove them from the game.
        Called by the game loop.
        """
        # Get list of fight IDs to avoid modifying dict during iteration
        fight_ids = list(self.active_fights.keys())
        
        for fight_id in fight_ids:
            fight = self.active_fights.get(fight_id)
            if not fight or not fight.is_active:
                continue
            
            # Only check timeouts for player turns, not monster turns
            if fight.is_monster_turn:
                continue
            
            # Check if time has run out
            if fight.time_remaining > 0:
                continue
            
            # Player's turn has timed out!
            timed_out_player_id = fight.current_turn_id
            player = self.players.get(timed_out_player_id)
            
            if not player:
                # Player doesn't exist, just remove from fight and advance
                fight.remove_player(timed_out_player_id)
                continue
            
            print(f"[GameManager] Player {timed_out_player_id} timed out in fight {fight_id} - killing player")
            
            # Kill the player
            player.hp = 0
            fight.add_log_entry("timeout", f"⏱️ Time's up! A hero stood frozen in fear and was struck down!")
            fight.add_log_entry("death", f"💀 A hero has fallen due to inaction!")
            
            # Save original player IDs for broadcasting
            original_player_ids = list(fight.player_ids)
            
            # Remove from fight
            fight.remove_player(timed_out_player_id)
            
            # Respawn the player instead of removing them
            await self._respawn_player(timed_out_player_id)
            
            # Check if fight should end
            if not fight.player_ids:
                fight.end_fight("defeat")
                fight.add_log_entry("defeat", f"☠️ The party has been wiped out!")
                
                # Get monster for the fight data
                monster = self.monsters.get(fight.monster_id)
                
                # Notify all original players (including the one who timed out)
                await self._broadcast_fight_ended_to_players(fight_id, "defeat", fight.to_dict(), original_player_ids)
                
                # Clean up fight
                del self.active_fights[fight_id]
            else:
                # Fight continues, send updated state
                monster = self.monsters.get(fight.monster_id)
                if monster:
                    await self.send_fight_updated(fight, monster)
                    
                # Also notify the timed-out player that fight ended for them
                await self._broadcast_fight_ended_to_players(
                    fight_id, 
                    "timeout_death", 
                    fight.to_dict(), 
                    [timed_out_player_id]
                )

    # ============== Fight Management ==============

    async def start_fight(self, player_id: str, monster_id: str) -> dict:
        """
        Start a new fight between a player and a monster.
        Returns fight data or error.
        """
        async with self._lock:
            if player_id not in self.players:
                return {"success": False, "error": "Player not found"}
            
            if monster_id not in self.monsters:
                return {"success": False, "error": "Monster not found"}
            
            if self._is_player_in_fight(player_id):
                return {"success": False, "error": "Already in a fight"}
            
            if self._is_monster_in_fight(monster_id):
                return {"success": False, "error": "Monster already in combat"}
            
            monster = self.monsters[monster_id]
            fight = Fight.create(
                monster_id=monster_id,
                initiator_player_id=player_id,
                turn_duration=30  # 30 seconds
            )
            
            self.active_fights[fight.id] = fight
            
            await event_bus.emit_async(GameEvent(
                type=EventType.COMBAT_STARTED,
                source_id=player_id,
                target_id=monster_id,
                data={"fight_id": fight.id}
            ))
            
            print(f"[GameManager] Fight {fight.id} started: Player {player_id} vs {monster.name}")
            
            return {
                "success": True,
                "fight": fight.to_dict(),
                "monster": monster.to_dict(),
                "player_ids": fight.player_ids
            }

    async def join_fight(self, player_id: str, fight_id: str) -> dict:
        """
        Add a player to an existing fight.
        Returns updated fight data or error.
        """
        async with self._lock:
            if player_id not in self.players:
                return {"success": False, "error": "Player not found"}
            
            if fight_id not in self.active_fights:
                return {"success": False, "error": "Fight not found"}
            
            if self._is_player_in_fight(player_id):
                return {"success": False, "error": "Already in a fight"}
            
            fight = self.active_fights[fight_id]
            
            if not fight.is_active:
                return {"success": False, "error": "Fight is not active"}
            
            # Check if player is adjacent to the monster
            monster = self.monsters.get(fight.monster_id)
            if not monster:
                return {"success": False, "error": "Monster not found"}
            
            player = self.players[player_id]
            dx = abs(player.x - monster.x)
            dy = abs(player.y - monster.y)
            if dx > 1 or dy > 1:
                return {"success": False, "error": "Not adjacent to the monster"}
            
            if not fight.add_player(player_id):
                return {"success": False, "error": "Could not join fight"}
            
            print(f"[GameManager] Player {player_id} joined fight {fight_id}")
            
            return {
                "success": True,
                "fight": fight.to_dict(),
                "monster": monster.to_dict()
            }

    async def flee_fight(self, player_id: str, fight_id: str) -> dict:
        """
        Remove a player from a fight (flee).
        Returns result and updated fight state.
        """
        async with self._lock:
            if fight_id not in self.active_fights:
                return {"success": False, "error": "Fight not found"}
            
            fight = self.active_fights[fight_id]
            
            if player_id not in fight.player_ids:
                return {"success": False, "error": "Not in this fight"}
            
            fight.remove_player(player_id)
            
            print(f"[GameManager] Player {player_id} fled from fight {fight_id}")
            
            # Check if fight should end
            fight_ended = not fight.is_active
            
            if fight_ended:
                # Clean up fight
                del self.active_fights[fight_id]
                print(f"[GameManager] Fight {fight_id} ended - all players fled")
            
            return {
                "success": True,
                "fight_ended": fight_ended,
                "fight": fight.to_dict() if not fight_ended else None,
                "remaining_players": fight.player_ids if not fight_ended else []
            }

    async def process_combat_action(self, player_id: str, fight_id: str, action: str) -> dict:
        """
        Process a combat action from a player using D&D-style dice mechanics.
        Actions: attack, defend, item, flee
        """
        async with self._lock:
            if fight_id not in self.active_fights:
                return {"success": False, "error": "Fight not found"}
            
            fight = self.active_fights[fight_id]
            
            if player_id not in fight.player_ids:
                return {"success": False, "error": "Not in this fight"}
            
            if fight.current_turn_id != player_id:
                return {"success": False, "error": "Not your turn"}
            
            player = self.players.get(player_id)
            monster = self.monsters.get(fight.monster_id)
            
            if not player or not monster:
                return {"success": False, "error": "Combatant not found"}
            
            # Clear defending status at start of turn
            player.is_defending = False
            
            result_data = {"action": action}
            
            if action == "attack":
                # Player attacks monster
                result_data = await self._process_player_attack(player, monster, fight)
                
            elif action == "defend":
                # Player takes defensive stance (+2 AC until next turn)
                player.is_defending = True
                fight.add_log_entry(
                    "defend",
                    f"🛡️ You take a defensive stance! (+2 AC)",
                    source_id=player_id
                )
                result_data["defended"] = True
                
            elif action == "item":
                # Simple healing potion for now
                heal_roll = roll_d20(0)  # d20 as healing (simplified)
                heal_amount = min(heal_roll.rolls[0], player.max_hp - player.hp)
                if heal_amount > 0:
                    player.heal(heal_amount)
                    fight.add_log_entry(
                        "heal",
                        f"🧪 You drink a potion! Heal {heal_amount} HP (🎲 {heal_roll.rolls[0]})",
                        source_id=player_id
                    )
                else:
                    fight.add_log_entry(
                        "info",
                        f"🧪 You're already at full health!",
                        source_id=player_id
                    )
                result_data["healed"] = heal_amount
            
            # Check if monster is dead
            if not monster.is_alive:
                fight.end_fight("victory")
                fight.add_log_entry("victory", f"⚔️ {monster.name} has been defeated!")
                # Emit monster death event for AI learning
                await event_bus.emit_async(GameEvent(
                    type=EventType.MONSTER_DIED,
                    source_id=monster.id,
                    data={
                        "monster_type": monster.monster_type,
                        "fight_id": fight_id,
                        "reward": -100.0,
                        "ai_snapshot": {
                            "monster_type": monster.monster_type,
                            "state_index": monster.intelligence_state.last_state_index,
                            "action": monster.intelligence_state.last_action,
                            "hp_ratio": 0.0,
                            "world_state": monster.intelligence_state.last_world_state,
                        },
                    },
                ))
                # Remove monster from game
                del self.monsters[monster.id]
                del self.active_fights[fight_id]
                self._mark_dirty()
                return {
                    "success": True,
                    "fight_ended": True,
                    "result": "victory",
                    "fight": fight.to_dict()
                }
            
            # Advance to next turn (monster's turn)
            fight.advance_turn()
            
            # If it's now monster's turn, process monster attack
            if fight.is_monster_turn:
                await self._process_monster_turn(fight, monster, player_id)
                
                # Save player IDs before removing dead players
                original_player_ids = list(fight.player_ids)
                
                # Check if any players died
                dead_players = [pid for pid in fight.player_ids if not self.players.get(pid, Player("",0,0)).is_alive]
                
                if dead_players:
                    for dead_pid in dead_players:
                        fight.add_log_entry("death", f"💀 A hero has fallen!")
                        fight.remove_player(dead_pid)
                        # Respawn the dead player
                        await self._respawn_player(dead_pid)
                
                # Check if all players dead/fled
                if not fight.player_ids:
                    fight.end_fight("defeat")
                    fight.add_log_entry("defeat", f"☠️ The party has been wiped out!")
                    fight_data = fight.to_dict()
                    # Add original player IDs so broadcast knows who to send to
                    fight_data["player_ids"] = original_player_ids
                    del self.active_fights[fight_id]
                    return {
                        "success": True,
                        "fight_ended": True,
                        "result": "defeat",
                        "fight": fight_data
                    }
                
                # Advance past monster turn
                fight.advance_turn()
            
            return {
                "success": True,
                "fight": fight.to_dict(),
                "action": action
            }
    
    async def _process_player_attack(self, player: Player, monster: Monster, fight: Fight) -> dict:
        """Process a player's attack action with dice rolls."""
        # Calculate attack bonus (STR modifier for melee)
        attack_bonus = player.str_mod
        target_ac = monster.stats.ac
        
        # Roll to hit
        attack_roll, hit, is_critical = roll_attack(attack_bonus, target_ac)
        
        if is_critical:
            # Critical hit!
            damage_roll = roll_damage(player.damage_dice, is_critical=True)
            actual_damage = monster.take_damage(damage_roll.total)
            fight.add_log_entry(
                "critical",
                f"⚔️ CRITICAL HIT! Attack: 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac}",
                source_id=player.id
            )
            fight.add_log_entry(
                "damage",
                f"💥 Damage: 🎲{damage_roll} → {actual_damage} damage!",
                source_id=player.id
            )
            # Emit negative reward for monster taking damage
            await event_bus.emit_async(GameEvent(
                type=EventType.DAMAGE_DEALT,
                source_id=player.id,
                target_id=monster.id,
                data={
                    "damage": actual_damage,
                    "is_critical": True,
                    "reward": float(-actual_damage) * 2.0,
                    "ai_snapshot": {
                        "monster_type": monster.monster_type,
                        "state_index": monster.intelligence_state.last_state_index,
                        "action": monster.intelligence_state.last_action,
                        "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
                        "world_state": monster.intelligence_state.last_world_state,
                    },
                },
            ))
            return {"hit": True, "critical": True, "damage": actual_damage, "roll": attack_roll.to_dict()}
            
        elif hit:
            # Normal hit
            damage_roll = roll_damage(player.damage_dice, is_critical=False)
            actual_damage = monster.take_damage(damage_roll.total)
            fight.add_log_entry(
                "hit",
                f"⚔️ Attack: 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac} - HIT!",
                source_id=player.id
            )
            fight.add_log_entry(
                "damage",
                f"💥 Damage: 🎲{damage_roll} → {actual_damage} damage!",
                source_id=player.id
            )
            # Emit negative reward for monster taking damage
            await event_bus.emit_async(GameEvent(
                type=EventType.DAMAGE_DEALT,
                source_id=player.id,
                target_id=monster.id,
                data={
                    "damage": actual_damage,
                    "is_critical": False,
                    "reward": float(-actual_damage),
                    "ai_snapshot": {
                        "monster_type": monster.monster_type,
                        "state_index": monster.intelligence_state.last_state_index,
                        "action": monster.intelligence_state.last_action,
                        "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
                        "world_state": monster.intelligence_state.last_world_state,
                    },
                },
            ))
            return {"hit": True, "critical": False, "damage": actual_damage, "roll": attack_roll.to_dict()}
            
        else:
            # Miss
            fight.add_log_entry(
                "miss",
                f"⚔️ Attack: 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac} - MISS!",
                source_id=player.id
            )
            return {"hit": False, "critical": False, "damage": 0, "roll": attack_roll.to_dict()}
    
    async def _process_monster_turn(self, fight: Fight, monster: Monster, target_player_id: str) -> bool:
        """Process the monster's combat decision. Returns False if fight ended."""
        player = self.players.get(target_player_id)
        if not player:
            return False

        room = next((r for r in self.rooms if r.id == monster.room_id), None)
        world_state = self._build_monster_world_state(monster, room)
        world_state.update({
            "nearby_enemies": len(fight.player_ids),
            "distance_to_threat": 1,
        })
        action = monster_service.decide_combat_action(
            monster,
            current_tick=int(time.time()),
            world_state=world_state,
        )

        if action == AIAction.DEFEND:
            fight.add_log_entry(
                "enemy_defend",
                f"🛡️ {monster.name} braces for impact!",
                source_id=monster.id,
            )
            return True
        if action == AIAction.FLEE:
            await self._handle_monster_flee(fight, monster)
            return False
        if action == AIAction.CALL_ALLIES:
            fight.add_log_entry(
                "enemy_call",
                f"📣 {monster.name} calls for reinforcements!",
                source_id=monster.id,
            )

        attack_bonus = monster.stats.get_modifier(monster.stats.str)
        target_ac = player.effective_ac
        damage_modifier = 0
        advantage = False

        if action == AIAction.ATTACK_AGGRESSIVE:
            attack_bonus += 1
            damage_modifier += 1
        elif action == AIAction.ATTACK_DEFENSIVE:
            target_ac = max(5, target_ac - 1)
        elif action == AIAction.AMBUSH:
            advantage = True
            damage_modifier += 1

        primary_roll = roll_attack(attack_bonus, target_ac)
        attack_roll, hit, is_critical = primary_roll
        if advantage and not hit and not is_critical:
            reroll = roll_attack(attack_bonus, target_ac)
            if reroll[1] or reroll[2]:
                attack_roll, hit, is_critical = reroll

        monster_damage = f"1d{6 + int(monster.stats.challenge_rating * 2)}"

        if is_critical:
            damage_roll = roll_damage(monster_damage, is_critical=True)
            total_damage = max(1, damage_roll.total + damage_modifier)
            actual_damage = player.take_damage(total_damage)
            fight.add_log_entry(
                "enemy_critical",
                f"🐲 {monster.name} CRITICAL HIT! 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac}",
                source_id=monster.id,
            )
            fight.add_log_entry(
                "enemy_damage",
                f"💀 Takes 🎲{damage_roll} → {actual_damage} damage!",
                source_id=monster.id,
            )
            # Emit positive reward for monster dealing damage
            await event_bus.emit_async(GameEvent(
                type=EventType.DAMAGE_DEALT,
                source_id=monster.id,
                target_id=player.id,
                data={
                    "damage": actual_damage,
                    "is_critical": True,
                    "reward": float(actual_damage) * 2.0,
                    "ai_snapshot": {
                        "monster_type": monster.monster_type,
                        "state_index": monster.intelligence_state.last_state_index,
                        "action": monster.intelligence_state.last_action,
                        "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
                        "world_state": monster.intelligence_state.last_world_state,
                    },
                },
            ))
        elif hit:
            damage_roll = roll_damage(monster_damage, is_critical=False)
            total_damage = max(1, damage_roll.total + damage_modifier)
            actual_damage = player.take_damage(total_damage)
            fight.add_log_entry(
                "enemy_hit",
                f"🐲 {monster.name} strikes ({action.name.lower()})! 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac} - HIT!",
                source_id=monster.id,
            )
            fight.add_log_entry(
                "enemy_damage",
                f"💀 Takes 🎲{damage_roll} → {actual_damage} damage!",
                source_id=monster.id,
            )
            # Emit positive reward for monster dealing damage
            await event_bus.emit_async(GameEvent(
                type=EventType.DAMAGE_DEALT,
                source_id=monster.id,
                target_id=player.id,
                data={
                    "damage": actual_damage,
                    "is_critical": False,
                    "reward": float(actual_damage),
                    "ai_snapshot": {
                        "monster_type": monster.monster_type,
                        "state_index": monster.intelligence_state.last_state_index,
                        "action": monster.intelligence_state.last_action,
                        "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
                        "world_state": monster.intelligence_state.last_world_state,
                    },
                },
            ))
        else:
            fight.add_log_entry(
                "enemy_miss",
                f"🐲 {monster.name} ({action.name.lower()}) misses! 🎲{attack_roll.rolls[0]}+{attack_bonus}={attack_roll.total} vs AC {target_ac}",
                source_id=monster.id,
            )
            # Emit small negative reward for missing
            await event_bus.emit_async(GameEvent(
                type=EventType.DAMAGE_DEALT,
                source_id=monster.id,
                target_id=player.id,
                data={
                    "damage": 0,
                    "is_critical": False,
                    "reward": -1.0,
                    "ai_snapshot": {
                        "monster_type": monster.monster_type,
                        "state_index": monster.intelligence_state.last_state_index,
                        "action": monster.intelligence_state.last_action,
                        "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
                        "world_state": monster.intelligence_state.last_world_state,
                    },
                },
            ))

        return True

    async def monster_attack_player(self, monster_id: str, target_player_id: str) -> dict:
        """
        Monster initiates combat with a player.
        Creates fight immediately without popup confirmation.
        """
        async with self._lock:
            if monster_id not in self.monsters:
                return {"success": False, "error": "Monster not found"}
            
            if target_player_id not in self.players:
                return {"success": False, "error": "Player not found"}
            
            if self._is_monster_in_fight(monster_id):
                return {"success": False, "error": "Monster already in combat"}
            
            if self._is_player_in_fight(target_player_id):
                return {"success": False, "error": "Player already in combat"}
            
            monster = self.monsters[monster_id]
            fight = Fight.create(
                monster_id=monster_id,
                initiator_player_id=target_player_id,
                turn_duration=30
            )
            
            # Monster attacks first when it initiates
            fight.current_turn_index = fight.turn_order.index(monster_id)
            fight._reset_turn_timer()
            fight.add_log_entry("system", f"{monster.name} attacks!")
            
            self.active_fights[fight.id] = fight
            
            print(f"[GameManager] Monster {monster.name} attacks player {target_player_id}")
            
            return {
                "success": True,
                "fight": fight.to_dict(),
                "monster": monster.to_dict(),
                "attacked_player_id": target_player_id
            }

    async def get_nearby_fights(self, player_id: str) -> list[dict]:
        """
        Get fights happening near a player that they could join.
        """
        if player_id not in self.players:
            return []
        
        player = self.players[player_id]
        nearby_fights = []
        
        for fight in self.active_fights.values():
            if not fight.is_active:
                continue
            
            if player_id in fight.player_ids:
                continue
            
            monster = self.monsters.get(fight.monster_id)
            if not monster:
                continue
            
            # Check if player is adjacent to the monster
            dx = abs(player.x - monster.x)
            dy = abs(player.y - monster.y)
            if dx <= 1 and dy <= 1:
                nearby_fights.append({
                    "fight": fight.to_dict(),
                    "monster": monster.to_dict()
                })
        
        return nearby_fights

    # ============== Broadcasting ==============

    async def _broadcast_message(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.connections:
            return

        message_text = json.dumps(message)
        disconnected = []
        
        for player_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message_text)
            except Exception:
                disconnected.append(player_id)

        for player_id in disconnected:
            await self.remove_player(player_id)

    async def broadcast_state(self) -> None:
        """Broadcast the current game state to all connected clients."""
        if not self.connections:
            return

        disconnected = []
        for player_id, websocket in self.connections.items():
            try:
                state = self.get_viewport_state(player_id)
                message = json.dumps({
                    "type": "state_update",
                    "state": state
                })
                await websocket.send_text(message)
            except Exception:
                disconnected.append(player_id)

        for player_id in disconnected:
            await self.remove_player(player_id)

    async def send_welcome(self, player_id: str, is_reconnection: bool = False) -> None:
        """Send welcome message with full state to a specific player."""
        if player_id not in self.connections:
            return

        websocket = self.connections[player_id]
        state = self.get_viewport_state(player_id)
        
        player = self.players.get(player_id)
        room_info = None
        if player and player.current_room_id:
            room = next((r for r in self.rooms if r.id == player.current_room_id), None)
            if room:
                room_info = room.get_info()
        
        message = json.dumps({
            "type": "welcome",
            "playerId": player_id,
            "state": state,
            "currentRoom": room_info,
            "isReconnection": is_reconnection
        })

        await websocket.send_text(message)

    async def send_room_entered(self, player_id: str, room_info: dict) -> None:
        """Send room entered notification to a specific player."""
        if player_id not in self.connections:
            return

        websocket = self.connections[player_id]
        message = json.dumps({
            "type": "room_entered",
            "room": room_info
        })
        
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    async def broadcast_player_joined(self, player_id: str) -> None:
        """Notify all other players that someone joined."""
        if not self.connections:
            return

        message = json.dumps({
            "type": "player_joined",
            "playerId": player_id
        })

        for pid, websocket in self.connections.items():
            if pid != player_id:
                try:
                    await websocket.send_text(message)
                except Exception:
                    pass

    async def broadcast_player_left(self, player_id: str) -> None:
        """Notify all players that someone left."""
        if not self.connections:
            return

        message = json.dumps({
            "type": "player_left",
            "playerId": player_id
        })

        for websocket in self.connections.values():
            try:
                await websocket.send_text(message)
            except Exception:
                pass

    async def send_fight_started(self, fight: Fight, monster: Monster, to_player_ids: list[str]) -> None:
        """Send fight_started message to specific players."""
        message = json.dumps({
            "type": "fight_started",
            "fight": fight.to_dict(),
            "monster": monster.to_dict()
        })
        
        for player_id in to_player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                except Exception:
                    pass

    async def send_fight_updated(self, fight: Fight, monster: Monster) -> None:
        """Send fight update to all participants."""
        message = json.dumps({
            "type": "fight_updated",
            "fight": fight.to_dict(),
            "monster": monster.to_dict()
        })
        
        for player_id in fight.player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                except Exception:
                    pass

    async def send_player_fled(self, fight_id: str, fled_player_id: str, remaining_player_ids: list[str]) -> None:
        """Notify remaining players that someone fled."""
        message = json.dumps({
            "type": "player_fled",
            "fight_id": fight_id,
            "fled_player_id": fled_player_id
        })
        
        for player_id in remaining_player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                except Exception:
                    pass

    async def send_fight_ended(self, fight_id: str, result: str, to_player_ids: list[str]) -> None:
        """Notify players that a fight has ended."""
        message = json.dumps({
            "type": "fight_ended",
            "fight_id": fight_id,
            "result": result
        })
        
        for player_id in to_player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                except Exception:
                    pass
    
    async def broadcast_fight_ended(self, result: dict, fight_id: str) -> None:
        """Broadcast fight ended to all participants with full details."""
        # Get the fight data from the result
        fight_data = result.get("fight", {})
        player_ids = fight_data.get("player_ids", [])
        
        print(f"[GameManager] Broadcasting fight_ended: result={result.get('result')}, player_ids={player_ids}")
        
        message = json.dumps({
            "type": "fight_ended",
            "fight_id": fight_id,
            "result": result.get("result", "unknown"),
            "fight": fight_data
        })
        
        for player_id in player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                    print(f"[GameManager] Sent fight_ended to player {player_id}")
                except Exception as e:
                    print(f"[GameManager] Failed to send fight_ended to {player_id}: {e}")
        
        # Broadcast updated game state after a short delay to ensure fight_ended is processed first
        await self.broadcast_state()

    async def _broadcast_fight_ended_to_players(self, fight_id: str, result: str, fight_data: dict, player_ids: list[str], xp_earned: int = 0, monster_type: str = None) -> None:
        """Broadcast fight ended to specific players (used when players have been removed from fight)."""
        message = json.dumps({
            "type": "fight_ended",
            "fight_id": fight_id,
            "result": result,
            "fight": fight_data,
            "xp_earned": xp_earned,
            "monster_type": monster_type
        })
        
        for player_id in player_ids:
            if player_id in self.connections:
                try:
                    await self.connections[player_id].send_text(message)
                except Exception:
                    pass
        
        # Also broadcast updated game state
        await self.broadcast_state()

    async def send_monster_attacks(self, fight: Fight, monster: Monster, target_player_id: str) -> None:
        """Send immediate fight start when monster attacks."""
        message = json.dumps({
            "type": "monster_attacks",
            "fight": fight.to_dict(),
            "monster": monster.to_dict()
        })
        
        if target_player_id in self.connections:
            try:
                await self.connections[target_player_id].send_text(message)
            except Exception:
                pass


# Global game manager instance
game_manager = GameManager()
game_manager._sync_initialize()
