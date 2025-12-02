"""
API dependencies for dependency injection.
"""
from typing import Generator

from ..core import game_manager, game_loop
from ..services import ai_service, storage_service, monster_service


def get_game_manager():
    """Get the game manager instance."""
    return game_manager


def get_game_loop():
    """Get the game loop instance."""
    return game_loop


def get_ai_service():
    """Get the AI service instance."""
    return ai_service


def get_storage_service():
    """Get the storage service instance."""
    return storage_service


def get_monster_service():
    """Get the monster service instance."""
    return monster_service
