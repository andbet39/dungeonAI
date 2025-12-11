"""
Application settings and environment configuration.
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AzureOpenAISettings:
    """Azure OpenAI configuration."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY"))
    endpoint: Optional[str] = field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT"))
    deployment: str = field(default_factory=lambda: os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"))
    api_version: str = "2024-02-15-preview"
    
    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key and self.endpoint)


@dataclass
class GameSettings:
    """Game-related settings."""
    default_map_width: int = 80
    default_map_height: int = 50
    default_room_count: int = 15
    tick_interval: float = 0.5  # seconds
    autosave_interval: int = 300  # seconds (5 minutes)
    viewport_width: int = 60
    viewport_height: int = 30


@dataclass
class AISettings:
    """AI/Intelligence tuning knobs."""

    max_generation_cap: int = field(
        default_factory=lambda: int(os.getenv("AI_MAX_GENERATION_CAP", "10"))
    )
    generation_inheritance_ratio: float = field(
        default_factory=lambda: float(os.getenv("AI_INHERITANCE_RATIO", "0.7"))
    )
    debug_enabled: bool = field(
        default_factory=lambda: os.getenv("AI_DEBUG", "false").lower() == "true"
    )

    def clamp(self) -> None:
        self.max_generation_cap = max(1, self.max_generation_cap)
        self.generation_inheritance_ratio = max(
            0.0, min(1.0, self.generation_inheritance_ratio)
        )


@dataclass
class MultiGameSettings:
    """Multi-game hosting settings."""
    max_players_per_game: int = field(
        default_factory=lambda: int(os.getenv("MAX_PLAYERS_PER_GAME", "4"))
    )
    game_inactive_timeout_minutes: int = field(
        default_factory=lambda: int(os.getenv("GAME_INACTIVE_TIMEOUT_MINUTES", "30"))
    )
    completed_game_grace_period_minutes: int = field(
        default_factory=lambda: int(os.getenv("COMPLETED_GAME_GRACE_PERIOD_MINUTES", "5"))
    )


@dataclass
class MongoDBSettings:
    """MongoDB configuration."""
    connection_string: Optional[str] = field(
        default_factory=lambda: os.getenv("MONGODB_CONNECTION_STRING")
    )
    database_name: str = field(
        default_factory=lambda: os.getenv("MONGODB_DATABASE", "dungeonai_db")
    )
    required: bool = field(
        default_factory=lambda: os.getenv("MONGODB_REQUIRED", "true").lower() == "true"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if MongoDB is configured and should be used."""
        return bool(self.connection_string)


@dataclass
class StorageSettings:
    """Storage/persistence settings."""
    _save_path: Path = field(init=False, repr=False)
    _games_path: Path = field(init=False, repr=False)
    _players_file: Path = field(init=False, repr=False)

    def __post_init__(self):
        # Default to saves directory relative to app folder
        base_dir = Path(__file__).resolve().parent.parent
        env_path = os.getenv("GAME_SAVE_PATH")
        self._save_path = Path(env_path).resolve() if env_path else base_dir / "saves"
        self._save_path.mkdir(parents=True, exist_ok=True)

        # Per-game saves directory
        self._games_path = self._save_path / "games"
        self._games_path.mkdir(parents=True, exist_ok=True)

        # Players registry file
        self._players_file = self._save_path / "players.json"

    @property
    def save_path(self) -> Path:
        return self._save_path

    @property
    def games_path(self) -> Path:
        return self._games_path

    @property
    def players_file(self) -> Path:
        return self._players_file


@dataclass
class Settings:
    """Main application settings container."""
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    config_data_dir: Path = field(init=False)
    static_dir: Path = field(init=False)
    templates_dir: Path = field(init=False)

    # Sub-settings
    azure_openai: AzureOpenAISettings = field(default_factory=AzureOpenAISettings)
    game: GameSettings = field(default_factory=GameSettings)
    ai: AISettings = field(default_factory=AISettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    multi_game: MultiGameSettings = field(default_factory=MultiGameSettings)
    mongodb: MongoDBSettings = field(default_factory=MongoDBSettings)

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    def __post_init__(self):
        self.config_data_dir = self.base_dir / "config" / "data"
        self.static_dir = self.base_dir / "static"
        self.templates_dir = self.base_dir / "templates"
        self.ai.clamp()


# Global settings instance
settings = Settings()
