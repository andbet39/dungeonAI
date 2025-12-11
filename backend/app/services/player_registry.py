"""
Player Registry - Manages player identity and cross-game persistence.
Uses token-based identification for reconnection support.
"""
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, field, asdict

from ..config import settings
from . import storage_service


@dataclass
class PlayerProfile:
    """Persistent player data across games."""
    token: str
    display_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    current_game_id: Optional[str] = None
    current_player_id: Optional[str] = None  # player_id within current game
    total_games_played: int = 0
    nickname: Optional[str] = None  # AI-generated nickname based on achievements
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlayerProfile":
        # Handle missing fields for forward compatibility
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def update_last_seen(self) -> None:
        self.last_seen = datetime.now().isoformat()
    
    def get_full_title(self) -> str:
        """Get the player's full title (name + nickname)."""
        if self.nickname:
            return f"{self.display_name} {self.nickname}"
        return self.display_name


class PlayerRegistry:
    """
    Central registry for player identity management.
    Tracks player tokens across games and persists to disk.
    """
    
    _instance: Optional["PlayerRegistry"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "PlayerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._players: Dict[str, PlayerProfile] = {}
        self._lock = asyncio.Lock()
        self._dirty = False
        self._save_task: Optional[asyncio.Task] = None
        self._initialized = True
    
    async def start(self) -> None:
        """Start the registry and load from disk."""
        await self._load()
        self._start_periodic_save()
        print(f"[PlayerRegistry] Started with {len(self._players)} players")
    
    async def stop(self) -> None:
        """Stop and save to disk."""
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        await self._save()
        print("[PlayerRegistry] Stopped")
    
    def _start_periodic_save(self) -> None:
        if self._save_task is not None:
            return
        
        async def periodic_save():
            while True:
                await asyncio.sleep(60)  # Save every minute if dirty
                if self._dirty:
                    await self._save()
        
        self._save_task = asyncio.create_task(periodic_save())
    
    async def _load(self) -> None:
        """Load player registry from disk."""
        registry_data = await storage_service.load_player_registry()
        if registry_data:
            self._players = {
                token: PlayerProfile.from_dict({"token": token, **data})
                for token, data in registry_data.get("players", {}).items()
            }
    
    async def _save(self) -> None:
        """Save player registry to disk."""
        # Load existing data to preserve stats and other data
        existing_data = await storage_service.load_player_registry() or {}
        existing_data["players"] = {token: p.to_dict() for token, p in self._players.items()}
        await storage_service.save_player_registry(existing_data)
        self._dirty = False
    
    async def save(self) -> None:
        """Public save method for manual saves (e.g., shutdown)."""
        await self._save()
    
    def generate_token(self) -> str:
        """Generate a new unique player token."""
        return str(uuid.uuid4())
    
    async def get_or_create_player(self, token: str, display_name: Optional[str] = None) -> PlayerProfile:
        """
        Get existing player by token or create a new one.
        
        Args:
            token: Player's unique token (from localStorage)
            display_name: Optional display name for new players
        
        Returns:
            PlayerProfile for the token
        """
        async with self._lock:
            if token in self._players:
                player = self._players[token]
                player.update_last_seen()
                self._dirty = True
                return player
            
            # Create new player
            if not display_name:
                display_name = f"Hero_{token[:6]}"
            
            player = PlayerProfile(
                token=token,
                display_name=display_name
            )
            self._players[token] = player
            self._dirty = True
            
            print(f"[PlayerRegistry] New player registered: {display_name}")
            return player
    
    def get_player(self, token: str) -> Optional[PlayerProfile]:
        """Get player by token."""
        return self._players.get(token)
    
    async def update_player_game(
        self,
        token: str,
        game_id: Optional[str],
        player_id: Optional[str] = None
    ) -> None:
        """Update which game a player is currently in."""
        async with self._lock:
            if token in self._players:
                player = self._players[token]
                player.current_game_id = game_id
                player.current_player_id = player_id
                player.update_last_seen()
                if game_id:
                    player.total_games_played += 1
                self._dirty = True
    
    def find_player_game(self, token: str) -> Optional[str]:
        """Find which game a player is currently in."""
        player = self._players.get(token)
        if player:
            return player.current_game_id
        return None
    
    async def clear_player_game(self, token: str) -> None:
        """Clear a player's current game assignment."""
        await self.update_player_game(token, None, None)
    
    async def update_display_name(self, token: str, display_name: str) -> bool:
        """Update a player's display name."""
        async with self._lock:
            if token in self._players:
                self._players[token].display_name = display_name
                self._players[token].update_last_seen()
                self._dirty = True
                return True
            return False
    
    async def update_nickname(self, token: str, nickname: str) -> bool:
        """Update a player's nickname."""
        async with self._lock:
            if token in self._players:
                self._players[token].nickname = nickname
                self._players[token].update_last_seen()
                self._dirty = True
                return True
            return False
    
    def get_players_in_game(self, game_id: str) -> list[PlayerProfile]:
        """Get all players currently in a specific game."""
        return [p for p in self._players.values() if p.current_game_id == game_id]
    
    @property
    def players(self) -> Dict[str, PlayerProfile]:
        """Access to all player profiles."""
        return self._players
    
    @property
    def player_count(self) -> int:
        """Total registered players."""
        return len(self._players)
    
    @property
    def active_player_count(self) -> int:
        """Players currently in a game."""
        return sum(1 for p in self._players.values() if p.current_game_id)


# Global player registry instance
player_registry = PlayerRegistry()
