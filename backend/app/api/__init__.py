"""
API layer - Routes and dependencies.
"""
from .routes import admin_router, game_router, websocket_router

__all__ = ["admin_router", "game_router", "websocket_router"]
