"""
DungeonAI - Main FastAPI application entry point.
Multi-game architecture with lobby system.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import asyncio

from .config import settings
from .services import game_registry, player_registry, get_storage_backend_name
from .services.player_stats import player_stats_tracker
from .services.monster_service import monster_service
from .api import admin_router, game_router, websocket_router, auth_router
from .db import mongodb_manager


async def cleanup_task():
    """Periodic cleanup of inactive and completed games."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        try:
            await game_registry.cleanup_games()
        except Exception as e:
            print(f"[Main] Error during cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Startup
    # Initialize MongoDB connection if configured
    if settings.mongodb.is_enabled:
        try:
            print(f"[Main] Attempting MongoDB connection to: {settings.mongodb.database_name}")
            await mongodb_manager.connect(
                settings.mongodb.connection_string,
                settings.mongodb.database_name
            )
            print(f"[Main] ✓ MongoDB connected successfully: {settings.mongodb.database_name}")
            print(f"[Main] ✓ Storage backend: {get_storage_backend_name()}")

            # Initialize MonsterService with MongoDB species store
            monster_service.initialize()

        except Exception as e:
            error_msg = f"MongoDB connection failed: {e}"
            print(f"[Main] ✗ {error_msg}")

            if settings.mongodb.required:
                # MongoDB is required, fail startup
                print(f"[Main] ✗ MONGODB_REQUIRED=true, cannot start without MongoDB")
                raise RuntimeError(error_msg)
            else:
                # Fallback to JSON storage
                print(f"[Main] ✗ Falling back to JSON storage (set MONGODB_REQUIRED=true to prevent this)")
                print(f"[Main] ✗ Storage backend: {get_storage_backend_name()}")
                monster_service.initialize()
    else:
        print(f"[Main] MongoDB not configured, using JSON storage")
        print(f"[Main] Storage backend: {get_storage_backend_name()}")
        monster_service.initialize()

    # Clean up legacy single-game save if it exists
    legacy_save = settings.storage.save_path / "current.json"
    if legacy_save.exists():
        try:
            legacy_save.unlink()
            print("[Main] Removed legacy current.json save file")
        except Exception as e:
            print(f"[Main] Warning: Could not remove legacy save: {e}")

    # Restore any saved games
    await game_registry.restore_games()

    # Load player registry
    await player_registry.start()

    # Start player stats tracker (subscribes to events for XP/kills tracking)
    await player_stats_tracker.start()

    print(f"[Main] Game registry initialized with {len(game_registry.games)} game(s)")
    print(f"[Main] Player registry loaded with {len(player_registry.players)} player(s)")
    print(f"[Main] ════════════════════════════════════════════════════")
    print(f"[Main] STORAGE BACKEND: {get_storage_backend_name()}")
    print(f"[Main] ════════════════════════════════════════════════════")

    # Start cleanup background task
    cleanup_handle = asyncio.create_task(cleanup_task())

    yield

    # Shutdown
    cleanup_handle.cancel()
    try:
        await cleanup_handle
    except asyncio.CancelledError:
        pass

    # Save all active games
    for game_id, game in game_registry.games.items():
        await game.force_save()

    # Stop player stats tracker (saves stats)
    await player_stats_tracker.stop()

    # Save player registry
    await player_registry.save()

    # Disconnect MongoDB
    if mongodb_manager.is_connected:
        await mongodb_manager.disconnect()

    print("[Main] All games saved and shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DungeonAI",
        description="A multiplayer dungeon crawler with AI-generated content",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware for cookie-based authentication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:8000",  # Production server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000"
        ],
        allow_credentials=True,  # Required for cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files directory
    if settings.static_dir.exists():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    
    # Setup templates
    templates = Jinja2Templates(directory=settings.templates_dir)
    
    # Include routers
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(game_router)
    app.include_router(websocket_router)
    
    @app.get("/", response_class=HTMLResponse)
    async def read_root(request: Request):
        """Serve the main game page."""
        index_path = settings.static_dir / "index.html"
        if index_path.exists():
            with open(index_path, 'r') as f:
                html_content = f.read()
            return HTMLResponse(
                content=html_content,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        else:
            return templates.TemplateResponse(request=request, name="index.html")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
