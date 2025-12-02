"""
API route modules.
"""
from .admin import router as admin_router
from .game import router as game_router
from .websocket import router as websocket_router

__all__ = ["admin_router", "game_router", "websocket_router"]
