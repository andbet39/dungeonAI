"""
Services layer - Business logic and external integrations.
"""
from .ai_service import AIService, ai_service
from .storage_service import StorageService, storage_service
from .monster_service import MonsterService, monster_service
from .player_registry import PlayerRegistry, PlayerProfile, player_registry
from .player_stats import PlayerStatsTracker, PlayerStats, StatType, player_stats_tracker

# Import game_registry from core for convenience
from ..core.game_registry import GameRegistry, GameInfo, game_registry

__all__ = [
    "AIService", "ai_service",
    "StorageService", "storage_service",
    "MonsterService", "monster_service",
    "PlayerRegistry", "PlayerProfile", "player_registry",
    "PlayerStatsTracker", "PlayerStats", "StatType", "player_stats_tracker",
    "GameRegistry", "GameInfo", "game_registry",
]
