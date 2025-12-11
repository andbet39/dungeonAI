"""Monster service for spawning, AI behavior, and configuration management."""
import json
import random
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from ..config import settings
from ..core.events import event_bus, EventType, GameEvent
from ..domain.entities import (
    Monster,
    MonsterBehavior,
    MonsterIntelligenceState,
    MonsterStats,
    Room,
)
from ..domain.intelligence import (
    DecisionContext,
    DecisionEngine,
    DecisionResult,
    PersonalityProfile,
    QLearningConfig,
    SpeciesKnowledgeStore,
    SpeciesKnowledgeRecord,
    ThreatMemory,
)
from ..domain.intelligence.learning import AIAction
from ..domain.map import (
    TILE_DOOR_CLOSED, TILE_DOOR_OPEN, TILE_FLOOR,
    AStar, Direction, get_direction_to_target, is_in_corridor, find_nearest_corridor,
)
from ..db import mongodb_manager
from .mongodb_species_store import MongoDBSpeciesKnowledgeStore


@dataclass
class MonsterAIProfile:
    decision_engine: DecisionEngine
    personality: PersonalityProfile
    memory_capacity: int
    memory_decay: float
    decision_cooldown_ticks: int
    preferred_tactics: list[str]


class MonsterService:
    """Service for monster spawning, configuration, and AI behavior."""
    
    _instance: Optional["MonsterService"] = None
    
    def __new__(cls) -> "MonsterService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        self.config_path = settings.config_data_dir
        self.monster_types: dict = {}
        self.spawn_rates: dict = {}
        self.ai_profiles: dict[str, MonsterAIProfile] = {}
        self.species_store = None  # Will be set later in initialize()

        print("[MonsterService] Initializing MonsterService (deferred species store setup)")
        
        self.monster_memories: dict[str, ThreatMemory] = {}
        # Don't load configs yet - will be done in initialize()
        event_bus.subscribe_async(EventType.DAMAGE_DEALT, self._handle_damage_event)
        event_bus.subscribe_async(EventType.MONSTER_DIED, self._handle_monster_death)
        self._initialized = True

    def initialize(self) -> None:
        """Initialize the species store and load configurations."""
        if self.species_store is not None:
            return  # Already initialized

        print(f"[MonsterService] Initializing species store - MongoDB enabled: {settings.mongodb.is_enabled}, connected: {mongodb_manager.is_connected}")
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            self.species_store = MongoDBSpeciesKnowledgeStore()
            print("[MonsterService] Using MongoDB species knowledge store")
        else:
            self.species_store = SpeciesKnowledgeStore()
            print("[MonsterService] Using JSON species knowledge store")

        self._load_configs()

    def _ensure_initialized(self) -> None:
        """Ensure the service is fully initialized."""
        if self.species_store is None:
            self.initialize()

    def reinitialize_species_store(self) -> None:
        """Reinitialize the species store based on current MongoDB connection status."""
        print(f"[MonsterService] Reinitializing species store - MongoDB connected: {mongodb_manager.is_connected}")
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            self.species_store = MongoDBSpeciesKnowledgeStore()
            print("[MonsterService] Switched to MongoDB species knowledge store")
        else:
            self.species_store = SpeciesKnowledgeStore()
            print("[MonsterService] Switched to JSON species knowledge store")
        
        # Reload spawn rates with the new store
        self.spawn_rates = self._load_spawn_rates_sync()
    
    def _load_configs(self) -> None:
        """Load monster and spawn rate configurations."""
        # Load monster types - try MongoDB first, fallback to JSON
        self.monster_types = self._load_monsters_sync()

        # Load spawn rates - try MongoDB first, fallback to JSON
        self.spawn_rates = self._load_spawn_rates_sync()
        self._build_ai_profiles()

    def _load_monsters_sync(self) -> dict:
        """Load monster types configuration (synchronous)."""
        # Try MongoDB first if available
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # In async context, schedule task
                    asyncio.create_task(self._async_load_monsters_to_cache())
                    # Return from JSON for now
                    return self._load_monsters_from_json()
                else:
                    # Can use run_until_complete
                    return loop.run_until_complete(self._async_load_monsters())
            except Exception as e:
                print(f"[MonsterService] Error loading monsters from MongoDB: {e}")

        # Fallback to JSON
        return self._load_monsters_from_json()

    async def _async_load_monsters(self) -> dict:
        """Load monster types from MongoDB (async)."""
        try:
            doc = await mongodb_manager.db.monsters.find_one({"config_version": "1.0"})
            if doc and "monsters" in doc:
                monsters = doc["monsters"]
                print(f"[MonsterService] ✓ Loaded {len(monsters)} monster types from MongoDB")
                return monsters
        except Exception as e:
            print(f"[MonsterService] Error loading monsters from MongoDB: {e}")

        # Fallback to JSON
        return self._load_monsters_from_json()

    async def _async_load_monsters_to_cache(self) -> None:
        """Load monsters from MongoDB and update cache (async helper)."""
        monsters = await self._async_load_monsters()
        if monsters:
            self.monster_types = monsters
            self._build_ai_profiles()

    def _load_monsters_from_json(self) -> dict:
        """Load monster types from JSON file (fallback)."""
        monsters_file = self.config_path / "monsters.json"
        if monsters_file.exists():
            with open(monsters_file, "r") as f:
                monsters = json.load(f)
            print(f"[MonsterService] Loaded {len(monsters)} monster types from JSON")
            return monsters
        else:
            print(f"[MonsterService] Warning: {monsters_file} not found")
            return {}

    def _load_spawn_rates_sync(self) -> dict:
        """Load spawn rates configuration (synchronous)."""
        # Try MongoDB first if available
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # In async context, schedule task
                    asyncio.create_task(self._async_load_spawn_rates_to_cache())
                    # Return from JSON for now
                    return self._load_spawn_rates_from_json()
                else:
                    # Can use run_until_complete
                    return loop.run_until_complete(self._async_load_spawn_rates())
            except Exception as e:
                print(f"[MonsterService] Error loading spawn rates from MongoDB: {e}")

        # Fallback to JSON
        return self._load_spawn_rates_from_json()

    async def _async_load_spawn_rates(self) -> dict:
        """Load spawn rates from MongoDB (async)."""
        try:
            doc = await mongodb_manager.db.spawn_rates.find_one({"config_version": "1.0"})
            if doc:
                # Remove MongoDB-specific fields
                doc.pop("_id", None)
                doc.pop("config_version", None)
                doc.pop("created_at", None)
                doc.pop("last_updated", None)
                print("[MonsterService] Loaded spawn rates from MongoDB")
                return doc
        except Exception as e:
            print(f"[MonsterService] Error loading from MongoDB: {e}")

        # Fallback to JSON
        return self._load_spawn_rates_from_json()

    async def _async_load_spawn_rates_to_cache(self) -> None:
        """Async helper to load spawn rates and update cache."""
        self.spawn_rates = await self._async_load_spawn_rates()

    def _load_spawn_rates_from_json(self) -> dict:
        """Load spawn rates from JSON file."""
        spawn_file = self.config_path / "spawn_rates.json"
        if spawn_file.exists():
            with open(spawn_file, "r") as f:
                spawn_rates = json.load(f)
            print("[MonsterService] Loaded spawn rates from JSON")
            return spawn_rates
        else:
            print(f"[MonsterService] Warning: {spawn_file} not found, using defaults")
            return {
                "room_spawn_chances": {},
                "room_monster_weights": {},
                "max_monsters_per_room": 2,
                "min_room_area_for_spawn": 36
            }

    def _build_ai_profiles(self) -> None:
        self.ai_profiles.clear()
        for monster_type, config in self.monster_types.items():
            intel = config.get("intelligence")
            if not intel:
                continue

            personality = PersonalityProfile.from_dict(intel.get("personality"))
            learning_cfg = QLearningConfig(
                learning_rate=float(intel.get("learning", {}).get("learning_rate", 0.1)),
                discount_factor=float(intel.get("learning", {}).get("discount_factor", 0.95)),
                exploration_rate=float(intel.get("learning", {}).get("exploration_rate", 0.3)),
                min_exploration_rate=float(intel.get("learning", {}).get("min_exploration_rate", 0.05)),
                exploration_decay=float(intel.get("learning", {}).get("exploration_decay", 0.995)),
            )
            memory_cfg = intel.get("memory", {})
            profile = MonsterAIProfile(
                decision_engine=DecisionEngine(config=learning_cfg),
                personality=personality,
                memory_capacity=int(memory_cfg.get("capacity", 5)),
                memory_decay=float(memory_cfg.get("decay_rate", 0.05)),
                decision_cooldown_ticks=int(intel.get("decision_cooldown_ticks", 2)),
                preferred_tactics=intel.get("preferred_tactics", []),
            )
            self.ai_profiles[monster_type] = profile
    
    def get_spawn_chance(self, room_type: str) -> float:
        """Get spawn probability for a room type."""
        return self.spawn_rates.get("room_spawn_chances", {}).get(room_type, 0.5)
    
    def get_monster_weights(self, room_type: str) -> dict[str, int]:
        """Get monster type weights for a room type."""
        default_weights = {mt: 5 for mt in self.monster_types.keys()}
        return self.spawn_rates.get("room_monster_weights", {}).get(room_type, default_weights)
    
    def select_monster_type(self, room_type: str) -> Optional[str]:
        """Select a random monster type based on room weights."""
        weights = self.get_monster_weights(room_type)
        if not weights:
            return None
        
        valid_weights = {k: v for k, v in weights.items() if k in self.monster_types}
        if not valid_weights:
            return None
        
        total = sum(valid_weights.values())
        r = random.random() * total
        cumulative = 0
        for monster_type, weight in valid_weights.items():
            cumulative += weight
            if r <= cumulative:
                return monster_type
        
        return list(valid_weights.keys())[0]
    
    def create_monster(
        self,
        monster_type: str,
        x: int,
        y: int,
        room_id: str
    ) -> Optional[Monster]:
        """Create a new monster instance from a type configuration."""
        self._ensure_initialized()
        
        if monster_type not in self.monster_types:
            return None
        
        config = self.monster_types[monster_type]
        monster_id = f"m_{str(uuid.uuid4())[:8]}"

        monster = Monster(
            id=monster_id,
            monster_type=monster_type,
            name=config["name"],
            x=x,
            y=y,
            room_id=room_id,
            symbol=config["symbol"],
            color=config["color"],
            stats=MonsterStats.from_dict(config["stats"]),
            behavior=MonsterBehavior(config.get("behavior", "static")),
            description=config.get("description", "")
        )
        profile = self.ai_profiles.get(monster_type)
        if profile:
            record = self.species_store.get_or_create(
                monster_type,
                state_space=profile.decision_engine.encoder.state_space,
                action_count=len(AIAction),
            )
            monster.intelligence_state = MonsterIntelligenceState(
                generation=record.generation,
                q_table_version=record.q_table.shape[0],
            )
            self.monster_memories[monster.id] = ThreatMemory(
                capacity=profile.memory_capacity,
                decay_rate=profile.memory_decay,
            )
        return monster
    
    def get_max_monsters_per_room(self) -> int:
        """Get maximum monsters that can spawn in a room."""
        return self.spawn_rates.get("max_monsters_per_room", 2)
    
    def get_min_room_area(self) -> int:
        """Get minimum room area required for monster spawns."""
        return self.spawn_rates.get("min_room_area_for_spawn", 36)
    
    def spawn_monsters_in_room(
        self,
        room: Room,
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        map_width: int,
        map_height: int
    ) -> list[Monster]:
        """
        Spawn monsters in a room.
        
        Args:
            room: The room to spawn monsters in
            tiles: 2D tile array
            occupied_positions: Set of (x, y) positions already occupied
            map_width: Width of the map
            map_height: Height of the map
        
        Returns:
            List of spawned monsters
        """
        spawned = []
        
        # Check if room meets minimum size requirement
        if room.area < self.get_min_room_area():
            return spawned
        
        # Get spawn chance for this room type
        spawn_chance = self.get_spawn_chance(room.room_type)
        
        # Roll for spawn
        if random.random() > spawn_chance:
            return spawned
        
        # Calculate number of monsters
        max_monsters = self.get_max_monsters_per_room()
        monster_count = min(max_monsters, max(1, room.area // 50))
        
        # Get valid spawn positions
        valid_positions = []
        for y in range(room.y + 1, room.y + room.height - 1):
            for x in range(room.x + 1, room.x + room.width - 1):
                if tiles[y][x] == TILE_FLOOR and (x, y) not in occupied_positions:
                    # Check not adjacent to door
                    near_door = False
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < map_width and 0 <= ny < map_height:
                                if tiles[ny][nx] in (TILE_DOOR_CLOSED, TILE_DOOR_OPEN):
                                    near_door = True
                                    break
                        if near_door:
                            break
                    if not near_door:
                        valid_positions.append((x, y))
        
        if not valid_positions:
            return spawned
        
        # Spawn monsters
        for _ in range(min(monster_count, len(valid_positions))):
            if not valid_positions:
                break
            
            monster_type = self.select_monster_type(room.room_type)
            if not monster_type:
                continue
            
            pos = random.choice(valid_positions)
            valid_positions.remove(pos)
            
            monster = self.create_monster(
                monster_type=monster_type,
                x=pos[0],
                y=pos[1],
                room_id=room.id
            )
            
            if monster:
                spawned.append(monster)
                occupied_positions.add(pos)
                print(f"[MonsterService] Spawned {monster.name} at ({pos[0]}, {pos[1]}) in {room.name}")
        
        return spawned
    
    def update_monster(
        self,
        monster: Monster,
        room_bounds: tuple[int, int, int, int],
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
        *,
        world_state: Optional[dict[str, object]] = None,
        log_callback: Optional[Callable[[dict], None]] = None,
        rooms: Optional[list[Room]] = None,
    ) -> bool:
        """
        Update a monster's AI behavior.
        
        Args:
            monster: The monster to update
            room_bounds: (x, y, width, height) of the room
            tiles: 2D tile array
            occupied_positions: Set of occupied positions
            current_tick: Current game tick
            world_state: Optional world state context
            log_callback: Optional callback to receive decision log data
            rooms: Optional list of all rooms (for corridor detection/patrol)
        
        Returns:
            True if monster moved
        """
        profile = self.ai_profiles.get(monster.monster_type)
        if not profile:
            if monster.behavior == MonsterBehavior.STATIC:
                return False
            if monster.behavior == MonsterBehavior.PATROL:
                return self._update_patrol(monster, room_bounds, tiles, occupied_positions, current_tick)
            if monster.behavior == MonsterBehavior.SEARCHING:
                return self._update_searching(monster, room_bounds, tiles, occupied_positions)
            return False

        world = self._prepare_world_state(world_state)
        decision, species_record, _ = self._evaluate_decision(
            monster=monster,
            profile=profile,
            world_state=world,
            current_tick=current_tick,
            log_callback=log_callback,
        )

        return self._execute_action(
            decision.action,
            monster,
            room_bounds,
            tiles,
            occupied_positions,
            current_tick,
            world_state=world,
            rooms=rooms,
        )

    def decide_combat_action(
        self,
        monster: Monster,
        *,
        current_tick: int,
        world_state: Optional[dict[str, object]] = None,
    ) -> AIAction:
        profile = self.ai_profiles.get(monster.monster_type)
        if not profile:
            return AIAction.ATTACK_AGGRESSIVE
        world = self._prepare_world_state(world_state)
        decision, _, _ = self._evaluate_decision(
            monster=monster,
            profile=profile,
            world_state=world,
            current_tick=current_tick,
        )
        return decision.action

    def _prepare_world_state(self, world_state: Optional[dict[str, object]]) -> dict:
        base = {
            "room_type": "chamber",
            "nearby_enemies": 0,
            "nearby_allies": 0,
            "distance_to_threat": 8,
            "threat_direction": 8,  # NONE (Direction.NONE.value)
            "in_corridor": False,
            "threat_position": None,  # (x, y) of nearest threat, if any
        }
        if world_state:
            base.update(world_state)
        return base

    def _evaluate_decision(
        self,
        *,
        monster: Monster,
        profile: MonsterAIProfile,
        world_state: dict,
        current_tick: int,
        log_callback: Optional[Callable[[dict], None]] = None,
    ) -> tuple[DecisionResult, SpeciesKnowledgeRecord, ThreatMemory]:
        self._ensure_initialized()
        
        memory = self._get_memory(monster.id, profile)
        memory.decay(current_tick)
        species_record = self.species_store.get_or_create(
            monster.monster_type,
            state_space=profile.decision_engine.encoder.state_space,
            action_count=len(AIAction),
        )
        context = DecisionContext(
            monster=monster,
            memory=memory,
            personality=profile.personality,
            q_table=species_record.q_table,
            current_tick=current_tick,
            world_state=world_state,
        )
        decision = profile.decision_engine.decide(context)
        monster.intelligence_state.last_state_index = decision.state_index
        monster.intelligence_state.last_action = decision.action.name
        monster.intelligence_state.last_decision_tick = current_tick
        monster.intelligence_state.q_table_version = species_record.q_table.shape[0]
        monster.intelligence_state.last_world_state = dict(world_state)
        
        # Call log callback if provided
        if log_callback:
            q_values = species_record.q_table[decision.state_index].tolist()
            action_names = [a.name for a in AIAction]
            hp_ratio = monster.stats.hp / monster.stats.max_hp if monster.stats.max_hp > 0 else 1.0
            
            log_callback({
                "monster_id": monster.id,
                "tick": current_tick,
                "state_index": decision.state_index,
                "state_breakdown": {
                    "hp_ratio": hp_ratio,
                    "nearby_enemies": world_state.get("nearby_enemies", 0),
                    "nearby_allies": world_state.get("nearby_allies", 0),
                    "room_type": world_state.get("room_type", "chamber"),
                    "distance_to_threat": world_state.get("distance_to_threat", 8),
                    "threat_direction": world_state.get("threat_direction", 8),
                    "in_corridor": world_state.get("in_corridor", False),
                },
                "q_values": dict(zip(action_names, q_values)),
                "action": decision.action.name,
                "explored": decision.confidence < 0.5,  # Low confidence = likely explored
                "confidence": decision.confidence,
            })
        
        return decision, species_record, memory

    def _get_memory(self, monster_id: str, profile: MonsterAIProfile) -> ThreatMemory:
        memory = self.monster_memories.get(monster_id)
        if not memory:
            memory = ThreatMemory(
                capacity=profile.memory_capacity,
                decay_rate=profile.memory_decay,
            )
            self.monster_memories[monster_id] = memory
        return memory

    def _execute_action(
        self,
        action: AIAction,
        monster: Monster,
        room_bounds: tuple[int, int, int, int],
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
        *,
        world_state: Optional[dict] = None,
        rooms: Optional[list[Room]] = None,
    ) -> bool:
        """
        Execute an AI action for a monster.
        
        Args:
            action: The AI action to execute
            monster: The monster executing the action
            room_bounds: (x, y, width, height) of the current room
            tiles: 2D tile array
            occupied_positions: Set of occupied (x, y) positions
            current_tick: Current game tick
            world_state: World state containing threat info
            rooms: List of all rooms (for corridor detection)
        
        Returns:
            True if monster moved, False otherwise
        """
        # Movement actions
        if action == AIAction.MOVE_TOWARD_THREAT:
            return self._move_toward_threat(
                monster, tiles, occupied_positions, current_tick,
                world_state=world_state,
            )
        
        if action == AIAction.MOVE_AWAY_FROM_THREAT:
            return self._move_away_from_threat(
                monster, tiles, occupied_positions, current_tick,
                world_state=world_state,
            )
        
        if action == AIAction.PATROL_WAYPOINT:
            return self._patrol_waypoint(
                monster, tiles, occupied_positions, current_tick,
                rooms=rooms,
            )
        
        if action in (AIAction.PATROL, AIAction.AMBUSH, AIAction.ATTACK_DEFENSIVE):
            return self._update_patrol(monster, room_bounds, tiles, occupied_positions, current_tick)
        
        if action == AIAction.FLEE:
            return self._attempt_flee(monster, room_bounds, tiles, occupied_positions, current_tick)
        
        if action == AIAction.CALL_ALLIES:
            return False  # No movement for calling allies
        
        return False  # ATTACK_AGGRESSIVE and others don't move
    
    def _update_patrol(
        self,
        monster: Monster,
        room_bounds: tuple[int, int, int, int],
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int
    ) -> bool:
        """Patrol behavior: move randomly within room bounds."""
        # Only move every 2-4 ticks
        move_interval = 2 + (hash(monster.id) % 3)
        if current_tick - monster.last_move_tick < move_interval:
            return False
        
        rx, ry, rw, rh = room_bounds
        
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(directions)
        
        for dx, dy in directions:
            new_x = monster.x + dx
            new_y = monster.y + dy
            
            # Check room bounds
            if not (rx <= new_x < rx + rw and ry <= new_y < ry + rh):
                continue
            
            # Check tile is walkable
            if tiles[new_y][new_x] != TILE_FLOOR:
                continue
            
            # Check not occupied
            if (new_x, new_y) in occupied_positions:
                continue
            
            # Move monster
            monster.x = new_x
            monster.y = new_y
            monster.last_move_tick = current_tick
            return True
        
        return False
    
    def _update_searching(
        self,
        monster: Monster,
        room_bounds: tuple[int, int, int, int],
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]]
    ) -> bool:
        """Searching behavior: placeholder for future implementation."""
        # For now, just act like patrol
        return False

    def _attempt_flee(
        self,
        monster: Monster,
        room_bounds: tuple[int, int, int, int],
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
    ) -> bool:
        rx, ry, rw, rh = room_bounds
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(directions)
        for dx, dy in directions:
            new_x = monster.x + dx
            new_y = monster.y + dy
            if not (rx <= new_x < rx + rw and ry <= new_y < ry + rh):
                continue
            if tiles[new_y][new_x] != TILE_FLOOR:
                continue
            if (new_x, new_y) in occupied_positions:
                continue
            monster.x = new_x
            monster.y = new_y
            monster.last_move_tick = current_tick
            return True
        return False

    def _move_toward_threat(
        self,
        monster: Monster,
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
        *,
        world_state: Optional[dict] = None,
    ) -> bool:
        """
        Move monster toward the nearest threat using A* pathfinding.
        
        This is used by aggressive monsters to chase players.
        Movement is rate-limited to prevent jittery behavior.
        """
        # Rate limit movement
        move_interval = 2 + (hash(monster.id) % 2)  # 2-3 ticks between moves
        if current_tick - monster.last_move_tick < move_interval:
            return False
        
        # Get threat position from world state
        threat_pos = world_state.get("threat_position") if world_state else None
        if not threat_pos:
            return False
        
        threat_x, threat_y = threat_pos
        
        # Don't move if already adjacent to threat
        dist = abs(monster.x - threat_x) + abs(monster.y - threat_y)
        if dist <= 1:
            return False
        
        # Use A* to find path to threat
        astar = AStar(tiles, occupied_positions)
        path = astar.find_path(
            start=(monster.x, monster.y),
            goal=(threat_x, threat_y),
            max_iterations=200,
        )
        
        if not path:
            return False
        
        # Move to first step in path
        next_x, next_y = path[0]
        
        # Verify position is still valid (not occupied since pathfinding)
        if (next_x, next_y) in occupied_positions:
            return False
        
        monster.x = next_x
        monster.y = next_y
        monster.last_move_tick = current_tick
        return True

    def _move_away_from_threat(
        self,
        monster: Monster,
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
        *,
        world_state: Optional[dict] = None,
    ) -> bool:
        """
        Move monster away from the nearest threat (tactical retreat).
        
        Unlike FLEE which is panicked, this is a calculated retreat to
        a safer position while maintaining visibility/engagement.
        """
        # Rate limit movement
        move_interval = 2 + (hash(monster.id) % 2)
        if current_tick - monster.last_move_tick < move_interval:
            return False
        
        # Get threat position from world state
        threat_pos = world_state.get("threat_position") if world_state else None
        if not threat_pos:
            return False
        
        threat_x, threat_y = threat_pos
        
        # Use A* to find best flee position
        astar = AStar(tiles, occupied_positions)
        flee_pos = astar.find_flee_position(
            start=(monster.x, monster.y),
            threat=(threat_x, threat_y),
            search_radius=4,
        )
        
        if not flee_pos:
            # Fallback: try simple directional movement away from threat
            direction = get_direction_to_target(monster.x, monster.y, threat_x, threat_y)
            opposite = direction.opposite()
            dx, dy = opposite.to_delta()
            
            new_x, new_y = monster.x + dx, monster.y + dy
            if self._can_move_to(new_x, new_y, tiles, occupied_positions):
                monster.x = new_x
                monster.y = new_y
                monster.last_move_tick = current_tick
                return True
            return False
        
        # Find path to flee position
        path = astar.find_path(
            start=(monster.x, monster.y),
            goal=flee_pos,
            max_iterations=100,
        )
        
        if not path:
            return False
        
        next_x, next_y = path[0]
        if (next_x, next_y) in occupied_positions:
            return False
        
        monster.x = next_x
        monster.y = next_y
        monster.last_move_tick = current_tick
        return True

    def _patrol_waypoint(
        self,
        monster: Monster,
        tiles: list[list[int]],
        occupied_positions: set[tuple[int, int]],
        current_tick: int,
        *,
        rooms: Optional[list[Room]] = None,
    ) -> bool:
        """
        Move monster toward a patrol waypoint, including corridor exploration.
        
        This enables monsters to patrol through corridors between rooms,
        not just within their current room bounds.
        """
        # Rate limit movement (patrol is slower)
        move_interval = 3 + (hash(monster.id) % 3)  # 3-5 ticks between moves
        if current_tick - monster.last_move_tick < move_interval:
            return False
        
        rooms = rooms or []
        
        # Check if we need a new waypoint
        current_waypoint = getattr(monster, '_patrol_waypoint', None)
        
        if current_waypoint is None or (monster.x, monster.y) == current_waypoint:
            # Generate new waypoint
            current_waypoint = self._generate_patrol_waypoint(
                monster, tiles, rooms
            )
            monster._patrol_waypoint = current_waypoint
        
        if current_waypoint is None:
            return False
        
        # Use A* to find path to waypoint
        astar = AStar(tiles, occupied_positions)
        path = astar.find_path(
            start=(monster.x, monster.y),
            goal=current_waypoint,
            max_iterations=150,
        )
        
        if not path:
            # Can't reach waypoint, clear it and try again next tick
            monster._patrol_waypoint = None
            return False
        
        next_x, next_y = path[0]
        if (next_x, next_y) in occupied_positions:
            return False
        
        monster.x = next_x
        monster.y = next_y
        monster.last_move_tick = current_tick
        return True

    def _generate_patrol_waypoint(
        self,
        monster: Monster,
        tiles: list[list[int]],
        rooms: list[Room],
    ) -> Optional[tuple[int, int]]:
        """
        Generate a new patrol waypoint for the monster.
        
        Strategy:
        1. If in a room, sometimes pick a corridor exit
        2. If in a corridor, pick a connected room or random corridor direction
        3. Otherwise, pick a random walkable position in range
        """
        height = len(tiles)
        width = len(tiles[0]) if tiles else 0
        
        # Check if monster is in a room
        current_room = None
        for room in rooms:
            if room.contains(monster.x, monster.y):
                current_room = room
                break
        
        # If in a room, 40% chance to head to a corridor
        if current_room and random.random() < 0.4:
            corridor = find_nearest_corridor(monster.x, monster.y, tiles, rooms, max_search=8)
            if corridor:
                return corridor
        
        # If in a corridor, 60% chance to head toward a connected room
        if is_in_corridor(monster.x, monster.y, tiles, rooms):
            # Try to find a nearby room entrance
            for room in rooms:
                dx = room.center_x - monster.x
                dy = room.center_y - monster.y
                dist = abs(dx) + abs(dy)
                if dist < 15 and random.random() < 0.6:
                    return (room.center_x, room.center_y)
        
        # Default: random position within patrol range
        search_range = 6
        valid_positions = []
        for dy in range(-search_range, search_range + 1):
            for dx in range(-search_range, search_range + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = monster.x + dx, monster.y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if tiles[ny][nx] == TILE_FLOOR:
                        valid_positions.append((nx, ny))
        
        if valid_positions:
            return random.choice(valid_positions)
        
        return None

    def _can_move_to(
        self,
        x: int,
        y: int,
        tiles: list[list[int]],
        occupied: set[tuple[int, int]],
    ) -> bool:
        """Check if a position is valid for movement."""
        height = len(tiles)
        width = len(tiles[0]) if tiles else 0
        if x < 0 or x >= width or y < 0 or y >= height:
            return False
        if tiles[y][x] != TILE_FLOOR:
            return False
        if (x, y) in occupied:
            return False
        return True

    async def _handle_damage_event(self, event: GameEvent) -> None:
        snapshot = event.data.get("ai_snapshot") if isinstance(event.data, dict) else None
        if not snapshot:
            return
        reward = float(event.data.get("reward", 0.0)) if isinstance(event.data, dict) else 0.0
        if reward == 0.0:
            return
        self._apply_reward_from_snapshot(snapshot, reward)

    async def _handle_monster_death(self, event: GameEvent) -> None:
        self._ensure_initialized()
        
        snapshot = event.data.get("ai_snapshot") if isinstance(event.data, dict) else None
        if not snapshot:
            return
        reward = float(event.data.get("reward", -100.0)) if isinstance(event.data, dict) else -100.0
        self._apply_reward_from_snapshot(snapshot, reward)
        monster_type = snapshot.get("monster_type")
        if monster_type:
            self.species_store.bump_generation(monster_type, settings.ai.max_generation_cap)
            self.species_store.save()

    def _apply_reward_from_snapshot(self, snapshot: dict, reward: float) -> None:
        """
        Apply Q-learning reward from an AI snapshot.
        
        This is called when monsters receive feedback (damage dealt/taken, death).
        The snapshot contains the state-action pair that led to the outcome.
        """
        self._ensure_initialized()
        
        monster_type = snapshot.get("monster_type")
        state_index = snapshot.get("state_index")
        action_name = snapshot.get("action")
        if (
            monster_type not in self.ai_profiles
            or state_index is None
            or not action_name
            or reward == 0.0
        ):
            return
        try:
            action = AIAction[action_name]
        except KeyError:
            return

        profile = self.ai_profiles[monster_type]
        species_record = self.species_store.get_or_create(
            monster_type,
            state_space=profile.decision_engine.encoder.state_space,
            action_count=len(AIAction),
        )

        next_state_index = snapshot.get("next_state_index")
        if next_state_index is None:
            next_state_index, _ = self._encode_state_from_snapshot(
                profile,
                snapshot.get("world_state"),
                snapshot.get("hp_ratio", 1.0),
            )

        # Capture Q-value before learning for history tracking
        q_value_before = float(species_record.q_table[state_index, action.value])
        
        # Apply Q-learning update
        profile.decision_engine.learn(
            species_record.q_table,
            state_index=int(state_index),
            next_state_index=int(next_state_index),
            action=action,
            reward=reward,
        )
        
        # Capture Q-value after learning
        q_value_after = float(species_record.q_table[state_index, action.value])
        
        # Record learning event for history/evolution tracking
        self.species_store.record_learning_event(
            monster_type,
            reward=reward,
            state_index=state_index,
            action=action_name,
            q_value_before=q_value_before,
            q_value_after=q_value_after,
        )
        
        print(f"[MonsterService] Q-learning update for {monster_type}: "
              f"state={state_index}, action={action_name}, reward={reward:.1f}, "
              f"Q: {q_value_before:.3f} -> {q_value_after:.3f}")
        
        self.species_store.save()

    def _encode_state_from_snapshot(
        self,
        profile: MonsterAIProfile,
        world_state: Optional[dict[str, object]],
        hp_ratio: float,
    ) -> tuple[int, tuple[int, int, int, int, int]]:
        world = self._prepare_world_state(world_state)
        return profile.decision_engine.encoder.encode(
            hp_ratio=max(0.0, min(1.0, float(hp_ratio))),
            enemy_count=int(world.get("nearby_enemies", 0)),
            ally_count=int(world.get("nearby_allies", 0)),
            room_type=str(world.get("room_type", "chamber")),
            distance_to_threat=int(world.get("distance_to_threat", 8)),
        )


# Global monster service instance
monster_service = MonsterService()
