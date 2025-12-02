"""
Game instance for DungeonAI multiplayer.
Each Game represents an independent dungeon session.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime
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
from ..services.ai_service import ai_service
from ..services.player_stats import get_xp_for_cr
from .events import event_bus, GameEvent, EventType

# Lazy import to avoid circular dependency
def _get_monster_service():
    from ..services.monster_service import monster_service
    return monster_service


class Game:
    """
    Game instance managing state and WebSocket connections for a single dungeon.
    Multiple Game instances can run concurrently.
    """
    
    def __init__(self, game_id: str, name: str):
        """Create a new game instance."""
        self.game_id = game_id
        self.name = name
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.completed_at: Optional[datetime] = None
        
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
        
        # Player token mapping (token -> player_id within this game)
        self.token_to_player: dict[str, str] = {}
        
        # Combat state
        self.active_fights: dict[str, Fight] = {}
        
        # Connection state
        self.connections: dict[str, WebSocket] = {}
        
        # Internal state
        self._lock = asyncio.Lock()
        self._game_loop_task: Optional[asyncio.Task] = None
        self._save_task: Optional[asyncio.Task] = None
        self._dirty = False
        self._initialized = False
    
    async def initialize(
        self, 
        load_save_id: Optional[str] = None,
        map_width: Optional[int] = None,
        map_height: Optional[int] = None,
        room_count: Optional[int] = None
    ) -> bool:
        """Async initialization - generates or loads map. Returns True if successful."""
        if self._initialized:
            return True
        
        # Try to load existing game if save_id provided
        if load_save_id:
            loaded = await self._load_game(load_save_id)
            if loaded:
                self._initialized = True
                self._start_game_loop()
                self._start_periodic_save()
                print(f"[Game:{self.game_id}] Loaded from save, {len(self.rooms)} rooms")
                return True
            else:
                # Failed to load, return False for restoration scenario
                return False
        
        # Generate new map with custom size if provided
        await self._generate_new_map(
            width=map_width,
            height=map_height,
            room_count=room_count
        )
        self._start_game_loop()
        self._start_periodic_save()
        self._initialized = True
        print(f"[Game:{self.game_id}] Initialized '{self.name}' with {len(self.rooms)} rooms")
        return True
    
    async def stop(self) -> None:
        """Stop the game and cleanup."""
        if self._game_loop_task:
            self._game_loop_task.cancel()
            try:
                await self._game_loop_task
            except asyncio.CancelledError:
                pass
            self._game_loop_task = None
        
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
            self._save_task = None
        
        # Final save
        await self._save_game("game_stopped")
        print(f"[Game:{self.game_id}] Stopped")
    
    def _start_game_loop(self) -> None:
        """Start the game loop for this instance."""
        if self._game_loop_task is not None:
            return
        
        async def game_loop():
            tick = 0
            while True:
                try:
                    await asyncio.sleep(settings.game.tick_interval)
                    tick += 1
                    
                    # Update monsters
                    state_changed = await self.update_monsters(tick)
                    
                    # Process monster combat turns
                    await self.process_monster_combat_turns()
                    
                    # Check turn timeouts
                    await self.process_turn_timeouts()
                    
                    # Broadcast if changed
                    if state_changed and self.has_connections:
                        await self.broadcast_state()
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[Game:{self.game_id}] Loop error: {e}")
        
        self._game_loop_task = asyncio.create_task(game_loop())
    
    def _start_periodic_save(self) -> None:
        """Start periodic save task."""
        if self._save_task is not None:
            return
        
        async def periodic_save():
            while True:
                await asyncio.sleep(settings.game.autosave_interval)
                if self._dirty:
                    await self._save_game("periodic")
                    self._dirty = False
        
        self._save_task = asyncio.create_task(periodic_save())
    
    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    # ============== Completion Check ==============
    
    @property
    def is_completed(self) -> bool:
        """Check if game is completed (all rooms visited, no monsters)."""
        if self.completed_at:
            return True
        
        all_visited = all(room.visited for room in self.rooms)
        no_monsters = len(self.monsters) == 0
        
        if all_visited and no_monsters and self.rooms:
            self.completed_at = datetime.now()
            return True
        return False
    
    @property
    def player_count(self) -> int:
        """Get number of players in this game."""
        return len(self.players)
    
    @property
    def active_player_count(self) -> int:
        """Get number of currently connected players."""
        return len(self.connections)
    
    @property
    def has_connections(self) -> bool:
        """Check if there are active connections."""
        return bool(self.connections)

    # ============== State Loading/Saving ==============
    
    async def _load_game(self, save_id: str) -> bool:
        """Load game state from disk."""
        from ..services import storage_service
        try:
            game_state = await storage_service.load_game_by_id(save_id)
            if not game_state:
                return False
            
            # Restore metadata
            self.name = game_state.get("name", self.name)
            
            map_data = game_state.get("map", {})
            self.width = map_data.get("width", settings.game.default_map_width)
            self.height = map_data.get("height", settings.game.default_map_height)
            self.tiles = map_data.get("tiles", [])
            self.spawn_x = map_data.get("spawn_x", 1)
            self.spawn_y = map_data.get("spawn_y", 1)
            self.map_seed = map_data.get("seed")
            
            self.rooms = [Room.from_dict(r) for r in game_state.get("rooms", [])]
            self.monsters = {mid: Monster.from_dict(m) for mid, m in game_state.get("monsters", {}).items()}
            self.players = {pid: Player.from_dict(p) for pid, p in game_state.get("players", {}).items()}
            self.token_to_player = game_state.get("token_to_player", {})
            
            return True
        except Exception as e:
            print(f"[Game:{self.game_id}] Load failed: {e}")
            return False

    async def _generate_new_map(
        self, 
        width: int = None, 
        height: int = None, 
        room_count: int = None,
        seed: Optional[int] = None
    ) -> None:
        """Generate a new dungeon map."""
        width = width or settings.game.default_map_width
        height = height or settings.game.default_map_height
        room_count = room_count or settings.game.default_room_count
        
        generated = generate_dungeon(width=width, height=height, room_count=room_count, seed=seed)
        
        self.width = generated.width
        self.height = generated.height
        self.tiles = generated.tiles
        self.spawn_x = generated.spawn_x
        self.spawn_y = generated.spawn_y
        self.map_seed = generated.seed
        
        room_dicts = [r.to_dict() for r in generated.rooms]
        room_dicts = await ai_service.generate_room_descriptions(room_dicts)
        self.rooms = [Room.from_dict(r) for r in room_dicts]
        
        self.players = {}
        self.monsters = {}
        
        await self._save_game("new_map")

    async def regenerate_map(self, width: int = None, height: int = None, room_count: int = None, seed: Optional[int] = None) -> dict:
        """Regenerate the map (admin function)."""
        async with self._lock:
            await self._broadcast_message({"type": "map_regenerating", "message": "Regenerating dungeon..."})
            
            old_count = len(self.players)
            self.players = {}
            self.monsters = {}
            self.connections = {}
            self.token_to_player = {}
            self.completed_at = None
            
            await self._generate_new_map(width, height, room_count, seed)
            
            return {"success": True, "width": self.width, "height": self.height, "room_count": len(self.rooms), "seed": self.map_seed, "players_disconnected": old_count}

    async def _save_game(self, reason: str = "manual") -> None:
        """Save game state to disk."""
        from ..services import storage_service
        game_state = {
            "game_id": self.game_id,
            "name": self.name,
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
            "monsters": {mid: m.to_dict() for mid, m in self.monsters.items()},
            "token_to_player": self.token_to_player
        }
        await storage_service.save_game_by_id(self.game_id, game_state, reason=reason)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_activity()

    async def force_save(self) -> bool:
        try:
            await self._save_game("manual_save")
            self._dirty = False
            return True
        except Exception as e:
            print(f"[Game:{self.game_id}] Save failed: {e}")
            return False

    # ============== State Queries ==============

    def _find_room_at(self, x: int, y: int) -> Optional[Room]:
        for room in self.rooms:
            if room.contains(x, y):
                return room
        return None

    def _find_spawn_position(self) -> tuple[int, int]:
        occupied = {(p.x, p.y) for p in self.players.values()}
        
        if (self.spawn_x, self.spawn_y) not in occupied:
            if self.tiles[self.spawn_y][self.spawn_x] == TILE_FLOOR:
                return self.spawn_x, self.spawn_y
        
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x, y = self.spawn_x + dx, self.spawn_y + dy
                if 0 <= x < self.width and 0 <= y < self.height:
                    if self.tiles[y][x] == TILE_FLOOR and (x, y) not in occupied:
                        return x, y
        
        for room in self.rooms:
            for ry in range(room.y, room.y + room.height):
                for rx in range(room.x, room.x + room.width):
                    if self.tiles[ry][rx] == TILE_FLOOR and (rx, ry) not in occupied:
                        return rx, ry
        
        return self.spawn_x, self.spawn_y

    def _is_walkable(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        return tile == TILE_FLOOR or tile == TILE_DOOR_OPEN

    def _is_occupied(self, x: int, y: int, exclude_player_id: Optional[str] = None) -> bool:
        for pid, p in self.players.items():
            if pid != exclude_player_id and p.x == x and p.y == y:
                return True
        for m in self.monsters.values():
            if m.x == x and m.y == y:
                return True
        return False

    def _get_adjacent_monster(self, player_id: str) -> Optional[Monster]:
        if player_id not in self.players:
            return None
        player = self.players[player_id]
        directions = [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]
        for dx, dy in directions:
            for m in self.monsters.values():
                if m.x == player.x + dx and m.y == player.y + dy:
                    return m
        return None

    def _get_adjacent_players(self, monster_id: str) -> list[str]:
        if monster_id not in self.monsters:
            return []
        monster = self.monsters[monster_id]
        result = []
        directions = [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]
        for dx, dy in directions:
            for pid, p in self.players.items():
                if p.x == monster.x + dx and p.y == monster.y + dy:
                    result.append(pid)
        return result

    def _get_fight_for_player(self, player_id: str) -> Optional[Fight]:
        for f in self.active_fights.values():
            if player_id in f.player_ids and f.is_active:
                return f
        return None

    def _get_fight_for_monster(self, monster_id: str) -> Optional[Fight]:
        for f in self.active_fights.values():
            if f.monster_id == monster_id and f.is_active:
                return f
        return None

    def _build_ai_snapshot(self, monster: Monster) -> dict:
        """
        Build AI snapshot for Q-learning from monster's intelligence state.
        
        This snapshot captures the state-action pair that led to the current
        outcome, enabling the Q-learning algorithm to apply rewards correctly.
        """
        intel = monster.intelligence_state
        if not intel or intel.last_state_index is None:
            return {}
        return {
            "monster_type": monster.monster_type,
            "state_index": intel.last_state_index,
            "action": intel.last_action,
            "world_state": intel.last_world_state,
            "hp_ratio": monster.stats.hp / max(1, monster.stats.max_hp),
        }

    def _is_player_in_fight(self, player_id: str) -> bool:
        return self._get_fight_for_player(player_id) is not None

    def _is_monster_in_fight(self, monster_id: str) -> bool:
        return self._get_fight_for_monster(monster_id) is not None
    
    def _get_token_for_player(self, player_id: str) -> Optional[str]:
        """Get the player token for a given player_id."""
        for token, pid in self.token_to_player.items():
            if pid == player_id:
                return token
        return None

    # ============== State Serialization ==============

    def get_state(self) -> dict:
        return {
            "game_id": self.game_id,
            "game_name": self.name,
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "monsters": {mid: m.to_dict() for mid, m in self.monsters.items()},
            "rooms": [r.to_dict() for r in self.rooms],
            "tileTypes": TILE_TYPES,
            "is_completed": self.is_completed
        }
    
    def get_viewport_state(self, player_id: str, viewport_width: int = None, viewport_height: int = None) -> dict:
        viewport_width = viewport_width or settings.game.viewport_width
        viewport_height = viewport_height or settings.game.viewport_height
        
        player = self.players.get(player_id)
        if not player:
            return self.get_state()
        
        half_w, half_h = viewport_width // 2, viewport_height // 2
        cam_x = max(0, min(player.x - half_w, self.width - viewport_width))
        cam_y = max(0, min(player.y - half_h, self.height - viewport_height))
        actual_w = min(viewport_width, self.width - cam_x)
        actual_h = min(viewport_height, self.height - cam_y)
        
        visible_tiles = []
        for y in range(cam_y, cam_y + actual_h):
            row = [self.tiles[y][x] if 0 <= x < self.width else TILE_WALL for x in range(cam_x, cam_x + actual_w)]
            visible_tiles.append(row)
        
        viewport_players = {}
        for pid, p in self.players.items():
            rx, ry = p.x - cam_x, p.y - cam_y
            if 0 <= rx < actual_w and 0 <= ry < actual_h:
                viewport_players[pid] = {**p.to_dict(), "x": rx, "y": ry, "world_x": p.x, "world_y": p.y}
        
        viewport_monsters = {}
        for mid, m in self.monsters.items():
            rx, ry = m.x - cam_x, m.y - cam_y
            if 0 <= rx < actual_w and 0 <= ry < actual_h:
                viewport_monsters[mid] = {**m.to_dict(), "x": rx, "y": ry, "world_x": m.x, "world_y": m.y}
        
        return {
            "game_id": self.game_id,
            "game_name": self.name,
            "width": actual_w,
            "height": actual_h,
            "viewport_x": cam_x,
            "viewport_y": cam_y,
            "map_width": self.width,
            "map_height": self.height,
            "tiles": visible_tiles,
            "players": viewport_players,
            "monsters": viewport_monsters,
            "rooms": [r.to_dict() for r in self.rooms],
            "tileTypes": TILE_TYPES,
            "is_completed": self.is_completed
        }

    # ============== Player Management ==============

    async def add_player(self, websocket: WebSocket, player_token: str, existing_player_id: str = None) -> tuple[str, bool]:
        """Add or reconnect a player using their token."""
        async with self._lock:
            self._update_activity()
            
            # Check token mapping for reconnection
            if player_token in self.token_to_player:
                pid = self.token_to_player[player_token]
                if pid in self.players:
                    self.connections[pid] = websocket
                    print(f"[Game:{self.game_id}] Player {pid} reconnected via token")
                    return pid, True
            
            # Check existing_player_id for reconnection
            if existing_player_id and existing_player_id in self.players:
                self.connections[existing_player_id] = websocket
                self.token_to_player[player_token] = existing_player_id
                print(f"[Game:{self.game_id}] Player {existing_player_id} reconnected")
                return existing_player_id, True
            
            # New player
            player_id = str(uuid.uuid4())[:8]
            x, y = self._find_spawn_position()
            colors = ["#ff0", "#0ff", "#f0f", "#0f0", "#f80", "#08f", "#f08", "#8f0"]
            color = colors[len(self.players) % len(colors)]
            
            initial_room = self._find_room_at(x, y)
            player = Player(id=player_id, x=x, y=y, color=color, current_room_id=initial_room.id if initial_room else None)
            
            self.players[player_id] = player
            self.connections[player_id] = websocket
            self.token_to_player[player_token] = player_id
            self._mark_dirty()
            
            await event_bus.emit_async(GameEvent(type=EventType.PLAYER_JOINED, source_id=player_id, data={"x": x, "y": y, "game_id": self.game_id}))
            print(f"[Game:{self.game_id}] Player {player_id} joined. Total: {len(self.players)}")
            
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
                        "player_token": player_token,
                        "room_id": initial_room.id,
                        "first_visit": True,
                        "game_id": self.game_id,
                    },
                ))
            
            return player_id, False

    async def remove_player(self, player_id: str, permanent: bool = False) -> None:
        """Handle player disconnection."""
        async with self._lock:
            if player_id in self.connections:
                del self.connections[player_id]
            
            if permanent:
                if player_id in self.players:
                    del self.players[player_id]
                # Remove token mapping
                tokens_to_remove = [t for t, pid in self.token_to_player.items() if pid == player_id]
                for t in tokens_to_remove:
                    del self.token_to_player[t]
            
            self._mark_dirty()
            await self._save_game("player_disconnected")
            print(f"[Game:{self.game_id}] Player {player_id} {'removed' if permanent else 'disconnected'}")

    async def remove_player_by_token(self, token: str) -> None:
        """Remove a player by their token."""
        if token in self.token_to_player:
            player_id = self.token_to_player[token]
            await self.remove_player(player_id, permanent=True)

    async def _respawn_player(self, player_id: str) -> None:
        """Respawn a defeated player."""
        if player_id not in self.players:
            return
        
        # Emit player died event for stats tracking before respawning
        player_token = self._get_token_for_player(player_id)
        if player_token:
            await event_bus.emit_async(GameEvent(
                type=EventType.PLAYER_DIED,
                source_id=player_id,
                data={
                    "player_token": player_token,
                    "game_id": self.game_id,
                },
            ))
        
        player = self.players[player_id]
        x, y = self._find_spawn_position()
        player.respawn(x, y)
        player.current_room_id = self._find_room_at(x, y).id if self._find_room_at(x, y) else None
        self._mark_dirty()
        
        if player_id in self.connections:
            try:
                await self.connections[player_id].send_text(json.dumps({
                    "type": "player_respawned", "player_id": player_id, "x": x, "y": y, "hp": player.hp, "max_hp": player.max_hp
                }))
            except: pass

    async def move_player(self, player_id: str, dx: int, dy: int) -> dict:
        """Move a player."""
        async with self._lock:
            result = {"success": False, "room_entered": None}
            if player_id not in self.players:
                return result
            
            player = self.players[player_id]
            new_x, new_y = player.x + dx, player.y + dy
            
            if not self._is_walkable(new_x, new_y) or self._is_occupied(new_x, new_y, player_id):
                return result
            
            player.x, player.y = new_x, new_y
            result["success"] = True
            self._mark_dirty()
            
            new_room = self._find_room_at(new_x, new_y)
            new_room_id = new_room.id if new_room else None
            
            if new_room_id != player.current_room_id:
                player.current_room_id = new_room_id
                first_visit = False
                if new_room and not new_room.visited:
                    new_room.visited = True
                    first_visit = True
                    await self._spawn_monsters_in_room(new_room)
                    self._mark_dirty()
                if new_room:
                    result["room_entered"] = new_room.get_info()
                    # Emit room entered event for stats tracking
                    player_token = self._get_token_for_player(player_id)
                    if player_token:
                        await event_bus.emit_async(GameEvent(
                            type=EventType.PLAYER_ENTERED_ROOM,
                            source_id=player_id,
                            data={
                                "player_token": player_token,
                                "room_id": new_room.id,
                                "first_visit": first_visit,
                                "game_id": self.game_id,
                            },
                        ))
            
            return result

    async def interact(self, player_id: str) -> dict:
        """Handle player interaction (fight or door)."""
        async with self._lock:
            if player_id not in self.players:
                return {"action": None}
            
            player = self.players[player_id]
            
            if self._is_player_in_fight(player_id):
                return {"action": "already_in_fight"}
            
            adjacent_monster = self._get_adjacent_monster(player_id)
            if adjacent_monster:
                existing_fight = self._get_fight_for_monster(adjacent_monster.id)
                if existing_fight:
                    return {"action": "can_join_fight", "fight_id": existing_fight.id, "fight": existing_fight.to_dict(), "monster": adjacent_monster.to_dict()}
                return {"action": "fight_request", "monster": adjacent_monster.to_dict(), "monster_id": adjacent_monster.id}
            
            directions = [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]
            for dx, dy in directions:
                x, y = player.x + dx, player.y + dy
                if 0 <= x < self.width and 0 <= y < self.height:
                    tile = self.tiles[y][x]
                    if tile == TILE_DOOR_CLOSED:
                        self.tiles[y][x] = TILE_DOOR_OPEN
                        self._mark_dirty()
                        return {"action": "door_opened", "x": x, "y": y}
                    elif tile == TILE_DOOR_OPEN:
                        self.tiles[y][x] = TILE_DOOR_CLOSED
                        self._mark_dirty()
                        return {"action": "door_closed", "x": x, "y": y}
            
            return {"action": None}

    # ============== Monster Management ==============

    async def _spawn_monsters_in_room(self, room: Room) -> None:
        occupied = {(p.x, p.y) for p in self.players.values()}
        occupied.update((m.x, m.y) for m in self.monsters.values())
        
        spawned = _get_monster_service().spawn_monsters_in_room(room=room, tiles=self.tiles, occupied_positions=occupied, map_width=self.width, map_height=self.height)
        for m in spawned:
            self.monsters[m.id] = m

    async def update_monsters(self, current_tick: int) -> bool:
        if not self.monsters:
            return False
        
        any_moved = False
        occupied = {(p.x, p.y) for p in self.players.values()}
        occupied.update((m.x, m.y) for m in self.monsters.values())
        
        await self._check_monster_aggro()
        
        for monster in self.monsters.values():
            if self._is_monster_in_fight(monster.id):
                continue
            room = next((r for r in self.rooms if r.id == monster.room_id), None)
            if not room:
                continue
            
            occupied.discard((monster.x, monster.y))
            world_state = self._build_monster_world_state(monster, room)
            moved = _get_monster_service().update_monster(monster=monster, room_bounds=room.bounds, tiles=self.tiles, occupied_positions=occupied, current_tick=current_tick, world_state=world_state)
            if moved:
                any_moved = True
            occupied.add((monster.x, monster.y))
        
        if any_moved:
            self._mark_dirty()
        return any_moved

    def _build_monster_world_state(self, monster: Monster, room: Optional[Room]) -> dict:
        nearby_players = [(pid, abs(p.x - monster.x) + abs(p.y - monster.y)) for pid, p in self.players.items() if abs(p.x - monster.x) + abs(p.y - monster.y) <= 6]
        return {
            "room_type": room.room_type if room else "chamber",
            "nearby_enemies": len(nearby_players),
            "nearby_allies": sum(1 for m in self.monsters.values() if m.room_id == (room.id if room else None) and m.id != monster.id),
            "distance_to_threat": min((d for _, d in nearby_players), default=8)
        }

    async def _check_monster_aggro(self) -> None:
        for monster_id in list(self.monsters.keys()):
            monster = self.monsters.get(monster_id)
            if not monster or self._is_monster_in_fight(monster_id):
                continue
            
            adjacent_players = self._get_adjacent_players(monster_id)
            if not adjacent_players:
                continue
            
            room = next((r for r in self.rooms if r.id == monster.room_id), None)
            world_state = self._build_monster_world_state(monster, room)
            world_state["distance_to_threat"] = 1
            
            action = _get_monster_service().decide_combat_action(monster, current_tick=int(time.time()), world_state=world_state)
            attack_actions = (AIAction.ATTACK_AGGRESSIVE, AIAction.ATTACK_DEFENSIVE, AIAction.AMBUSH)
            
            if action not in attack_actions:
                continue
            
            for pid in adjacent_players:
                player = self.players.get(pid)
                # Skip players in fight or with fight immunity
                if not player or self._is_player_in_fight(pid) or player.has_fight_immunity:
                    continue
                await self._monster_initiate_combat(monster_id, pid)
                break

    async def _monster_initiate_combat(self, monster_id: str, player_id: str) -> dict:
        if monster_id not in self.monsters or player_id not in self.players:
            return {"success": False}
        
        player = self.players[player_id]
        
        # Check if player has post-combat immunity
        if player.has_fight_immunity:
            return {"success": False, "error": "Player has fight immunity"}
        
        # Double-check player is not already in a fight (race condition protection)
        if self._is_player_in_fight(player_id):
            return {"success": False, "error": "Player already in fight"}
        
        # Also check if monster is already in a fight
        if self._is_monster_in_fight(monster_id):
            return {"success": False, "error": "Monster already in fight"}
        
        monster = self.monsters[monster_id]
        fight = Fight.create(monster_id=monster_id, initiator_player_id=player_id, turn_duration=120)
        fight.current_turn_index = fight.turn_order.index(monster_id)
        fight._reset_turn_timer()
        fight.add_log_entry("system", f"{monster.name} attacks!")
        
        self.active_fights[fight.id] = fight
        await self.send_monster_attacks(fight, monster, player_id)
        
        return {"success": True, "fight": fight.to_dict(), "monster": monster.to_dict()}

    async def process_monster_combat_turns(self) -> None:
        for fight_id in list(self.active_fights.keys()):
            fight = self.active_fights.get(fight_id)
            if not fight or not fight.is_active or not fight.is_monster_turn:
                continue
            
            monster = self.monsters.get(fight.monster_id)
            if not monster or not fight.player_ids:
                continue
            
            target_id = fight.player_ids[0]
            if not self.players.get(target_id):
                continue
            
            fight_active = await self._process_monster_turn(fight, monster, target_id)
            if not fight_active:
                continue
            
            original_ids = list(fight.player_ids)
            dead = [pid for pid in fight.player_ids if not self.players.get(pid, Player("",0,0)).is_alive]
            for pid in dead:
                fight.add_log_entry("death", "💀 A hero has fallen!")
                fight.remove_player(pid)
                await self._respawn_player(pid)
                # Grant immunity to respawned player
                if pid in self.players:
                    self.players[pid].grant_fight_immunity()
            
            if not fight.player_ids:
                fight.end_fight("defeat")
                # Grant immunity to all original players
                for pid in original_ids:
                    if pid in self.players:
                        self.players[pid].grant_fight_immunity()
                await self._broadcast_fight_ended_to_players(fight_id, "defeat", fight.to_dict(), original_ids)
                del self.active_fights[fight_id]
                continue
            
            fight.advance_turn()
            await self.send_fight_updated(fight, monster)

    async def process_turn_timeouts(self) -> None:
        for fight_id in list(self.active_fights.keys()):
            fight = self.active_fights.get(fight_id)
            if not fight or not fight.is_active or fight.is_monster_turn or fight.time_remaining > 0:
                continue
            
            timed_out_id = fight.current_turn_id
            player = self.players.get(timed_out_id)
            if not player:
                fight.remove_player(timed_out_id)
                continue
            
            player.hp = 0
            fight.add_log_entry("timeout", "⏱️ Time's up!")
            original_ids = list(fight.player_ids)
            fight.remove_player(timed_out_id)
            await self._respawn_player(timed_out_id)
            # Grant immunity to timed out player
            if timed_out_id in self.players:
                self.players[timed_out_id].grant_fight_immunity()
            
            if not fight.player_ids:
                fight.end_fight("defeat")
                # Grant immunity to all original players
                for pid in original_ids:
                    if pid in self.players:
                        self.players[pid].grant_fight_immunity()
                await self._broadcast_fight_ended_to_players(fight_id, "defeat", fight.to_dict(), original_ids)
                del self.active_fights[fight_id]
            else:
                monster = self.monsters.get(fight.monster_id)
                if monster:
                    await self.send_fight_updated(fight, monster)

    # ============== Fight Management ==============

    async def start_fight(self, player_id: str, monster_id: str) -> dict:
        async with self._lock:
            if player_id not in self.players or monster_id not in self.monsters:
                return {"success": False, "error": "Not found"}
            if self._is_player_in_fight(player_id) or self._is_monster_in_fight(monster_id):
                return {"success": False, "error": "Already in fight"}
            
            monster = self.monsters[monster_id]
            fight = Fight.create(monster_id=monster_id, initiator_player_id=player_id, turn_duration=120)
            self.active_fights[fight.id] = fight
            
            return {"success": True, "fight": fight.to_dict(), "monster": monster.to_dict(), "player_ids": fight.player_ids}

    async def join_fight(self, player_id: str, fight_id: str) -> dict:
        async with self._lock:
            if player_id not in self.players or fight_id not in self.active_fights:
                return {"success": False, "error": "Not found"}
            if self._is_player_in_fight(player_id):
                return {"success": False, "error": "Already in fight"}
            
            fight = self.active_fights[fight_id]
            monster = self.monsters.get(fight.monster_id)
            if not monster:
                return {"success": False, "error": "Monster not found"}
            
            player = self.players[player_id]
            if abs(player.x - monster.x) > 1 or abs(player.y - monster.y) > 1:
                return {"success": False, "error": "Not adjacent"}
            
            fight.add_player(player_id)
            return {"success": True, "fight": fight.to_dict(), "monster": monster.to_dict()}

    async def flee_fight(self, player_id: str, fight_id: str) -> dict:
        async with self._lock:
            if fight_id not in self.active_fights:
                return {"success": False, "error": "Fight not found"}
            
            fight = self.active_fights[fight_id]
            if player_id not in fight.player_ids:
                return {"success": False, "error": "Not in fight"}
            
            fight.remove_player(player_id)
            ended = not fight.is_active
            
            # Grant immunity to fleeing player
            if player_id in self.players:
                self.players[player_id].grant_fight_immunity()
            
            if ended:
                del self.active_fights[fight_id]
            
            return {"success": True, "fight_ended": ended, "fight": fight.to_dict() if not ended else None, "remaining_players": fight.player_ids if not ended else []}

    async def process_combat_action(self, player_id: str, fight_id: str, action: str) -> dict:
        async with self._lock:
            if fight_id not in self.active_fights:
                return {"success": False, "error": "Fight not found"}
            
            fight = self.active_fights[fight_id]
            if player_id not in fight.player_ids or fight.current_turn_id != player_id:
                return {"success": False, "error": "Not your turn"}
            
            player = self.players.get(player_id)
            monster = self.monsters.get(fight.monster_id)
            if not player or not monster:
                return {"success": False, "error": "Combatant not found"}
            
            player.is_defending = False
            
            if action == "attack":
                await self._process_player_attack(player, monster, fight)
            elif action == "defend":
                player.is_defending = True
                fight.add_log_entry("defend", "🛡️ You take a defensive stance!", source_id=player_id)
            elif action == "item":
                heal = min(roll_d20(0).rolls[0], player.max_hp - player.hp)
                if heal > 0:
                    player.heal(heal)
                    fight.add_log_entry("heal", f"🧪 Heal {heal} HP!", source_id=player_id)
            
            if not monster.is_alive:
                fight.end_fight("victory")
                fight.add_log_entry("victory", f"⚔️ {monster.name} defeated!")
                
                # Calculate XP earned from this kill
                xp_earned = get_xp_for_cr(monster.stats.challenge_rating)
                
                # Emit monster death event for stats tracking AND Q-learning (big penalty)
                player_token = self._get_token_for_player(player_id)
                # Build AI snapshot BEFORE deletion for Q-learning
                ai_snapshot = self._build_ai_snapshot(monster)
                if player_token:
                    await event_bus.emit_async(GameEvent(
                        type=EventType.MONSTER_DIED,
                        source_id=monster.id,
                        data={
                            "player_token": player_token,
                            "monster_type": monster.monster_type,
                            "challenge_rating": monster.stats.challenge_rating,
                            "game_id": self.game_id,
                            "fight_id": fight_id,
                            # AI snapshot for Q-learning with death penalty
                            "ai_snapshot": ai_snapshot,
                            "reward": -100.0,  # Heavy penalty for death
                        },
                    ))
                
                # Grant fight immunity to all players in the fight
                for pid in fight.player_ids:
                    if pid in self.players:
                        self.players[pid].grant_fight_immunity()
                del self.monsters[monster.id]
                del self.active_fights[fight_id]
                self._mark_dirty()
                return {"success": True, "fight_ended": True, "result": "victory", "fight": fight.to_dict(), "xp_earned": xp_earned, "monster_type": monster.monster_type}
            
            fight.advance_turn()
            
            if fight.is_monster_turn:
                await self._process_monster_turn(fight, monster, player_id)
                
                original_ids = list(fight.player_ids)
                dead = [pid for pid in fight.player_ids if not self.players.get(pid, Player("",0,0)).is_alive]
                for pid in dead:
                    fight.add_log_entry("death", "💀 A hero has fallen!")
                    fight.remove_player(pid)
                    await self._respawn_player(pid)
                    # Grant immunity to dead player
                    if pid in self.players:
                        self.players[pid].grant_fight_immunity()
                
                if not fight.player_ids:
                    fight.end_fight("defeat")
                    # Grant immunity to all original players
                    for pid in original_ids:
                        if pid in self.players:
                            self.players[pid].grant_fight_immunity()
                    fight_data = fight.to_dict()
                    fight_data["player_ids"] = original_ids
                    del self.active_fights[fight_id]
                    return {"success": True, "fight_ended": True, "result": "defeat", "fight": fight_data}
                
                fight.advance_turn()
            
            return {"success": True, "fight": fight.to_dict(), "action": action}

    async def _process_player_attack(self, player: Player, monster: Monster, fight: Fight) -> dict:
        attack_roll, hit, is_crit = roll_attack(player.str_mod, monster.stats.ac)
        actual = 0
        
        if is_crit:
            dmg = roll_damage(player.damage_dice, is_critical=True)
            actual = monster.take_damage(dmg.total)
            fight.add_log_entry("critical", f"⚔️ CRITICAL! {actual} damage!", source_id=player.id)
        elif hit:
            dmg = roll_damage(player.damage_dice, is_critical=False)
            actual = monster.take_damage(dmg.total)
            fight.add_log_entry("hit", f"⚔️ Hit for {actual} damage!", source_id=player.id)
        else:
            fight.add_log_entry("miss", "⚔️ Miss!", source_id=player.id)
        
        # Emit damage event for stats tracking AND Q-learning reward
        if actual > 0:
            player_token = self._get_token_for_player(player.id)
            if player_token:
                # Negative reward for monster taking damage (penalty proportional to damage)
                await event_bus.emit_async(GameEvent(
                    type=EventType.DAMAGE_DEALT,
                    source_id=player.id,
                    target_id=monster.id,
                    data={
                        "player_token": player_token,
                        "damage": actual,
                        "is_player_source": True,
                        "is_critical": is_crit,
                        "game_id": self.game_id,
                        # AI snapshot for Q-learning
                        "ai_snapshot": self._build_ai_snapshot(monster),
                        "reward": -float(actual),  # Penalty for taking damage
                    },
                ))
        
        return {"hit": hit}

    async def _process_monster_turn(self, fight: Fight, monster: Monster, target_id: str) -> bool:
        player = self.players.get(target_id)
        if not player:
            return False
        
        room = next((r for r in self.rooms if r.id == monster.room_id), None)
        world_state = self._build_monster_world_state(monster, room)
        world_state["distance_to_threat"] = 1
        
        action = _get_monster_service().decide_combat_action(monster, current_tick=int(time.time()), world_state=world_state)
        
        if action == AIAction.DEFEND:
            fight.add_log_entry("enemy_defend", f"🛡️ {monster.name} braces!", source_id=monster.id)
            return True
        if action == AIAction.FLEE:
            fight.add_log_entry("enemy_flee", f"🏃 {monster.name} flees!", source_id=monster.id)
            fight.end_fight("victory")
            # Half XP for fleeing monster
            xp_earned = get_xp_for_cr(monster.stats.challenge_rating) // 2
            # Grant immunity to all players in the fight
            for pid in fight.player_ids:
                if pid in self.players:
                    self.players[pid].grant_fight_immunity()
            if monster.id in self.monsters:
                del self.monsters[monster.id]
            if fight.id in self.active_fights:
                del self.active_fights[fight.id]
            await self._broadcast_fight_ended_to_players(fight.id, "victory", fight.to_dict(), list(fight.player_ids), xp_earned, monster.monster_type)
            return False
        
        attack_bonus = monster.stats.get_modifier(monster.stats.str)
        attack_roll, hit, is_crit = roll_attack(attack_bonus, player.effective_ac)
        monster_damage = f"1d{6 + int(monster.stats.challenge_rating * 2)}"
        
        if is_crit or hit:
            dmg = roll_damage(monster_damage, is_critical=is_crit)
            actual = player.take_damage(max(1, dmg.total))
            entry_type = "enemy_critical" if is_crit else "enemy_hit"
            fight.add_log_entry(entry_type, f"🐲 {monster.name} hits for {actual}!", source_id=monster.id)
            
            # Emit damage event for stats tracking AND Q-learning reward
            player_token = self._get_token_for_player(target_id)
            if player_token:
                # Positive reward for monster dealing damage (reward proportional to damage)
                await event_bus.emit_async(GameEvent(
                    type=EventType.DAMAGE_DEALT,
                    source_id=monster.id,
                    target_id=target_id,
                    data={
                        "player_token": player_token,
                        "damage": actual,
                        "is_player_source": False,
                        "is_critical": is_crit,
                        "game_id": self.game_id,
                        # AI snapshot for Q-learning
                        "ai_snapshot": self._build_ai_snapshot(monster),
                        "reward": float(actual),  # Reward for dealing damage
                    },
                ))
        else:
            fight.add_log_entry("enemy_miss", f"🐲 {monster.name} misses!", source_id=monster.id)
        
        return True

    # ============== Broadcasting ==============

    async def _broadcast_message(self, message: dict) -> None:
        if not self.connections:
            return
        text = json.dumps(message)
        disconnected = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_text(text)
            except:
                disconnected.append(pid)
        for pid in disconnected:
            await self.remove_player(pid)

    async def broadcast_state(self) -> None:
        if not self.connections:
            return
        disconnected = []
        for pid, ws in self.connections.items():
            try:
                state = self.get_viewport_state(pid)
                await ws.send_text(json.dumps({"type": "state_update", "state": state}))
            except:
                disconnected.append(pid)
        for pid in disconnected:
            await self.remove_player(pid)

    async def send_welcome(self, player_id: str, is_reconnection: bool = False) -> None:
        if player_id not in self.connections:
            return
        state = self.get_viewport_state(player_id)
        player = self.players.get(player_id)
        room_info = None
        if player and player.current_room_id:
            room = next((r for r in self.rooms if r.id == player.current_room_id), None)
            if room:
                room_info = room.get_info()
        
        await self.connections[player_id].send_text(json.dumps({
            "type": "welcome", "playerId": player_id, "state": state, "currentRoom": room_info, "isReconnection": is_reconnection
        }))

    async def send_room_entered(self, player_id: str, room_info: dict) -> None:
        if player_id in self.connections:
            try:
                await self.connections[player_id].send_text(json.dumps({"type": "room_entered", "room": room_info}))
            except: pass

    async def broadcast_player_joined(self, player_id: str) -> None:
        msg = json.dumps({"type": "player_joined", "playerId": player_id})
        for pid, ws in self.connections.items():
            if pid != player_id:
                try: await ws.send_text(msg)
                except: pass

    async def broadcast_player_left(self, player_id: str) -> None:
        msg = json.dumps({"type": "player_left", "playerId": player_id})
        for ws in self.connections.values():
            try: await ws.send_text(msg)
            except: pass

    async def send_fight_started(self, fight: Fight, monster: Monster, to_player_ids: list[str]) -> None:
        msg = json.dumps({"type": "fight_started", "fight": fight.to_dict(), "monster": monster.to_dict()})
        for pid in to_player_ids:
            if pid in self.connections:
                try: await self.connections[pid].send_text(msg)
                except: pass

    async def send_fight_updated(self, fight: Fight, monster: Monster) -> None:
        # Include players in fight with their current stats (especially HP)
        fight_players = {pid: self.players[pid].to_dict() for pid in fight.player_ids if pid in self.players}
        msg = json.dumps({
            "type": "fight_updated", 
            "fight": fight.to_dict(), 
            "monster": monster.to_dict(),
            "players": fight_players
        })
        for pid in fight.player_ids:
            if pid in self.connections:
                try: await self.connections[pid].send_text(msg)
                except: pass

    async def send_monster_attacks(self, fight: Fight, monster: Monster, target_id: str) -> None:
        if target_id in self.connections:
            # Include players in fight with their current stats
            fight_players = {pid: self.players[pid].to_dict() for pid in fight.player_ids if pid in self.players}
            try:
                await self.connections[target_id].send_text(json.dumps({
                    "type": "monster_attacks", 
                    "fight": fight.to_dict(), 
                    "monster": monster.to_dict(),
                    "players": fight_players
                }))
            except: pass

    async def send_player_fled(self, fight_id: str, fled_player_id: str, remaining_player_ids: list[str]) -> None:
        """Notify remaining players that someone fled."""
        msg = json.dumps({"type": "player_fled", "fight_id": fight_id, "fled_player_id": fled_player_id})
        for pid in remaining_player_ids:
            if pid in self.connections:
                try: await self.connections[pid].send_text(msg)
                except: pass

    async def send_fight_ended(self, fight_id: str, result: str, to_player_ids: list[str]) -> None:
        """Notify players that a fight has ended."""
        msg = json.dumps({"type": "fight_ended", "fight_id": fight_id, "result": result})
        for pid in to_player_ids:
            if pid in self.connections:
                try: await self.connections[pid].send_text(msg)
                except: pass

    async def _broadcast_fight_ended_to_players(self, fight_id: str, result: str, fight_data: dict, player_ids: list[str], xp_earned: int = 0, monster_type: str = None) -> None:
        msg = json.dumps({"type": "fight_ended", "fight_id": fight_id, "result": result, "fight": fight_data, "xp_earned": xp_earned, "monster_type": monster_type})
        for pid in player_ids:
            if pid in self.connections:
                try: await self.connections[pid].send_text(msg)
                except: pass
        await self.broadcast_state()

    async def broadcast_fight_ended(self, result: dict, fight_id: str) -> None:
        fight_data = result.get("fight", {})
        player_ids = fight_data.get("player_ids", [])
        xp_earned = result.get("xp_earned", 0)
        monster_type = result.get("monster_type")
        await self._broadcast_fight_ended_to_players(fight_id, result.get("result", "unknown"), fight_data, player_ids, xp_earned, monster_type)
