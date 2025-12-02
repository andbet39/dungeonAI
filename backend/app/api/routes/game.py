"""
Game state API endpoints for DungeonAI.
Includes lobby endpoints for multi-game management.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from ...core import game_registry
from ...services import ai_service, player_registry
from ...services.player_stats import player_stats_tracker


router = APIRouter(prefix="/api", tags=["game"])


# ============== Request/Response Models ==============

class CreateGameRequest(BaseModel):
    name: Optional[str] = None
    auto_join: bool = True
    map_width: Optional[int] = None
    map_height: Optional[int] = None
    room_count: Optional[int] = None


class PlayerTokenRequest(BaseModel):
    player_token: str
    display_name: Optional[str] = None


class UpdateNameRequest(BaseModel):
    display_name: str


# ============== Lobby Endpoints ==============

@router.get("/lobby")
async def get_lobby():
    """Get lobby info with list of available games."""
    games = game_registry.list_games()
    joinable = game_registry.list_joinable_games()
    
    return {
        "games": [g.to_dict() for g in games],
        "joinable_games": [g.to_dict() for g in joinable],
        "total_games": game_registry.game_count,
        "total_players": game_registry.total_player_count
    }


@router.post("/games")
async def create_game(request: CreateGameRequest = None):
    """Create a new game with optional map size configuration."""
    name = request.name if request else None
    map_width = request.map_width if request else None
    map_height = request.map_height if request else None
    room_count = request.room_count if request else None
    
    game = await game_registry.create_game(
        name=name,
        map_width=map_width,
        map_height=map_height,
        room_count=room_count
    )
    
    return {
        "success": True,
        "game_id": game.game_id,
        "name": game.name
    }


@router.get("/games/{game_id}")
async def get_game_info(game_id: str):
    """Get info about a specific game."""
    game = game_registry.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return {
        "game_id": game.game_id,
        "name": game.name,
        "player_count": game.player_count,
        "is_completed": game.is_completed,
        "room_count": len(game.rooms),
        "created_at": game.created_at.isoformat()
    }


@router.post("/games/{game_id}/join")
async def join_game(game_id: str, x_player_token: str = Header(alias="X-Player-Token")):
    """Join a specific game (including completed games for exploration)."""
    game = game_registry.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    from ...config import settings
    # Use active_player_count (connected players) instead of player_count (all registered)
    if game.active_player_count >= settings.multi_game.max_players_per_game:
        raise HTTPException(status_code=400, detail="Game is full")
    
    # Assign player to game
    success = await game_registry.assign_player_to_game(x_player_token, game_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not join game")
    
    # Update player registry
    await player_registry.update_player_game(x_player_token, game_id)
    
    return {
        "success": True,
        "game_id": game_id,
        "name": game.name
    }


@router.post("/games/auto-join")
async def auto_join_game(x_player_token: str = Header(alias="X-Player-Token")):
    """Automatically join an available game or create a new one."""
    game = await game_registry.get_or_create_joinable_game()
    
    # Assign player
    success = await game_registry.assign_player_to_game(x_player_token, game.game_id)
    if not success:
        raise HTTPException(status_code=500, detail="Could not join game")
    
    await player_registry.update_player_game(x_player_token, game.game_id)
    
    return {
        "success": True,
        "game_id": game.game_id,
        "name": game.name,
        "is_new": game.player_count == 0
    }


# ============== Player Endpoints ==============

@router.post("/player/register")
async def register_player(request: PlayerTokenRequest):
    """Register or retrieve a player by token."""
    player = await player_registry.get_or_create_player(
        token=request.player_token,
        display_name=request.display_name
    )
    
    return {
        "token": player.token,
        "display_name": player.display_name,
        "current_game_id": player.current_game_id,
        "total_games_played": player.total_games_played
    }


@router.get("/player/{token}/game")
async def get_player_current_game(token: str):
    """Get the game a player is currently in."""
    game_id = player_registry.find_player_game(token)
    if not game_id:
        return {"game_id": None}
    
    game = game_registry.get_game(game_id)
    if not game:
        # Clear stale reference
        await player_registry.clear_player_game(token)
        return {"game_id": None}
    
    return {
        "game_id": game_id,
        "name": game.name,
        "is_completed": game.is_completed
    }


@router.get("/player/{token}/stats")
async def get_player_stats(token: str):
    """Get a player's statistics including XP, kills by type, and nickname."""
    player = player_registry.get_player(token)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    stats = player_stats_tracker.get_stats(token)
    
    # Build response with stats data
    stats_data = {
        "token": token,
        "display_name": player.display_name,
        "nickname": player.nickname,
        "full_title": player.get_full_title(),
        "monsters_killed": stats.monsters_killed if stats else 0,
        "experience_earned": stats.experience_earned if stats else 0,
        "kills_by_type": stats.kills_by_type if stats else {},
        "rooms_visited": stats.rooms_visited if stats else 0,
        "damage_dealt": stats.damage_dealt if stats else 0,
        "damage_taken": stats.damage_taken if stats else 0,
        "deaths": stats.deaths if stats else 0,
        "games_completed": stats.games_completed if stats else 0,
        "critical_hits": stats.critical_hits if stats else 0,
        "total_games_played": player.total_games_played,
        "needs_nickname_refresh": stats.needs_nickname_refresh() if stats else False,
    }
    
    return stats_data


@router.put("/player/{token}/name")
async def update_player_name(token: str, request: UpdateNameRequest):
    """Update a player's display name."""
    player = player_registry.get_player(token)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Validate name length
    if len(request.display_name) < 2 or len(request.display_name) > 30:
        raise HTTPException(status_code=400, detail="Name must be 2-30 characters")
    
    success = await player_registry.update_display_name(token, request.display_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update name")
    
    return {
        "success": True,
        "display_name": request.display_name,
        "full_title": player_registry.get_player(token).get_full_title()
    }


@router.post("/player/{token}/nickname")
async def generate_player_nickname(token: str):
    """Generate or regenerate a player's nickname based on their kill stats."""
    player = player_registry.get_player(token)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    stats = player_stats_tracker.get_stats(token)
    if not stats or stats.monsters_killed == 0:
        raise HTTPException(status_code=400, detail="Need at least one kill to generate nickname")
    
    # Generate nickname using AI
    nickname = await ai_service.generate_player_nickname(
        kills_by_type=stats.kills_by_type,
        total_kills=stats.monsters_killed
    )
    
    # Save nickname to both registry and stats
    await player_registry.update_nickname(token, nickname)
    await player_stats_tracker.update_nickname(token, nickname)
    
    # Get updated player to return full title
    updated_player = player_registry.get_player(token)
    
    return {
        "success": True,
        "nickname": nickname,
        "full_title": updated_player.get_full_title() if updated_player else nickname
    }


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get the leaderboard of top players by XP."""
    # Get XP-based leaderboard from stats tracker
    leaderboard_data = player_stats_tracker.get_xp_leaderboard(limit=min(limit, 50))
    
    # Enrich with player profile data
    enriched_leaderboard = []
    for i, entry in enumerate(leaderboard_data):
        token = entry["token"]
        player = player_registry.get_player(token)
        
        enriched_leaderboard.append({
            "rank": i + 1,
            "token": token,
            "display_name": player.display_name if player else f"Hero_{token[:6]}",
            "nickname": entry.get("nickname") or (player.nickname if player else None),
            "full_title": player.get_full_title() if player else f"Hero_{token[:6]}",
            "experience": entry["experience"],
            "kills": entry["kills"],
            "top_kill": entry.get("top_kill"),
        })
    
    return {
        "leaderboard": enriched_leaderboard,
        "total_players": len(leaderboard_data)
    }


# ============== Legacy Endpoints ==============

@router.get("/state")
async def get_game_state():
    """Return the current game state (legacy - returns first active game)."""
    games = game_registry.list_games()
    if games:
        game = game_registry.get_game(games[0].game_id)
        if game:
            return game.get_state()
    return {"error": "No active games"}


@router.get("/status")
async def get_status():
    """Return server and AI status."""
    return {
        "status": "running",
        "total_games": game_registry.game_count,
        "total_players": game_registry.total_player_count,
        "ai_service": ai_service.get_status()
    }
