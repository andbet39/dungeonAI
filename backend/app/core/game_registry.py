"""
Game Registry - Central coordinator for managing multiple game instances.
Handles game lifecycle, player routing, and cleanup scheduling.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, TYPE_CHECKING

from ..config import settings

if TYPE_CHECKING:
    from .game import Game


class GameInfo:
    """Lightweight info about a game for the lobby."""
    
    def __init__(
        self,
        game_id: str,
        name: str,
        player_count: int,
        active_player_count: int,
        max_players: int,
        is_completed: bool,
        created_at: datetime
    ):
        self.game_id = game_id
        self.name = name
        self.player_count = player_count
        self.active_player_count = active_player_count
        self.max_players = max_players
        self.is_completed = is_completed
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "player_count": self.active_player_count,  # Show active players in UI
            "total_players": self.player_count,  # Total registered players
            "max_players": self.max_players,
            "is_completed": self.is_completed,
            # Use active player count to determine if joinable
            "is_joinable": self.active_player_count < self.max_players and not self.is_completed,
            "created_at": self.created_at.isoformat()
        }


class GameRegistry:
    """
    Central registry for managing multiple game instances.
    Handles game creation, player routing, and automatic cleanup.
    """
    
    _instance: Optional["GameRegistry"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "GameRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._games: Dict[str, "Game"] = {}
        self._player_to_game: Dict[str, str] = {}  # player_token -> game_id
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._max_players = settings.multi_game.max_players_per_game
        self._inactive_timeout = timedelta(minutes=settings.multi_game.game_inactive_timeout_minutes)
        self._completed_grace_period = timedelta(minutes=settings.multi_game.completed_game_grace_period_minutes)
        self._initialized = True
        
        print(f"[GameRegistry] Initialized with max_players={self._max_players}, "
              f"inactive_timeout={self._inactive_timeout}, grace_period={self._completed_grace_period}")
    
    async def start(self) -> None:
        """Start the registry and its cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            print("[GameRegistry] Started cleanup task")
    
    async def stop(self) -> None:
        """Stop the registry and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            print("[GameRegistry] Stopped cleanup task")
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of inactive and completed games."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_games()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[GameRegistry] Error in cleanup loop: {e}")
    
    async def _cleanup_games(self) -> None:
        """Remove inactive or completed games past their grace period."""
        async with self._lock:
            now = datetime.now()
            games_to_remove = []
            
            for game_id, game in self._games.items():
                # Check if game is completed and past grace period
                if game.is_completed:
                    if game.completed_at and now - game.completed_at > self._completed_grace_period:
                        games_to_remove.append(game_id)
                        print(f"[GameRegistry] Game {game_id} marked for removal (completed)")
                        continue
                
                # Check if game is inactive (no connections) for too long
                if not game.has_connections:
                    if game.last_activity and now - game.last_activity > self._inactive_timeout:
                        games_to_remove.append(game_id)
                        print(f"[GameRegistry] Game {game_id} marked for removal (inactive)")
            
            for game_id in games_to_remove:
                await self._remove_game(game_id)
    
    async def _remove_game(self, game_id: str) -> None:
        """Remove a game and clean up player mappings."""
        if game_id not in self._games:
            return
        
        game = self._games[game_id]
        
        # Stop game loop
        await game.stop()
        
        # Remove player mappings
        players_to_remove = [
            token for token, gid in self._player_to_game.items()
            if gid == game_id
        ]
        for token in players_to_remove:
            del self._player_to_game[token]
        
        # Remove game
        del self._games[game_id]
        print(f"[GameRegistry] Removed game {game_id}")
    
    def generate_game_id(self) -> str:
        """Generate a unique game ID."""
        return str(uuid.uuid4())[:8]
    
    async def create_game(
        self, 
        name: Optional[str] = None,
        map_width: Optional[int] = None,
        map_height: Optional[int] = None,
        room_count: Optional[int] = None
    ) -> "Game":
        """
        Create a new game instance.
        
        Args:
            name: Optional name for the game. If not provided, will be auto-generated.
            map_width: Optional map width (default from settings)
            map_height: Optional map height (default from settings)
            room_count: Optional room count (default from settings)
        
        Returns:
            The newly created Game instance
        """
        from .game import Game
        from ..services import ai_service
        
        async with self._lock:
            game_id = self.generate_game_id()
            
            # Generate name if not provided
            if not name:
                name = await ai_service.generate_game_name()
            
            # Create and initialize game with map options
            game = Game(game_id=game_id, name=name)
            await game.initialize(
                map_width=map_width,
                map_height=map_height,
                room_count=room_count
            )
            
            self._games[game_id] = game
            print(f"[GameRegistry] Created game {game_id}: {name}")
            
            return game
    
    async def get_or_create_joinable_game(self) -> "Game":
        """
        Get an existing joinable game or create a new one.
        A game is joinable if it has less than max active players and is not completed.
        
        Returns:
            A Game instance that can accept new players
        """
        async with self._lock:
            # Find first joinable game (use active_player_count for connected players)
            for game in self._games.values():
                if not game.is_completed and game.active_player_count < self._max_players:
                    return game
        
        # No joinable game found, create a new one
        return await self.create_game()
    
    def get_game(self, game_id: str) -> Optional["Game"]:
        """Get a game by its ID."""
        return self._games.get(game_id)
    
    def get_game_for_player(self, player_token: str) -> Optional["Game"]:
        """Get the game a player is currently in."""
        game_id = self._player_to_game.get(player_token)
        if game_id:
            return self._games.get(game_id)
        return None
    
    async def assign_player_to_game(self, player_token: str, game_id: str) -> bool:
        """
        Assign a player to a specific game.
        Players can join completed games for exploration.
        
        Returns:
            True if assignment was successful
        """
        async with self._lock:
            if game_id not in self._games:
                return False
            
            game = self._games[game_id]
            # Use active_player_count for connected players limit
            # Allow joining completed games (for exploration)
            if not game.is_completed and game.active_player_count >= self._max_players:
                return False
            
            # Remove from previous game if any
            if player_token in self._player_to_game:
                old_game_id = self._player_to_game[player_token]
                if old_game_id != game_id:
                    old_game = self._games.get(old_game_id)
                    if old_game:
                        await old_game.remove_player_by_token(player_token)
            
            self._player_to_game[player_token] = game_id
            return True
    
    def remove_player_mapping(self, player_token: str) -> None:
        """Remove player's game mapping (used when player fully leaves)."""
        if player_token in self._player_to_game:
            del self._player_to_game[player_token]
    
    def list_games(self) -> list[GameInfo]:
        """Get info about all active games."""
        games = []
        for game in self._games.values():
            games.append(GameInfo(
                game_id=game.game_id,
                name=game.name,
                player_count=game.player_count,
                active_player_count=game.active_player_count,
                max_players=self._max_players,
                is_completed=game.is_completed,
                created_at=game.created_at
            ))
        return sorted(games, key=lambda g: g.created_at, reverse=True)
    
    def list_joinable_games(self) -> list[GameInfo]:
        """Get info about games that can be joined."""
        return [
            g for g in self.list_games()
            if g.active_player_count < g.max_players and not g.is_completed
        ]
    
    @property
    def games(self) -> Dict[str, "Game"]:
        """Access to all game instances (for shutdown save)."""
        return self._games
    
    @property
    def game_count(self) -> int:
        """Get the number of active games."""
        return len(self._games)
    
    @property
    def total_player_count(self) -> int:
        """Get the total number of players across all games."""
        return sum(game.player_count for game in self._games.values())
    
    async def restore_games(self) -> None:
        """Restore saved games from storage on startup."""
        from ..services.storage_service import storage_service
        from .game import Game
        
        try:
            saved_games = storage_service.list_game_saves()
            for save_info in saved_games:
                game_id = save_info.get("game_id")
                if not game_id:
                    continue
                try:
                    game = Game(game_id=game_id, name=save_info.get("name", "Loading..."))
                    loaded = await game.initialize(load_save_id=game_id)
                    if loaded:
                        self._games[game_id] = game
                        print(f"[GameRegistry] Restored game {game_id}: {game.name}")
                except Exception as e:
                    print(f"[GameRegistry] Failed to restore game {game_id}: {e}")
            print(f"[GameRegistry] Restored {len(self._games)} game(s) from storage")
        except Exception as e:
            print(f"[GameRegistry] Error restoring games: {e}")
    
    async def cleanup_games(self) -> None:
        """Public cleanup method for external callers."""
        await self._cleanup_games()


# Global game registry instance
game_registry = GameRegistry()
