# DungeonAI Backend

A multiplayer dungeon crawler with AI-generated content, built with FastAPI.

## Project Structure

```
backend/
├── requirements.txt          # Python dependencies
├── app/                      # Main application package
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   │
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py      # App settings & environment variables
│   │   └── data/            # JSON configuration files
│   │       ├── monsters.json
│   │       └── spawn_rates.json
│   │
│   ├── api/                 # API layer (HTTP/WebSocket endpoints)
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── admin.py     # Admin endpoints (map generation, saves)
│   │       ├── game.py      # Game state endpoints
│   │       └── websocket.py # WebSocket handler for multiplayer
│   │
│   ├── core/                # Core game systems
│   │   ├── __init__.py
│   │   ├── game_manager.py  # Central game orchestrator
│   │   ├── game_loop.py     # Background tick loop
│   │   └── events.py        # Event bus for pub/sub messaging
│   │
│   ├── domain/              # Domain layer (entities & business logic)
│   │   ├── __init__.py
│   │   ├── entities/        # Game entities
│   │   │   ├── __init__.py
│   │   │   ├── player.py    # Player entity
│   │   │   ├── monster.py   # Monster entity & stats
│   │   │   └── room.py      # Room entity
│   │   ├── map/             # Map generation & tiles
│   │   │   ├── __init__.py
│   │   │   ├── tiles.py     # Tile type constants
│   │   │   ├── dungeon.py   # Dungeon data structure
│   │   │   └── generator.py # Procedural dungeon generator
│   │   ├── combat/          # Combat system (future)
│   │   │   └── __init__.py
│   │   └── inventory/       # Inventory system (future)
│   │       └── __init__.py
│   │
│   ├── services/            # Service layer (external integrations)
│   │   ├── __init__.py
│   │   ├── ai_service.py    # Azure OpenAI room descriptions
│   │   ├── monster_service.py # Monster spawning & AI behavior
│   │   └── storage_service.py # Game save/load persistence
│   │
│   ├── static/              # Served static files (built frontend)
│   │   └── ...
│   ├── templates/           # Jinja2 templates
│   │   └── ...
│   └── saves/               # Game save files
│       └── ...
```

## Architecture Principles

### Layered Architecture

1. **API Layer** (`api/`)
   - Handles HTTP requests and WebSocket connections
   - Validates input using Pydantic models
   - Delegates to core systems

2. **Core Layer** (`core/`)
   - Central game orchestration
   - State management
   - Event-driven communication

3. **Domain Layer** (`domain/`)
   - Pure business logic
   - Entities with behavior
   - No external dependencies

4. **Services Layer** (`services/`)
   - External integrations (AI, storage)
   - Reusable business services
   - Singleton instances

### Event System

The `EventBus` in `core/events.py` enables loose coupling:
- Components can emit events without knowing subscribers
- Async and sync handlers supported
- Event history for debugging

### Dependency Injection

Use `api/deps.py` for injecting services into route handlers.

## Development

### Running the Server

```bash
# From the project root
./start.sh

# Or manually
cd backend
uvicorn app.main:app --reload --port 8000
```

### Adding New Features

1. **New Entity**: Add to `domain/entities/`
2. **New API Endpoint**: Add to `api/routes/`
3. **New Service**: Add to `services/`
4. **New Game System**: Add to `core/`

### Configuration

Environment variables:
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_DEPLOYMENT` - Model deployment name (default: gpt-4)
- `GAME_SAVE_PATH` - Custom save file location
- `DEBUG` - Enable debug mode

## Future Expansion Areas

- `domain/combat/` - Combat mechanics, damage, initiative
- `domain/inventory/` - Items, equipment, loot
- `services/quest_service.py` - Quest system
- `domain/entities/npc.py` - Non-player characters
- `api/routes/auth.py` - Authentication/accounts
