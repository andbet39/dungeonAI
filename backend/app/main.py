"""
DungeonAI - Main FastAPI application entry point.
Multi-game architecture with lobby system.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import asyncio

from .config import settings
from .services import game_registry, player_registry
from .services.player_stats import player_stats_tracker
from .api import admin_router, game_router, websocket_router


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
    print("[Main] All games saved and shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DungeonAI",
        description="A multiplayer dungeon crawler with AI-generated content",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Mount static files directory
    if settings.static_dir.exists():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    
    # Setup templates
    templates = Jinja2Templates(directory=settings.templates_dir)
    
    # Include routers
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
