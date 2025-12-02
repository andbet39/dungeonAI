"""
Core game systems - Game instances, registry, and events.
"""
from .game import Game
from .game_registry import GameRegistry, GameInfo, game_registry
from .events import GameEvent, EventType

# Backward compatibility - import legacy singleton if needed
try:
    from .game_manager import GameManager, game_manager
    from .game_loop import GameLoop, game_loop
except ImportError:
    GameManager = Game
    game_manager = None
    GameLoop = None
    game_loop = None

__all__ = [
    "Game",
    "GameRegistry", "GameInfo", "game_registry",
    "GameManager", "game_manager",
    "GameLoop", "game_loop",
    "GameEvent", "EventType",
]
