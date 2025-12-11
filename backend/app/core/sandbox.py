"""
Sandbox simulation environment for testing monster AI behavior.

This module provides an isolated testing environment for the Q-learning
AI system, allowing observation of monster decisions and combat outcomes
without affecting the main game state.

Features:
- 2-room + corridor map layout
- Monster spawning with full AI profiles
- Virtual threat (player) for triggering combat decisions
- Dice-based combat simulation matching real game mechanics
- Detailed decision logging with Q-value tracking
- Q-learning reward application during simulated combat
"""
import asyncio
import json
import math
import random
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import settings
from ..domain.entities import Monster, Room
from ..domain.intelligence.learning import AIAction
from ..domain.combat.dice import roll_attack, roll_damage
from ..domain.map.tiles import (
    TILE_DOOR_CLOSED,
    TILE_FLOOR,
    TILE_VOID,
    TILE_WALL,
)
from ..services.monster_service import monster_service
from ..db import mongodb_manager
from datetime import datetime


@dataclass
class DecisionLogEntry:
    """A single decision log entry with full AI context."""
    tick: int
    monster_id: str
    monster_type: str
    monster_name: str
    state_index: int
    state_breakdown: dict[str, Any]
    q_values: dict[str, float]
    action: str
    explored: bool
    confidence: float
    position: tuple[int, int]
    hp_ratio: float


@dataclass
class CombatLogEntry:
    """A combat exchange log entry."""
    tick: int
    attacker: str  # "monster" or "threat"
    attacker_id: str
    target_id: str
    attack_roll: int
    hit: bool
    is_crit: bool
    damage: int
    reward: float
    description: str


@dataclass
class SandboxThreat:
    """Virtual player/threat entity for AI testing."""
    x: int
    y: int
    symbol: str = "@"
    color: str = "#ffff00"
    hp: int = 20
    max_hp: int = 20
    ac: int = 14
    str_mod: int = 2
    damage_dice: str = "1d8"


@dataclass
class SandboxState:
    """Complete sandbox simulation state."""
    tiles: list[list[int]]
    width: int
    height: int
    rooms: list[dict]
    monsters: dict[str, Monster]
    threat: Optional[SandboxThreat]
    tick: int
    running: bool
    speed_ms: int
    decision_log: deque
    combat_log: deque
    combat_enabled: bool = True  # Whether to simulate combat when adjacent


class SandboxManager:
    """
    Manages an isolated sandbox environment for testing monster AI.
    
    Features:
    - 2-room + corridor map layout
    - Monster spawning and removal
    - Virtual threat (player) placement and movement
    - Manual or automatic tick stepping
    - Detailed decision logging
    - State persistence
    """
    
    _instance: Optional["SandboxManager"] = None
    
    def __new__(cls) -> "SandboxManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.state: Optional[SandboxState] = None
        self.save_path = settings.storage.save_path / "sandbox.json"
        self._run_task: Optional[asyncio.Task] = None
        self._ws_connections: set = set()
        self._initialized = True
        
        # Try to load existing state
        self._load()
    
    def _generate_map(self) -> tuple[list[list[int]], list[Room]]:
        """Generate a 2-room + corridor map layout."""
        # Map dimensions
        width = 40
        height = 25
        
        # Initialize with void
        tiles = [[TILE_VOID for _ in range(width)] for _ in range(height)]
        rooms = []
        
        # Room 1: Left side (14x14 interior + walls)
        room1_x, room1_y = 1, 2
        room1_w, room1_h = 14, 14
        self._carve_room(tiles, room1_x, room1_y, room1_w, room1_h)
        rooms.append(Room(
            id="room_1",
            x=room1_x,
            y=room1_y,
            width=room1_w,
            height=room1_h,
            room_type="chamber",
            name="West Chamber",
            description="A testing chamber on the west side."
        ))
        
        # Room 2: Right side (14x14 interior + walls)
        room2_x, room2_y = 25, 2
        room2_w, room2_h = 14, 14
        self._carve_room(tiles, room2_x, room2_y, room2_w, room2_h)
        rooms.append(Room(
            id="room_2",
            x=room2_x,
            y=room2_y,
            width=room2_w,
            height=room2_h,
            room_type="chamber",
            name="East Chamber",
            description="A testing chamber on the east side."
        ))
        
        # Corridor connecting rooms (horizontal, 3 tiles wide)
        corridor_y = 8  # Center vertically
        corridor_start_x = room1_x + room1_w
        corridor_end_x = room2_x
        
        # Carve corridor walls and floor
        for x in range(corridor_start_x, corridor_end_x):
            tiles[corridor_y - 1][x] = TILE_WALL  # Top wall
            tiles[corridor_y][x] = TILE_FLOOR     # Middle floor
            tiles[corridor_y + 1][x] = TILE_WALL  # Bottom wall
        
        # Open the walls where corridor connects to rooms (no doors)
        tiles[corridor_y][corridor_start_x - 1] = TILE_FLOOR  # Room 1 side
        tiles[corridor_y][corridor_end_x] = TILE_FLOOR        # Room 2 side
        
        return tiles, rooms
    
    def _carve_room(
        self,
        tiles: list[list[int]],
        x: int,
        y: int,
        width: int,
        height: int
    ) -> None:
        """Carve a room with walls and floor."""
        for dy in range(height):
            for dx in range(width):
                px, py = x + dx, y + dy
                if dx == 0 or dx == width - 1 or dy == 0 or dy == height - 1:
                    tiles[py][px] = TILE_WALL
                else:
                    tiles[py][px] = TILE_FLOOR
    
    def create(self) -> dict:
        """Create/reset the sandbox with a fresh map."""
        tiles, rooms = self._generate_map()
        
        self.state = SandboxState(
            tiles=tiles,
            width=len(tiles[0]) if tiles else 0,
            height=len(tiles),
            rooms=[self._room_to_dict(r) for r in rooms],
            monsters={},
            threat=None,
            tick=0,
            running=False,
            speed_ms=500,
            decision_log=deque(maxlen=50),
            combat_log=deque(maxlen=100),
            combat_enabled=True,
        )
        
        self._save()
        return self.get_state()
    
    def get_state(self, include_static: bool = True, log_limit: int = 0) -> dict:
        """Get the current sandbox state as a dict.
        
        Args:
            include_static: If False, omit tiles/rooms for delta updates
            log_limit: If > 0, only include last N log entries (for delta updates)
        """
        if not self.state:
            return self.create()
        
        # Get log entries (optionally limited for delta updates)
        decision_log = list(self.state.decision_log)
        combat_log = list(self.state.combat_log)
        if log_limit > 0:
            decision_log = decision_log[-log_limit:] if decision_log else []
            combat_log = combat_log[-log_limit:] if combat_log else []
        
        result = {
            "monsters": {
                mid: self._monster_to_dict(m)
                for mid, m in self.state.monsters.items()
            },
            "threat": {
                "x": self.state.threat.x,
                "y": self.state.threat.y,
                "symbol": self.state.threat.symbol,
                "color": self.state.threat.color,
                "hp": self.state.threat.hp,
                "max_hp": self.state.threat.max_hp,
                "ac": self.state.threat.ac,
            } if self.state.threat else None,
            "tick": self.state.tick,
            "running": self.state.running,
            "speed_ms": self.state.speed_ms,
            "combat_enabled": bool(self.state.combat_enabled),
            "decision_log": [self._log_entry_to_dict(e) for e in decision_log],
            "combat_log": [self._combat_log_to_dict(e) for e in combat_log],
        }
        
        if include_static:
            result["tiles"] = self.state.tiles
            result["width"] = self.state.width
            result["height"] = self.state.height
            result["rooms"] = self.state.rooms
        
        return result
    
    def spawn_monster(self, monster_type: str, x: int, y: int) -> Optional[dict]:
        """Spawn a monster at the specified position."""
        if not self.state:
            self.create()
        
        # Validate position
        if not self._is_valid_spawn(x, y):
            return None
        
        # Find which room this position is in
        room_id = self._get_room_at(x, y) or "sandbox"
        
        # Create monster using monster service
        monster = monster_service.create_monster(
            monster_type=monster_type,
            x=x,
            y=y,
            room_id=room_id
        )
        
        if not monster:
            return None
        
        self.state.monsters[monster.id] = monster
        self._save()
        
        return self._monster_to_dict(monster)
    
    def remove_monster(self, monster_id: str) -> bool:
        """Remove a monster from the sandbox."""
        if not self.state or monster_id not in self.state.monsters:
            return False
        
        del self.state.monsters[monster_id]
        
        # Clean up memory in monster service
        if monster_id in monster_service.monster_memories:
            del monster_service.monster_memories[monster_id]
        
        self._save()
        return True
    
    def set_monster_hp(self, monster_id: str, hp: int) -> bool:
        """Set a monster's current HP."""
        if not self.state or monster_id not in self.state.monsters:
            return False
        
        monster = self.state.monsters[monster_id]
        monster.stats.hp = max(1, min(hp, monster.stats.max_hp))
        self._save()
        return True
    
    def spawn_threat(self, x: int, y: int) -> Optional[dict]:
        """Spawn or move the threat to a position."""
        if not self.state:
            self.create()
        
        if not self._is_valid_spawn(x, y):
            return None
        
        self.state.threat = SandboxThreat(x=x, y=y)
        self._save()
        
        return {
            "x": self.state.threat.x,
            "y": self.state.threat.y,
            "symbol": self.state.threat.symbol,
            "color": self.state.threat.color,
            "hp": self.state.threat.hp,
            "max_hp": self.state.threat.max_hp,
            "ac": self.state.threat.ac,
        }
    
    def set_combat_enabled(self, enabled: bool) -> bool:
        """Enable or disable combat simulation."""
        if not self.state:
            self.create()
        self.state.combat_enabled = enabled
        self._save()
        return True
    
    def reset_threat_hp(self) -> bool:
        """Reset threat HP to max."""
        if not self.state or not self.state.threat:
            return False
        self.state.threat.hp = self.state.threat.max_hp
        self._save()
        return True
    
    def move_threat(self, direction: Optional[str] = None, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Move the threat by direction or to absolute position."""
        if not self.state or not self.state.threat:
            return False
        
        if direction:
            dx, dy = 0, 0
            if direction == "up":
                dy = -1
            elif direction == "down":
                dy = 1
            elif direction == "left":
                dx = -1
            elif direction == "right":
                dx = 1
            else:
                return False
            
            new_x = self.state.threat.x + dx
            new_y = self.state.threat.y + dy
        elif x is not None and y is not None:
            new_x, new_y = x, y
        else:
            return False
        
        if not self._is_walkable(new_x, new_y):
            return False
        
        self.state.threat.x = new_x
        self.state.threat.y = new_y
        self._save()
        return True
    
    def remove_threat(self) -> bool:
        """Remove the threat from the sandbox."""
        if not self.state:
            return False
        
        self.state.threat = None
        self._save()
        return True
    
    def step(self, count: int = 1) -> list[dict]:
        """Advance the simulation by N ticks and return new decision logs."""
        if not self.state:
            self.create()
        
        new_logs = []
        
        for _ in range(count):
            self.state.tick += 1
            logs = self._update_monsters()
            new_logs.extend(logs)
        
        self._save()
        return new_logs
    
    def set_running(self, running: bool, speed_ms: Optional[int] = None) -> dict:
        """Start or stop auto-run mode."""
        if not self.state:
            self.create()
        
        self.state.running = running
        if speed_ms is not None:
            self.state.speed_ms = max(100, min(2000, speed_ms))
        
        self._save()
        
        # Manage the async run task
        if running:
            if self._run_task is None or self._run_task.done():
                self._run_task = asyncio.create_task(self._auto_run_loop())
        else:
            if self._run_task and not self._run_task.done():
                self._run_task.cancel()
        
        return {"running": self.state.running, "speed_ms": self.state.speed_ms}
    
    async def _auto_run_loop(self):
        """Auto-run loop that steps and broadcasts state."""
        try:
            while self.state and self.state.running:
                new_logs = self.step(1)
                
                # Broadcast to WebSocket connections
                await self._broadcast_state(new_logs)
                
                await asyncio.sleep(self.state.speed_ms / 1000.0)
        except asyncio.CancelledError:
            pass
    
    async def _broadcast_state(self, new_logs: list[dict]):
        """Broadcast state update to all connected WebSocket clients.
        
        Sends delta updates (without static tiles/rooms) for efficiency.
        """
        if not self._ws_connections:
            return
        
        # Send delta update without static data (tiles, rooms)
        # Only include last 10 log entries in delta updates
        message = json.dumps({
            "type": "sandbox_update",
            "state": self.get_state(include_static=False, log_limit=10),
            "new_logs": new_logs,
        })
        
        disconnected = set()
        for ws in self._ws_connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        
        self._ws_connections -= disconnected
    
    def register_ws(self, websocket) -> None:
        """Register a WebSocket connection for updates."""
        self._ws_connections.add(websocket)
    
    def unregister_ws(self, websocket) -> None:
        """Unregister a WebSocket connection."""
        self._ws_connections.discard(websocket)
    
    def _update_monsters(self) -> list[dict]:
        """
        Update all monsters and simulate combat.
        
        For each monster:
        1. Build world state including threat distance
        2. Get AI decision (attack, defend, flee, etc.)
        3. If adjacent to threat and combat enabled, simulate combat exchange
        4. Apply Q-learning rewards based on outcomes
        """
        if not self.state:
            return []
        
        new_logs = []
        occupied = self._get_occupied_positions()
        
        for monster_id, monster in list(self.state.monsters.items()):
            # Skip dead monsters
            if monster.stats.hp <= 0:
                continue
            
            # Build world state
            world_state = self._build_world_state(monster)
            
            # Get room bounds for this monster
            room_bounds = self._get_room_bounds(monster.room_id)
            if not room_bounds:
                room_bounds = (0, 0, self.state.width, self.state.height)
            
            # Create log callback to capture decision
            log_entry = None
            
            def log_callback(data: dict):
                nonlocal log_entry
                log_entry = DecisionLogEntry(
                    tick=self.state.tick,
                    monster_id=monster.id,
                    monster_type=monster.monster_type,
                    monster_name=monster.name,
                    state_index=data.get("state_index", 0),
                    state_breakdown=data.get("state_breakdown", {}),
                    q_values=data.get("q_values", {}),
                    action=data.get("action", "UNKNOWN"),
                    explored=data.get("explored", False),
                    confidence=data.get("confidence", 0.0),
                    position=(monster.x, monster.y),
                    hp_ratio=monster.stats.hp / monster.stats.max_hp,
                )
            
            # Update monster with log callback
            monster_service.update_monster(
                monster=monster,
                room_bounds=room_bounds,
                tiles=self.state.tiles,
                occupied_positions=occupied,
                current_tick=self.state.tick,
                world_state=world_state,
                log_callback=log_callback,
            )
            
            # If we got a log entry, add it
            if log_entry:
                self.state.decision_log.append(log_entry)
                new_logs.append(self._log_entry_to_dict(log_entry))
                
                # Simulate combat if adjacent to threat and combat is enabled
                if self.state.combat_enabled and self.state.threat and self._is_adjacent(monster, self.state.threat):
                    combat_logs = self._simulate_combat_exchange(monster, log_entry)
                    new_logs.extend(combat_logs)
            
            # Update occupied positions
            occupied.add((monster.x, monster.y))
        
        # Remove dead monsters and respawn them
        dead_monsters = [mid for mid, m in self.state.monsters.items() if m.stats.hp <= 0]
        for mid in dead_monsters:
            monster = self.state.monsters[mid]
            # Log death
            death_log = {
                "tick": self.state.tick,
                "type": "death",
                "monster_id": mid,
                "monster_name": monster.name,
                "description": f"☠️ {monster.name} has been slain!",
            }
            new_logs.append(death_log)
            
            # Respawn at original room with full HP
            monster.stats.hp = monster.stats.max_hp
            # Find a valid spawn position in the same room
            room_bounds = self._get_room_bounds(monster.room_id)
            if room_bounds:
                rx, ry, rw, rh = room_bounds
                for dy in range(1, rh - 1):
                    for dx in range(1, rw - 1):
                        px, py = rx + dx, ry + dy
                        if self._is_valid_spawn(px, py):
                            monster.x, monster.y = px, py
                            break
        
        # Reset dead threat
        if self.state.threat and self.state.threat.hp <= 0:
            new_logs.append({
                "tick": self.state.tick,
                "type": "threat_death",
                "description": "💀 Threat defeated! Respawning...",
            })
            self.state.threat.hp = self.state.threat.max_hp
        
        return new_logs
    
    def _is_adjacent(self, monster: Monster, threat: SandboxThreat) -> bool:
        """Check if monster is adjacent to threat (Chebyshev distance <= 1)."""
        dx = abs(monster.x - threat.x)
        dy = abs(monster.y - threat.y)
        return dx <= 1 and dy <= 1 and (dx + dy) > 0
    
    def _simulate_combat_exchange(
        self,
        monster: Monster,
        decision: DecisionLogEntry,
    ) -> list[dict]:
        """
        Simulate a single combat exchange between monster and threat.
        
        Uses the same dice mechanics as the real game:
        - roll_attack() for attack rolls vs AC
        - roll_damage() for damage on hit
        
        Returns list of combat log dicts for the UI.
        """
        combat_logs = []
        
        if not self.state or not self.state.threat:
            return combat_logs
        
        threat = self.state.threat
        action = decision.action
        
        # Build AI snapshot for Q-learning rewards
        ai_snapshot = {
            "monster_type": monster.monster_type,
            "state_index": decision.state_index,
            "action": action,
            "world_state": decision.state_breakdown,
            "hp_ratio": monster.stats.hp / monster.stats.max_hp,
        }
        
        # Process based on action
        if action in ("ATTACK_AGGRESSIVE", "ATTACK_DEFENSIVE", "AMBUSH"):
            # Monster attacks threat
            attack_bonus = monster.stats.get_modifier(monster.stats.str)
            attack_roll, hit, is_crit = roll_attack(attack_bonus, threat.ac)
            
            damage = 0
            reward = 0.0
            
            if hit:
                monster_damage = f"1d{6 + int(monster.stats.challenge_rating * 2)}"
                dmg_result = roll_damage(monster_damage, is_critical=is_crit)
                damage = dmg_result.total
                threat.hp = max(0, threat.hp - damage)
                reward = float(damage)  # Positive reward for dealing damage
                
                desc = f"🗡️ {monster.name} {'CRITS' if is_crit else 'hits'} for {damage} damage!"
            else:
                reward = -1.0  # Small penalty for missing
                desc = f"⚔️ {monster.name} misses!"
            
            combat_entry = CombatLogEntry(
                tick=self.state.tick,
                attacker="monster",
                attacker_id=monster.id,
                target_id="threat",
                attack_roll=attack_roll.total,
                hit=hit,
                is_crit=is_crit,
                damage=damage,
                reward=reward,
                description=desc,
            )
            self.state.combat_log.append(combat_entry)
            combat_logs.append(self._combat_log_to_dict(combat_entry))
            
            # Apply reward via monster_service
            self._apply_reward(ai_snapshot, reward)
            
            # Counter-attack from threat if still alive
            if threat.hp > 0 and action != "ATTACK_DEFENSIVE":
                counter_logs = self._threat_attacks_monster(monster, ai_snapshot)
                combat_logs.extend(counter_logs)
        
        elif action == "DEFEND":
            # Monster defends - no attack, but reduces incoming damage
            # Threat attacks with disadvantage (simulated as -2)
            counter_logs = self._threat_attacks_monster(monster, ai_snapshot, defend_bonus=2)
            combat_logs.extend(counter_logs)
            
            # Small positive reward for surviving a round while defending
            if monster.stats.hp > 0:
                self._apply_reward(ai_snapshot, 1.0)
        
        elif action == "FLEE":
            # Monster tries to flee - threat gets opportunity attack
            counter_logs = self._threat_attacks_monster(monster, ai_snapshot, opportunity=True)
            combat_logs.extend(counter_logs)
            
            # Reward based on survival
            if monster.stats.hp > 0:
                self._apply_reward(ai_snapshot, 2.0)  # Reward for successful flee
            else:
                self._apply_reward(ai_snapshot, -50.0)  # Penalty for dying while fleeing
        
        elif action == "CALL_ALLIES":
            # No immediate combat effect, but slight positive reward
            self._apply_reward(ai_snapshot, 0.5)
            combat_logs.append({
                "tick": self.state.tick,
                "type": "call",
                "description": f"📢 {monster.name} calls for allies!",
            })
        
        elif action == "PATROL":
            # Patrolling while adjacent - neutral/slight penalty
            self._apply_reward(ai_snapshot, -0.5)
        
        return combat_logs
    
    def _threat_attacks_monster(
        self,
        monster: Monster,
        ai_snapshot: dict,
        defend_bonus: int = 0,
        opportunity: bool = False,
    ) -> list[dict]:
        """
        Threat attacks monster.
        
        Args:
            monster: The monster being attacked
            ai_snapshot: AI state for reward application
            defend_bonus: Extra AC from defending
            opportunity: Whether this is an opportunity attack
        """
        combat_logs = []
        
        if not self.state or not self.state.threat:
            return combat_logs
        
        threat = self.state.threat
        effective_ac = monster.stats.ac + defend_bonus
        
        attack_roll, hit, is_crit = roll_attack(threat.str_mod, effective_ac)
        
        damage = 0
        reward = 0.0
        
        if hit:
            dmg_result = roll_damage(threat.damage_dice, is_critical=is_crit)
            damage = dmg_result.total
            monster.stats.hp = max(0, monster.stats.hp - damage)
            reward = -float(damage)  # Negative reward for taking damage
            
            prefix = "⚡ Opportunity attack!" if opportunity else "🎯"
            desc = f"{prefix} Threat {'CRITS' if is_crit else 'hits'} {monster.name} for {damage}!"
            
            # Extra penalty if killed
            if monster.stats.hp <= 0:
                reward = -100.0  # Heavy death penalty
                desc += " ☠️"
        else:
            reward = 1.0  # Small reward for avoiding damage
            desc = f"🛡️ {monster.name} avoids the attack!"
        
        combat_entry = CombatLogEntry(
            tick=self.state.tick,
            attacker="threat",
            attacker_id="threat",
            target_id=monster.id,
            attack_roll=attack_roll.total,
            hit=hit,
            is_crit=is_crit,
            damage=damage,
            reward=reward,
            description=desc,
        )
        self.state.combat_log.append(combat_entry)
        combat_logs.append(self._combat_log_to_dict(combat_entry))
        
        # Apply reward for taking/avoiding damage
        self._apply_reward(ai_snapshot, reward)
        
        return combat_logs
    
    def _apply_reward(self, ai_snapshot: dict, reward: float) -> None:
        """Apply Q-learning reward through monster_service."""
        if reward == 0.0:
            return
        
        # Use the monster service's internal method to apply the reward
        monster_service._apply_reward_from_snapshot(ai_snapshot, reward)
    
    def _combat_log_to_dict(self, entry: CombatLogEntry) -> dict:
        """Convert CombatLogEntry to dict."""
        return {
            "tick": entry.tick,
            "type": "combat",
            "attacker": entry.attacker,
            "attacker_id": entry.attacker_id,
            "target_id": entry.target_id,
            "attack_roll": entry.attack_roll,
            "hit": entry.hit,
            "is_crit": entry.is_crit,
            "damage": entry.damage,
            "reward": entry.reward,
            "description": entry.description,
        }
    
    def _build_world_state(self, monster: Monster) -> dict:
        """Build world state for a monster's decision."""
        state = {
            "room_type": "chamber",
            "nearby_enemies": 0,
            "nearby_allies": 0,
            "distance_to_threat": 10,
        }
        
        # Count nearby allies (other monsters in same room)
        for other_id, other in self.state.monsters.items():
            if other_id != monster.id and other.room_id == monster.room_id:
                state["nearby_allies"] += 1
        
        # Calculate distance to threat if present
        if self.state.threat:
            dx = abs(monster.x - self.state.threat.x)
            dy = abs(monster.y - self.state.threat.y)
            distance = max(dx, dy)  # Chebyshev distance
            state["distance_to_threat"] = distance
            
            # Count threat as enemy if close enough
            if distance <= 5:
                state["nearby_enemies"] = 1
        
        # Get room type
        room_id = monster.room_id
        for room in self.state.rooms:
            if room["id"] == room_id:
                state["room_type"] = room.get("room_type", "chamber")
                break
        
        return state
    
    def _get_room_bounds(self, room_id: str) -> Optional[tuple[int, int, int, int]]:
        """Get (x, y, width, height) for a room."""
        for room in self.state.rooms:
            if room["id"] == room_id:
                return (room["x"], room["y"], room["width"], room["height"])
        return None
    
    def _get_occupied_positions(self) -> set[tuple[int, int]]:
        """Get all occupied positions (monsters + threat)."""
        occupied = set()
        
        for monster in self.state.monsters.values():
            occupied.add((monster.x, monster.y))
        
        if self.state.threat:
            occupied.add((self.state.threat.x, self.state.threat.y))
        
        return occupied
    
    def _is_valid_spawn(self, x: int, y: int) -> bool:
        """Check if a position is valid for spawning."""
        if not self.state:
            return False
        
        if not self._is_walkable(x, y):
            return False
        
        # Check not occupied
        occupied = self._get_occupied_positions()
        return (x, y) not in occupied
    
    def _is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable."""
        if not self.state:
            return False
        
        if x < 0 or x >= self.state.width or y < 0 or y >= self.state.height:
            return False
        
        return self.state.tiles[y][x] == TILE_FLOOR
    
    def _get_room_at(self, x: int, y: int) -> Optional[str]:
        """Get the room ID at a position, if any."""
        if not self.state:
            return None
        
        for room in self.state.rooms:
            rx, ry = room["x"], room["y"]
            rw, rh = room["width"], room["height"]
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return room["id"]
        
        return None
    
    def _room_to_dict(self, room: Room) -> dict:
        """Convert a Room to a dict."""
        return {
            "id": room.id,
            "x": room.x,
            "y": room.y,
            "width": room.width,
            "height": room.height,
            "room_type": room.room_type,
            "name": room.name,
            "description": room.description,
        }
    
    def _monster_to_dict(self, monster: Monster) -> dict:
        """Convert a Monster to a dict for the API."""
        return {
            "id": monster.id,
            "monster_type": monster.monster_type,
            "name": monster.name,
            "x": monster.x,
            "y": monster.y,
            "room_id": monster.room_id,
            "symbol": monster.symbol,
            "color": monster.color,
            "hp": monster.stats.hp,
            "max_hp": monster.stats.max_hp,
            "behavior": monster.behavior.value if monster.behavior else "static",
            "intelligence": {
                "generation": monster.intelligence_state.generation if monster.intelligence_state else 0,
                "last_action": monster.intelligence_state.last_action if monster.intelligence_state else None,
                "last_state_index": monster.intelligence_state.last_state_index if monster.intelligence_state else None,
            } if monster.intelligence_state else None,
        }
    
    def _log_entry_to_dict(self, entry: DecisionLogEntry) -> dict:
        """Convert a DecisionLogEntry to a dict."""
        return {
            "tick": entry.tick,
            "monster_id": entry.monster_id,
            "monster_type": entry.monster_type,
            "monster_name": entry.monster_name,
            "state_index": entry.state_index,
            "state_breakdown": entry.state_breakdown,
            "q_values": entry.q_values,
            "action": entry.action,
            "explored": entry.explored,
            "confidence": entry.confidence,
            "position": list(entry.position),
            "hp_ratio": entry.hp_ratio,
        }
    
    def _save(self) -> None:
        """Save sandbox state (sync wrapper)."""
        if not self.state:
            return

        # Try MongoDB first if available
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._async_save())
                    return
                else:
                    loop.run_until_complete(self._async_save())
                    return
            except Exception as e:
                print(f"[SandboxManager] MongoDB save failed, falling back to JSON: {e}")

        # Fallback to JSON
        self._save_to_json()

    def _save_to_json(self) -> None:
        """Save sandbox state to JSON file."""
        if not self.state:
            return

        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "tiles": self.state.tiles,
                "width": self.state.width,
                "height": self.state.height,
                "rooms": self.state.rooms,
                "monsters": {
                    mid: {
                        "monster_type": m.monster_type,
                        "x": m.x,
                        "y": m.y,
                        "room_id": m.room_id,
                        "hp": m.stats.hp,
                    }
                    for mid, m in self.state.monsters.items()
                },
                "threat": {
                    "x": self.state.threat.x,
                    "y": self.state.threat.y,
                    "hp": self.state.threat.hp,
                    "max_hp": self.state.threat.max_hp,
                    "ac": self.state.threat.ac,
                } if self.state.threat else None,
                "tick": self.state.tick,
                "speed_ms": self.state.speed_ms,
                "combat_enabled": self.state.combat_enabled,
            }

            with open(self.save_path, "w") as f:
                json.dump(data, f, indent=2)
            print("[SandboxManager] Saved sandbox state to JSON")
        except Exception as e:
            print(f"[SandboxManager] Failed to save to JSON: {e}")

    async def _async_save(self) -> None:
        """Save sandbox state to MongoDB."""
        if not self.state:
            return

        try:
            data = {
                "singleton": "sandbox",
                "tiles": self.state.tiles,
                "width": self.state.width,
                "height": self.state.height,
                "rooms": self.state.rooms,
                "monsters": {
                    mid: {
                        "monster_type": m.monster_type,
                        "x": m.x,
                        "y": m.y,
                        "room_id": m.room_id,
                        "hp": m.stats.hp,
                    }
                    for mid, m in self.state.monsters.items()
                },
                "threat": {
                    "x": self.state.threat.x,
                    "y": self.state.threat.y,
                    "hp": self.state.threat.hp,
                    "max_hp": self.state.threat.max_hp,
                    "ac": self.state.threat.ac,
                } if self.state.threat else None,
                "tick": self.state.tick,
                "speed_ms": self.state.speed_ms,
                "combat_enabled": self.state.combat_enabled,
                "last_updated": datetime.now()
            }

            await mongodb_manager.db.sandbox.update_one(
                {"singleton": "sandbox"},
                {"$set": data},
                upsert=True
            )
            print("[SandboxManager] Saved sandbox state to MongoDB")
        except Exception as e:
            print(f"[SandboxManager] Failed to save to MongoDB: {e}")
    
    def _load(self) -> None:
        """Load sandbox state (sync wrapper)."""
        # Try MongoDB first if available
        if settings.mongodb.is_enabled and mongodb_manager.is_connected:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._async_load())
                    # Also try JSON as immediate fallback
                    if self.save_path.exists():
                        self._load_from_json()
                    return
                else:
                    loop.run_until_complete(self._async_load())
                    if self.state:  # Successfully loaded from MongoDB
                        return
            except Exception as e:
                print(f"[SandboxManager] MongoDB load failed, falling back to JSON: {e}")

        # Fallback to JSON
        if self.save_path.exists():
            self._load_from_json()

    def _load_from_json(self) -> None:
        """Load sandbox state from JSON file."""
        if not self.save_path.exists():
            return

        try:
            with open(self.save_path, "r") as f:
                data = json.load(f)

            self._reconstruct_state_from_data(data)
            print(f"[SandboxManager] Loaded sandbox state from JSON")
        except Exception as e:
            print(f"[SandboxManager] Failed to load from JSON: {e}")

    async def _async_load(self) -> None:
        """Load sandbox state from MongoDB."""
        try:
            doc = await mongodb_manager.db.sandbox.find_one({"singleton": "sandbox"})

            if not doc:
                return

            # Remove MongoDB-specific fields
            doc.pop("_id", None)
            doc.pop("singleton", None)
            doc.pop("last_updated", None)

            self._reconstruct_state_from_data(doc)
            print("[SandboxManager] Loaded sandbox state from MongoDB")
        except Exception as e:
            print(f"[SandboxManager] Failed to load from MongoDB: {e}")

    def _reconstruct_state_from_data(self, data: dict) -> None:
        """Reconstruct sandbox state from data dict (used by both JSON and MongoDB loaders)."""
        # Reconstruct monsters
        monsters = {}
        for mid, mdata in data.get("monsters", {}).items():
            monster = monster_service.create_monster(
                monster_type=mdata["monster_type"],
                x=mdata["x"],
                y=mdata["y"],
                room_id=mdata["room_id"]
            )
            if monster:
                monster.id = mid  # Restore original ID
                monster.stats.hp = mdata.get("hp", monster.stats.max_hp)
                monsters[mid] = monster

        # Reconstruct threat
        threat = None
        if data.get("threat"):
            threat_data = data["threat"]
            threat = SandboxThreat(
                x=threat_data["x"],
                y=threat_data["y"],
                hp=threat_data.get("hp", 20),
                max_hp=threat_data.get("max_hp", 20),
                ac=threat_data.get("ac", 14),
            )

        self.state = SandboxState(
            tiles=data["tiles"],
            width=data["width"],
            height=data["height"],
            rooms=data["rooms"],
            monsters=monsters,
            threat=threat,
            tick=data.get("tick", 0),
            running=False,  # Never auto-start
            speed_ms=data.get("speed_ms", 500),
            decision_log=deque(maxlen=50),
            combat_log=deque(maxlen=100),
            combat_enabled=data.get("combat_enabled", True),
        )


# Global sandbox manager instance
sandbox_manager = SandboxManager()