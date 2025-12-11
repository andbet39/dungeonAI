"""
Services layer - Business logic and external integrations.
"""
from .ai_service import AIService, ai_service
from .storage_service import StorageService
from .storage_service import storage_service as json_storage_service
from .mongodb_storage_service import MongoDBStorageService
from .monster_service import MonsterService, monster_service

# Import game_registry from core for convenience
from ..core.game_registry import GameRegistry, GameInfo, game_registry

# Auto-select storage backend based on MongoDB availability
from ..config import settings
from ..db import mongodb_manager

# Initialize storage service based on configuration
# This will be evaluated at import time, but MongoDB connection happens later in main.py
# So we create both instances and the actual selection happens at runtime
_mongodb_storage = MongoDBStorageService()
_json_storage = json_storage_service


def _get_storage_service():
    """Get the appropriate storage service based on MongoDB availability."""
    if settings.mongodb.is_enabled and mongodb_manager.is_connected:
        return _mongodb_storage
    return _json_storage


def get_storage_backend_name() -> str:
    """Get the name of the currently active storage backend."""
    if settings.mongodb.is_enabled and mongodb_manager.is_connected:
        return "MongoDB"
    return "JSON"


# Create a property-based accessor for storage_service
class _StorageServiceProxy:
    """Proxy that dynamically selects the appropriate storage backend."""

    def __getattr__(self, name):
        service = _get_storage_service()
        backend = "MongoDB" if service is _mongodb_storage else "JSON"
        # Debug logging to track which backend is being used
        if name in ['save_player_registry', 'load_player_registry', 'save_game_by_id', 'load_game_by_id']:
            print(f"[StorageProxy] Routing {name} to {backend} backend")
        return getattr(service, name)

    def __call__(self, *args, **kwargs):
        service = _get_storage_service()
        return service(*args, **kwargs)


storage_service = _StorageServiceProxy()

from .player_stats import PlayerStatsTracker, PlayerStats, StatType, player_stats_tracker
from .player_registry import PlayerRegistry, PlayerProfile, player_registry

__all__ = [
    "AIService", "ai_service",
    "StorageService", "storage_service",
    "MongoDBStorageService",
    "MonsterService", "monster_service",
    "PlayerRegistry", "PlayerProfile", "player_registry",
    "PlayerStatsTracker", "PlayerStats", "StatType", "player_stats_tracker",
    "GameRegistry", "GameInfo", "game_registry",
    "get_storage_backend_name",
]
