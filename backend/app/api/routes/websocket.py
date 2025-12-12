"""
WebSocket endpoint for DungeonAI multiplayer.
Supports multi-game routing via game_id query param.
Requires authentication via cookies.
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from ...core import game_registry
from ...core.sandbox import sandbox_manager
from ...services import player_registry
from ...services.auth_service import auth_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for multiplayer game communication.
    
    Requires authentication via access_token and player_token cookies.
    
    Query params:
        game_id: ID of game to join (optional, will auto-join if not provided)
    """
    await websocket.accept()
    
    # Extract tokens from cookies
    access_token = websocket.cookies.get("access_token")
    player_token = websocket.cookies.get("player_token")
    
    # Validate JWT authentication
    if not access_token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Not authenticated"}))
        await websocket.close(code=4401)
        return
    
    try:
        payload = auth_service.decode_token(access_token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.send_text(json.dumps({"type": "error", "message": "Invalid token"}))
            await websocket.close(code=4401)
            return
    except Exception:
        await websocket.send_text(json.dumps({"type": "error", "message": "Authentication failed"}))
        await websocket.close(code=4401)
        return
    
    # Require player token (selected profile)
    if not player_token:
        await websocket.send_text(json.dumps({"type": "error", "message": "No player profile selected"}))
        await websocket.close(code=4400)
        return
    
    # Verify the player profile belongs to the authenticated user
    profile = player_registry.get_player(player_token)
    if not profile:
        await websocket.send_text(json.dumps({"type": "error", "message": "Player profile not found"}))
        await websocket.close(code=4404)
        return
    
    if profile.user_id != user_id:
        await websocket.send_text(json.dumps({"type": "error", "message": "Profile belongs to different user"}))
        await websocket.close(code=4403)
        return
    
    player_id = None
    game = None
    
    try:
        # Player profile already verified above
        player_profile = profile
        
        # Get game - either specified, player's current, or auto-join
        if game_id:
            game = game_registry.get_game(game_id)
        elif player_profile.current_game_id:
            game = game_registry.get_game(player_profile.current_game_id)
        
        if not game:
            # Auto-join a game
            game = await game_registry.get_or_create_joinable_game()
            await game_registry.assign_player_to_game(player_token, game.game_id)
        
        if not game:
            await websocket.send_text(json.dumps({"type": "error", "message": "No game available"}))
            await websocket.close()
            return
        
        # Wait for initial message (may contain reconnect info)
        initial_data = await websocket.receive_text()
        initial_message = json.loads(initial_data)
        
        existing_player_id = initial_message.get("player_id") if initial_message.get("type") == "reconnect" else None
        
        # Add player to game
        player_id, is_reconnection = await game.add_player(websocket, player_token, existing_player_id)
        
        # Update player registry with game assignment
        await player_registry.update_player_game(player_token, game.game_id, player_id)
        
        # Send welcome
        await game.send_welcome(player_id, is_reconnection)
        
        if not is_reconnection:
            await game.broadcast_player_joined(player_id)
            # Send room_entered for initial spawn room (triggers room popup on client)
            player = game.players.get(player_id)
            if player and player.current_room_id:
                room = next((r for r in game.rooms if r.id == player.current_room_id), None)
                if room:
                    await game.send_room_entered(player_id, room.get_info())
        
        await game.broadcast_state()
        
        # Main message loop
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "move":
                if game._is_player_in_fight(player_id):
                    continue
                dx, dy = message.get("dx", 0), message.get("dy", 0)
                result = await game.move_player(player_id, dx, dy)
                if result["success"]:
                    if result.get("room_entered"):
                        await game.send_room_entered(player_id, result["room_entered"])
                    await game.broadcast_state()
            
            elif msg_type == "interact":
                result = await game.interact(player_id)
                action = result.get("action")
                
                if action == "fight_request":
                    await websocket.send_text(json.dumps({
                        "type": "fight_request",
                        "monster": result["monster"],
                        "monster_id": result["monster_id"]
                    }))
                elif action == "can_join_fight":
                    await websocket.send_text(json.dumps({
                        "type": "can_join_fight",
                        "fight_id": result["fight_id"],
                        "fight": result["fight"],
                        "monster": result["monster"]
                    }))
                elif action == "already_in_fight":
                    await websocket.send_text(json.dumps({"type": "error", "message": "Already in fight"}))
                elif action in ("door_opened", "door_closed"):
                    await game.broadcast_state()
            
            elif msg_type == "request_fight":
                monster_id = message.get("monster_id")
                if monster_id:
                    result = await game.start_fight(player_id, monster_id)
                    if result["success"]:
                        fight = game.active_fights.get(result["fight"]["id"])
                        monster = game.monsters.get(monster_id)
                        if fight and monster:
                            await game.send_fight_started(fight, monster, fight.player_ids)
                    else:
                        await websocket.send_text(json.dumps({"type": "error", "message": result.get("error")}))
            
            elif msg_type == "join_fight":
                fight_id = message.get("fight_id")
                if fight_id:
                    result = await game.join_fight(player_id, fight_id)
                    if result["success"]:
                        fight = game.active_fights.get(fight_id)
                        monster = game.monsters.get(result["monster"]["id"])
                        if fight and monster:
                            await websocket.send_text(json.dumps({
                                "type": "fight_started",
                                "fight": fight.to_dict(),
                                "monster": monster.to_dict()
                            }))
                            await game.send_fight_updated(fight, monster)
                    else:
                        await websocket.send_text(json.dumps({"type": "error", "message": result.get("error")}))
            
            elif msg_type == "decline_fight":
                await websocket.send_text(json.dumps({"type": "fight_declined"}))
            
            elif msg_type == "flee_fight":
                fight_id = message.get("fight_id")
                if fight_id:
                    fight = game.active_fights.get(fight_id)
                    remaining_before = list(fight.player_ids) if fight else []
                    
                    result = await game.flee_fight(player_id, fight_id)
                    if result["success"]:
                        await websocket.send_text(json.dumps({"type": "fight_left", "fight_id": fight_id}))
                        
                        if result["fight_ended"]:
                            if player_id in remaining_before:
                                remaining_before.remove(player_id)
                            await game.send_fight_ended(fight_id, "fled", remaining_before)
                        else:
                            remaining = result.get("remaining_players", [])
                            await game.send_player_fled(fight_id, player_id, remaining)
                            fight = game.active_fights.get(fight_id)
                            monster = game.monsters.get(fight.monster_id) if fight else None
                            if fight and monster:
                                await game.send_fight_updated(fight, monster)
                    else:
                        # Still send fight_left to reset client state even if the flee failed
                        # (e.g., fight already ended or player wasn't in fight)
                        await websocket.send_text(json.dumps({"type": "fight_left", "fight_id": fight_id}))
                else:
                    # No fight_id provided - send fight_left to clean up client state
                    await websocket.send_text(json.dumps({"type": "fight_left", "fight_id": None}))
            
            elif msg_type == "combat_action":
                fight_id, action = message.get("fight_id"), message.get("action")
                if fight_id and action:
                    result = await game.process_combat_action(player_id, fight_id, action)
                    if result["success"]:
                        if result.get("fight_ended"):
                            await game.broadcast_fight_ended(result, fight_id)
                        else:
                            fight = game.active_fights.get(fight_id)
                            monster = game.monsters.get(fight.monster_id) if fight else None
                            if fight and monster:
                                await game.send_fight_updated(fight, monster)
                    else:
                        await websocket.send_text(json.dumps({"type": "error", "message": result.get("error")}))
            
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        if player_id and game:
            player_fight = game._get_fight_for_player(player_id)
            if player_fight:
                await game.flee_fight(player_id, player_fight.id)
            
            await game.broadcast_player_left(player_id)
            await game.remove_player(player_id)
            await game.broadcast_state()


@router.websocket("/ws/sandbox")
async def sandbox_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for sandbox simulation."""
    await websocket.accept()
    sandbox_manager.register_ws(websocket)
    
    try:
        await websocket.send_text(json.dumps({"type": "sandbox_state", "state": sandbox_manager.get_state()}))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "move_threat":
                sandbox_manager.move_threat(direction=message.get("direction"), x=message.get("x"), y=message.get("y"))
                await websocket.send_text(json.dumps({"type": "sandbox_state", "state": sandbox_manager.get_state()}))
            
            elif msg_type == "set_hp":
                mid, hp = message.get("monster_id"), message.get("hp")
                if mid and hp is not None:
                    sandbox_manager.set_monster_hp(mid, hp)
                    await websocket.send_text(json.dumps({"type": "sandbox_state", "state": sandbox_manager.get_state()}))
            
            elif msg_type == "step":
                new_logs = sandbox_manager.step(message.get("count", 1))
                await websocket.send_text(json.dumps({"type": "sandbox_update", "state": sandbox_manager.get_state(), "new_logs": new_logs}))
            
            elif msg_type == "run":
                sandbox_manager.set_running(message.get("running", False), message.get("speed_ms"))
                await websocket.send_text(json.dumps({"type": "sandbox_state", "state": sandbox_manager.get_state()}))
            
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        sandbox_manager.unregister_ws(websocket)
