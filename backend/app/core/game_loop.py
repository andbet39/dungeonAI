"""
Game loop for DungeonAI.
Handles periodic updates for monster AI and other game systems.
"""
import asyncio
from typing import Optional, TYPE_CHECKING

from ..config import settings

if TYPE_CHECKING:
    from .game_manager import GameManager


class GameLoop:
    """
    Background game loop that runs periodic updates.
    Handles monster AI, scheduled events, etc.
    """
    
    _instance: Optional["GameLoop"] = None
    
    def __new__(cls) -> "GameLoop":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._tick_interval = settings.game.tick_interval
        self._current_tick = 0
        self._game_manager: Optional["GameManager"] = None
        self._initialized = True
    
    def set_game_manager(self, game_manager: "GameManager") -> None:
        """Set the game manager reference."""
        self._game_manager = game_manager
    
    async def start(self) -> None:
        """Start the game loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        print("[GameLoop] Started game loop")
    
    async def stop(self) -> None:
        """Stop the game loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print("[GameLoop] Stopped game loop")
    
    async def _loop(self) -> None:
        """Main game loop."""
        while self._running:
            try:
                await asyncio.sleep(self._tick_interval)
                self._current_tick += 1
                
                if self._game_manager:
                    # Update monsters (movement AI)
                    state_changed = await self._game_manager.update_monsters(self._current_tick)
                    
                    # Process monster combat turns (when it's monster's turn in active fights)
                    await self._game_manager.process_monster_combat_turns()
                    
                    # Check for player turn timeouts in active fights
                    await self._game_manager.process_turn_timeouts()
                    
                    # Only broadcast if state changed and there are players
                    if state_changed and self._game_manager.has_connections:
                        await self._game_manager.broadcast_state()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[GameLoop] Error in game loop: {e}")
                continue
    
    @property
    def current_tick(self) -> int:
        """Get current game tick."""
        return self._current_tick
    
    @property
    def is_running(self) -> bool:
        """Check if game loop is running."""
        return self._running


# Global game loop instance
game_loop = GameLoop()
