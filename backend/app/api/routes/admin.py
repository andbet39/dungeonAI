"""
Admin API endpoints for DungeonAI.
"""
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...core import game_manager
from ...core.game_registry import game_registry
from ...core.sandbox import sandbox_manager
from ...services import storage_service, monster_service
from ...domain import Room
from ...domain.intelligence.learning import AIAction

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RegenerateMapRequest(BaseModel):
    """Request model for map regeneration."""
    width: int = 80
    height: int = 50
    room_count: int = 15
    seed: Optional[int] = None


@router.post("/regenerate-map")
async def regenerate_map(request: RegenerateMapRequest):
    """
    Regenerate the dungeon map.
    Disconnects all players and generates a fresh map with AI descriptions.
    """
    result = await game_manager.regenerate_map(
        width=request.width,
        height=request.height,
        room_count=request.room_count,
        seed=request.seed
    )
    return result


@router.get("/maps")
async def list_saved_maps():
    """List all saved game files."""
    saves = storage_service.list_saves()
    return {"saves": saves}


@router.post("/load-map/{save_id}")
async def load_map(save_id: str):
    """Load a saved game state."""
    game_state = await storage_service.load_game(save_id)
    if not game_state:
        return {"success": False, "error": "Save not found"}
    
    # Notify current players
    await game_manager._broadcast_message({
        "type": "map_regenerating",
        "message": "Loading saved dungeon..."
    })
    
    # Clear current connections
    old_player_count = len(game_manager.players)
    game_manager.players = {}
    game_manager.connections = {}
    
    # Restore state
    map_data = game_state.get("map", {})
    game_manager.width = map_data.get("width", 80)
    game_manager.height = map_data.get("height", 50)
    game_manager.tiles = map_data.get("tiles", [])
    game_manager.spawn_x = map_data.get("spawn_x", 1)
    game_manager.spawn_y = map_data.get("spawn_y", 1)
    game_manager.map_seed = map_data.get("seed")
    
    rooms_data = game_state.get("rooms", [])
    game_manager.rooms = [Room.from_dict(r) for r in rooms_data]
    
    return {
        "success": True,
        "width": game_manager.width,
        "height": game_manager.height,
        "room_count": len(game_manager.rooms),
        "players_disconnected": old_player_count
    }


@router.post("/save")
async def force_save():
    """Force save the current game state."""
    success = await game_manager.force_save()
    return {"success": success}


@router.delete("/maps/{save_id}")
async def delete_save(save_id: str):
    """Delete a saved game file."""
    if save_id == "current":
        return {"success": False, "error": "Cannot delete current save"}
    
    success = await storage_service.delete_save(save_id)
    return {"success": success}


@router.post("/backup")
async def create_backup():
    """Create a backup of the current game state."""
    backup_id = await storage_service.create_backup()
    return {"success": backup_id is not None, "backup_id": backup_id}


# ================= AI Debug Endpoints =================


@router.get("/ai/profiles")
async def list_ai_profiles():
    """List all configured AI profiles for monster types."""
    profiles = {}
    for monster_type, profile in monster_service.ai_profiles.items():
        profiles[monster_type] = {
            "personality": {
                "aggression": profile.personality.aggression,
                "caution": profile.personality.caution,
                "cunning": profile.personality.cunning,
                "pack_mentality": profile.personality.pack_mentality,
            },
            "memory_capacity": profile.memory_capacity,
            "memory_decay": profile.memory_decay,
            "decision_cooldown_ticks": profile.decision_cooldown_ticks,
            "preferred_tactics": profile.preferred_tactics,
            "learning_rate": profile.decision_engine.agent.config.learning_rate,
            "exploration_rate": profile.decision_engine.agent.config.exploration_rate,
        }
    return {"profiles": profiles}


@router.get("/ai/species-knowledge")
async def get_species_knowledge():
    """Get current species knowledge store (generations and Q-table stats)."""
    from ...domain.intelligence.learning import SCHEMA_VERSION
    
    knowledge = {}
    for species, record in monster_service.species_store._data.items():
        q_table = record.q_table
        knowledge[species] = {
            "generation": record.generation,
            "total_learning_steps": record.total_learning_steps,
            "q_table_shape": list(q_table.shape),
            "q_table_mean": float(q_table.mean()),
            "q_table_max": float(q_table.max()),
            "q_table_min": float(q_table.min()),
            "q_table_nonzero": int((q_table != 0).sum()),
            "history_count": len(record.history),
        }
    return {
        "species": knowledge,
        "schema_version": SCHEMA_VERSION,
    }


@router.get("/ai/species-history/{species}")
async def get_species_history(species: str, limit: int = Query(100, ge=1, le=500)):
    """
    Get learning history for a species.
    
    Returns recent Q-learning events for evolution visualization.
    Each entry contains timestamp, reward, state, action, and Q-value changes.
    
    History is stored in separate files per species for efficiency.
    """
    # Use limit parameter directly - get_history now handles it
    history = monster_service.species_store.get_history(species, limit=limit)
    if not history:
        return {"species": species, "history": [], "total": 0}
    
    return {
        "species": species,
        "history": [
            {
                "timestamp": h.timestamp,
                "generation": h.generation,
                "reward": h.reward,
                "state_index": h.state_index,
                "action": h.action,
                "q_value_before": h.q_value_before,
                "q_value_after": h.q_value_after,
                "q_delta": h.q_value_after - h.q_value_before,
            }
            for h in history
        ],
        "total": len(history),
    }


@router.get("/ai/q-table/{species}")
async def get_q_table(species: str):
    """
    Get full Q-table for a species.
    
    Returns the Q-table as a 2D array with action names and state descriptions.
    Useful for detailed analysis and debugging.
    """
    record = monster_service.species_store.records.get(species)
    if not record:
        return {"error": "Species not found"}
    
    action_names = [a.name for a in AIAction]
    q_table = record.q_table.tolist()
    
    # Find states with significant Q-values
    significant_states = []
    for state_idx, row in enumerate(record.q_table):
        if any(abs(v) > 0.01 for v in row):
            significant_states.append({
                "state_index": state_idx,
                "q_values": dict(zip(action_names, row.tolist())),
                "best_action": action_names[int(row.argmax())],
                "max_q": float(row.max()),
            })
    
    return {
        "species": species,
        "shape": list(record.q_table.shape),
        "actions": action_names,
        "significant_states": significant_states,
        "total_states": record.q_table.shape[0],
        "nonzero_count": int((record.q_table != 0).sum()),
    }


@router.get("/ai/monsters")
async def list_monster_ai_states(game_id: Optional[str] = Query(None, description="Filter by game ID")):
    """List AI states for all active monsters across all games or a specific game."""
    states = {}
    
    # Collect monsters from all games in the registry
    for gid, game in game_registry.games.items():
        # Skip if filtering by game_id and this isn't the right game
        if game_id and gid != game_id:
            continue
        
        for monster_id, monster in game.monsters.items():
            intel = monster.intelligence_state
            memory = monster_service.monster_memories.get(monster_id)
            states[monster_id] = {
                "game_id": gid,
                "game_name": game.name,
                "monster_type": monster.monster_type,
                "name": monster.name,
                "hp": monster.stats.hp,
                "max_hp": monster.stats.max_hp,
                "position": {"x": monster.x, "y": monster.y},
                "intelligence": {
                    "generation": intel.generation,
                    "last_state_index": intel.last_state_index,
                    "last_action": intel.last_action,
                    "last_reward": intel.last_reward,
                    "last_decision_tick": intel.last_decision_tick,
                    "last_world_state": intel.last_world_state,
                },
                "memory_event_count": len(memory.events) if memory else 0,
            }
    
    return {"monsters": states}


class SimulateDecisionRequest(BaseModel):
    """Request model for simulating an AI decision."""
    monster_id: str
    hp_ratio: float = 1.0
    nearby_enemies: int = 1
    nearby_allies: int = 0
    room_type: str = "chamber"
    distance_to_threat: int = 1


@router.post("/ai/simulate-decision")
async def simulate_decision(request: SimulateDecisionRequest):
    """Simulate an AI decision for a monster without affecting game state."""
    # Find monster across all games
    monster = None
    for game in game_registry.games.values():
        if request.monster_id in game.monsters:
            monster = game.monsters[request.monster_id]
            break
    
    if not monster:
        return {"error": "Monster not found"}

    profile = monster_service.ai_profiles.get(monster.monster_type)
    if not profile:
        return {"error": "No AI profile for monster type"}

    world_state = {
        "room_type": request.room_type,
        "nearby_enemies": request.nearby_enemies,
        "nearby_allies": request.nearby_allies,
        "distance_to_threat": request.distance_to_threat,
    }

    species_record = monster_service.species_store.get_or_create(
        monster.monster_type,
        state_space=profile.decision_engine.encoder.state_space,
        action_count=len(AIAction),
    )

    memory = monster_service._get_memory(monster.id, profile)

    from ...domain.intelligence import DecisionContext
    import time

    context = DecisionContext(
        monster=monster,
        memory=memory,
        personality=profile.personality,
        q_table=species_record.q_table,
        current_tick=int(time.time()),
        world_state=world_state,
    )

    result = profile.decision_engine.decide(context)

    q_values = species_record.q_table[result.state_index].tolist()
    action_names = [a.name for a in AIAction]

    return {
        "state_index": result.state_index,
        "discrete_state": list(result.discrete_state),
        "action": result.action.name,
        "confidence": result.confidence,
        "q_values": dict(zip(action_names, q_values)),
        "personality_influence": {
            "aggression": profile.personality.aggression,
            "caution": profile.personality.caution,
        },
    }


@router.post("/ai/reset-species/{species}")
async def reset_species_knowledge(species: str):
    """Reset Q-table for a specific species (for testing)."""
    if species not in monster_service.ai_profiles:
        return {"error": "Unknown species"}

    profile = monster_service.ai_profiles[species]
    monster_service.species_store.reset_species(
        species,
        state_space=profile.decision_engine.encoder.state_space,
        action_count=len(AIAction),
    )
    monster_service.species_store.save()
    return {"success": True, "species": species}


# ================= Sandbox Endpoints =================


class SpawnMonsterRequest(BaseModel):
    """Request model for spawning a monster in sandbox."""
    monster_type: str
    x: int
    y: int


class MoveThreatRequest(BaseModel):
    """Request model for moving the threat."""
    direction: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None


class SetHPRequest(BaseModel):
    """Request model for setting monster HP."""
    hp: int


class StepRequest(BaseModel):
    """Request model for stepping the simulation."""
    count: int = 1


class RunRequest(BaseModel):
    """Request model for starting/stopping auto-run."""
    running: bool
    speed_ms: Optional[int] = None


class CombatToggleRequest(BaseModel):
    """Request model for enabling/disabling combat."""
    enabled: bool


@router.post("/sandbox/create")
async def create_sandbox():
    """Create or reset the sandbox environment."""
    return sandbox_manager.create()


@router.get("/sandbox/state")
async def get_sandbox_state():
    """Get the current sandbox state."""
    return sandbox_manager.get_state()


@router.post("/sandbox/spawn-monster")
async def spawn_sandbox_monster(request: SpawnMonsterRequest):
    """Spawn a monster in the sandbox."""
    result = sandbox_manager.spawn_monster(
        monster_type=request.monster_type,
        x=request.x,
        y=request.y
    )
    if result is None:
        return {"error": "Failed to spawn monster. Check type and position."}
    return {"success": True, "monster": result}


@router.delete("/sandbox/monster/{monster_id}")
async def remove_sandbox_monster(monster_id: str):
    """Remove a monster from the sandbox."""
    success = sandbox_manager.remove_monster(monster_id)
    return {"success": success}


@router.post("/sandbox/set-hp/{monster_id}")
async def set_sandbox_monster_hp(monster_id: str, request: SetHPRequest):
    """Set a monster's HP in the sandbox."""
    success = sandbox_manager.set_monster_hp(monster_id, request.hp)
    return {"success": success}


@router.post("/sandbox/spawn-threat")
async def spawn_sandbox_threat(request: MoveThreatRequest):
    """Spawn or place the threat at a position."""
    if request.x is None or request.y is None:
        return {"error": "x and y coordinates required"}
    result = sandbox_manager.spawn_threat(request.x, request.y)
    if result is None:
        return {"error": "Invalid position for threat"}
    return {"success": True, "threat": result}


@router.post("/sandbox/move-threat")
async def move_sandbox_threat(request: MoveThreatRequest):
    """Move the threat by direction or to position."""
    success = sandbox_manager.move_threat(
        direction=request.direction,
        x=request.x,
        y=request.y
    )
    return {"success": success}


@router.delete("/sandbox/threat")
async def remove_sandbox_threat():
    """Remove the threat from the sandbox."""
    success = sandbox_manager.remove_threat()
    return {"success": success}


@router.post("/sandbox/step")
async def step_sandbox(request: StepRequest):
    """Step the sandbox simulation by N ticks."""
    new_logs = sandbox_manager.step(count=request.count)
    return {
        "success": True,
        "tick": sandbox_manager.state.tick if sandbox_manager.state else 0,
        "new_logs": new_logs
    }


@router.post("/sandbox/run")
async def run_sandbox(request: RunRequest):
    """Start or stop auto-run mode."""
    result = sandbox_manager.set_running(
        running=request.running,
        speed_ms=request.speed_ms
    )
    return {"success": True, **result}


@router.get("/sandbox/monster-types")
async def get_sandbox_monster_types():
    """Get available monster types for spawning."""
    types = []
    for monster_type, config in monster_service.monster_types.items():
        types.append({
            "type": monster_type,
            "name": config.get("name", monster_type),
            "symbol": config.get("symbol", "?"),
            "color": config.get("color", "#ff0000"),
            "has_ai": monster_type in monster_service.ai_profiles,
        })
    return {"types": types}


@router.post("/sandbox/combat")
async def toggle_sandbox_combat(request: CombatToggleRequest):
    """Enable or disable combat simulation in sandbox."""
    success = sandbox_manager.set_combat_enabled(request.enabled)
    return {"success": success, "combat_enabled": request.enabled}


@router.post("/sandbox/reset-threat-hp")
async def reset_sandbox_threat_hp():
    """Reset threat HP to maximum."""
    success = sandbox_manager.reset_threat_hp()
    return {"success": success}
