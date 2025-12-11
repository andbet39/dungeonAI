"""
Player Stats Tracker - Modular cross-game statistics tracking.
Uses event bus pattern for extensibility.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto

from ..core.events import event_bus, GameEvent, EventType
from . import storage_service


# D&D 5e Challenge Rating to XP mapping
XP_BY_CHALLENGE_RATING: Dict[float, int] = {
    0.0: 10,
    0.125: 25,
    0.25: 50,
    0.5: 100,
    1.0: 200,
    2.0: 450,
    3.0: 700,
    4.0: 1100,
    5.0: 1800,
    6.0: 2300,
    7.0: 2900,
    8.0: 3900,
}


def get_xp_for_cr(challenge_rating: float) -> int:
    """Get XP reward for a given challenge rating."""
    # Find the closest CR that doesn't exceed the given one
    if challenge_rating in XP_BY_CHALLENGE_RATING:
        return XP_BY_CHALLENGE_RATING[challenge_rating]
    # For CRs not in the table, interpolate or use closest lower
    sorted_crs = sorted(XP_BY_CHALLENGE_RATING.keys())
    for cr in reversed(sorted_crs):
        if cr <= challenge_rating:
            return XP_BY_CHALLENGE_RATING[cr]
    return XP_BY_CHALLENGE_RATING[0.0]


class StatType(Enum):
    """Types of trackable statistics."""
    MONSTERS_KILLED = auto()
    ROOMS_VISITED = auto()
    DAMAGE_DEALT = auto()
    DAMAGE_TAKEN = auto()
    DEATHS = auto()
    GAMES_COMPLETED = auto()
    CRITICAL_HITS = auto()
    # Future extensibility
    ITEMS_COLLECTED = auto()
    EXPERIENCE_EARNED = auto()
    GOLD_EARNED = auto()


@dataclass
class PlayerStats:
    """Player statistics container."""
    token: str
    monsters_killed: int = 0
    rooms_visited: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    deaths: int = 0
    games_completed: int = 0
    critical_hits: int = 0
    # Future stats
    items_collected: int = 0
    experience_earned: int = 0
    gold_earned: int = 0
    # Kill tracking by monster type
    kills_by_type: Dict[str, int] = field(default_factory=dict)
    # Nickname tracking
    nickname: str = ""
    kills_at_last_nickname: int = 0
    # Metadata
    first_game_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlayerStats":
        # Handle missing fields for forward compatibility
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def increment(self, stat_type: StatType, amount: int = 1) -> None:
        """Increment a stat by amount."""
        self.last_updated = datetime.now().isoformat()
        
        if stat_type == StatType.MONSTERS_KILLED:
            self.monsters_killed += amount
        elif stat_type == StatType.ROOMS_VISITED:
            self.rooms_visited += amount
        elif stat_type == StatType.DAMAGE_DEALT:
            self.damage_dealt += amount
        elif stat_type == StatType.DAMAGE_TAKEN:
            self.damage_taken += amount
        elif stat_type == StatType.DEATHS:
            self.deaths += amount
        elif stat_type == StatType.GAMES_COMPLETED:
            self.games_completed += amount
        elif stat_type == StatType.CRITICAL_HITS:
            self.critical_hits += amount
        elif stat_type == StatType.ITEMS_COLLECTED:
            self.items_collected += amount
        elif stat_type == StatType.EXPERIENCE_EARNED:
            self.experience_earned += amount
        elif stat_type == StatType.GOLD_EARNED:
            self.gold_earned += amount
    
    def record_monster_kill(self, monster_type: str, challenge_rating: float) -> int:
        """
        Record a monster kill and award XP.
        
        Args:
            monster_type: Type of monster killed (e.g., 'goblin', 'orc')
            challenge_rating: The monster's challenge rating
        
        Returns:
            XP awarded for this kill
        """
        self.last_updated = datetime.now().isoformat()
        
        # Increment kills by type
        if monster_type not in self.kills_by_type:
            self.kills_by_type[monster_type] = 0
        self.kills_by_type[monster_type] += 1
        
        # Increment total kills
        self.monsters_killed += 1
        
        # Calculate and award XP
        xp_earned = get_xp_for_cr(challenge_rating)
        self.experience_earned += xp_earned
        
        return xp_earned
    
    def needs_nickname_refresh(self) -> bool:
        """Check if nickname should be regenerated (kills increased by 50%)."""
        if self.kills_at_last_nickname == 0:
            # Generate first nickname after 5 kills
            return self.monsters_killed >= 5
        
        # Check if kills increased by 50%
        threshold = int(self.kills_at_last_nickname * 1.5)
        return self.monsters_killed >= threshold
    
    def get_top_kill_type(self) -> Optional[tuple[str, int]]:
        """Get the monster type with the most kills."""
        if not self.kills_by_type:
            return None
        top_type = max(self.kills_by_type.keys(), key=lambda k: self.kills_by_type[k])
        return (top_type, self.kills_by_type[top_type])


# Type for stat handlers
StatHandler = Callable[[str, GameEvent], None]


class PlayerStatsTracker:
    """
    Tracks player statistics across games using event-driven architecture.
    Modular design allows easy addition of new stat types.
    """
    
    _instance: Optional["PlayerStatsTracker"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "PlayerStatsTracker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._stats: Dict[str, PlayerStats] = {}
        self._handlers: Dict[EventType, list[StatHandler]] = {}
        self._lock = asyncio.Lock()
        self._dirty = False
        self._save_task: Optional[asyncio.Task] = None
        self._initialized = True
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register built-in stat tracking handlers."""
        # Monster kill tracking
        self.register_handler(EventType.MONSTER_DIED, self._handle_monster_killed)
        
        # Room visit tracking
        self.register_handler(EventType.PLAYER_ENTERED_ROOM, self._handle_room_entered)
        
        # Damage tracking
        self.register_handler(EventType.DAMAGE_DEALT, self._handle_damage_dealt)
        
        # Death tracking
        self.register_handler(EventType.PLAYER_DIED, self._handle_player_died)
    
    def register_handler(self, event_type: EventType, handler: StatHandler) -> None:
        """Register a stat handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def start(self) -> None:
        """Start the tracker and load stats."""
        await self._load()
        self._start_periodic_save()
        self._subscribe_to_events()
        print(f"[PlayerStatsTracker] Started with stats for {len(self._stats)} players")
    
    async def stop(self) -> None:
        """Stop and save stats."""
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        await self._save()
        print("[PlayerStatsTracker] Stopped")
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to game events for stat tracking."""
        for event_type in self._handlers:
            event_bus.subscribe_async(event_type, self._on_event)
    
    async def _on_event(self, event: GameEvent) -> None:
        """Handle incoming game events."""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                # Get player token from event data
                token = event.data.get("player_token") if event.data else None
                if token:
                    handler(token, event)
                    self._dirty = True
            except Exception as e:
                print(f"[PlayerStatsTracker] Handler error: {e}")
    
    def _start_periodic_save(self) -> None:
        if self._save_task is not None:
            return
        
        async def periodic_save():
            while True:
                await asyncio.sleep(120)  # Save every 2 minutes
                if self._dirty:
                    await self._save()
        
        self._save_task = asyncio.create_task(periodic_save())
    
    async def _load(self) -> None:
        """Load stats from disk."""
        # Stats are stored alongside player registry
        registry_data = await storage_service.load_player_registry()
        if registry_data and "stats" in registry_data:
            self._stats = {
                token: PlayerStats.from_dict({"token": token, **data})
                for token, data in registry_data.get("stats", {}).items()
            }
    
    async def _save(self) -> None:
        """Save stats to disk."""
        # Load current registry to merge
        registry_data = await storage_service.load_player_registry() or {}
        registry_data["stats"] = {token: s.to_dict() for token, s in self._stats.items()}
        await storage_service.save_player_registry(registry_data)
        self._dirty = False
    
    def get_or_create_stats(self, token: str) -> PlayerStats:
        """Get stats for a player, creating if needed."""
        if token not in self._stats:
            self._stats[token] = PlayerStats(token=token)
            self._dirty = True
        return self._stats[token]
    
    def get_stats(self, token: str) -> Optional[PlayerStats]:
        """Get stats for a player."""
        return self._stats.get(token)
    
    def increment_stat(self, token: str, stat_type: StatType, amount: int = 1) -> None:
        """Increment a stat for a player."""
        stats = self.get_or_create_stats(token)
        stats.increment(stat_type, amount)
        self._dirty = True
    
    # ============== Default Handlers ==============
    
    def _handle_monster_killed(self, token: str, event: GameEvent) -> None:
        """Track monster kills with XP rewards."""
        if not event.data:
            # Fallback to simple increment if no data
            self.increment_stat(token, StatType.MONSTERS_KILLED)
            return
        
        monster_type = event.data.get("monster_type", "unknown")
        challenge_rating = event.data.get("challenge_rating", 0.25)
        
        stats = self.get_or_create_stats(token)
        xp_earned = stats.record_monster_kill(monster_type, challenge_rating)
        self._dirty = True
        
        print(f"[PlayerStatsTracker] Player {token[:8]} killed {monster_type}, earned {xp_earned} XP (total: {stats.experience_earned} XP, {stats.monsters_killed} kills)")
    
    def _handle_room_entered(self, token: str, event: GameEvent) -> None:
        """Track room visits."""
        # Only count first visit
        if event.data and event.data.get("first_visit", True):
            self.increment_stat(token, StatType.ROOMS_VISITED)
    
    def _handle_damage_dealt(self, token: str, event: GameEvent) -> None:
        """Track damage dealt/taken."""
        if not event.data:
            return
        
        damage = event.data.get("damage", 0)
        is_player_source = event.data.get("is_player_source", False)
        is_critical = event.data.get("is_critical", False)
        
        if is_player_source:
            self.increment_stat(token, StatType.DAMAGE_DEALT, damage)
            if is_critical:
                self.increment_stat(token, StatType.CRITICAL_HITS)
        else:
            self.increment_stat(token, StatType.DAMAGE_TAKEN, damage)
    
    def _handle_player_died(self, token: str, event: GameEvent) -> None:
        """Track player deaths."""
        self.increment_stat(token, StatType.DEATHS)
        print(f"[PlayerStatsTracker] Player {token[:8]} died")
    
    # ============== Public API for Manual Tracking ==============
    
    def record_death(self, token: str) -> None:
        """Record a player death."""
        self.increment_stat(token, StatType.DEATHS)
    
    def record_game_completed(self, token: str) -> None:
        """Record a game completion."""
        self.increment_stat(token, StatType.GAMES_COMPLETED)
    
    def get_leaderboard(self, stat_type: StatType, limit: int = 10) -> list[dict]:
        """Get top players for a stat type."""
        stats_list = list(self._stats.values())
        
        # Sort by the requested stat
        key_map = {
            StatType.MONSTERS_KILLED: lambda s: s.monsters_killed,
            StatType.ROOMS_VISITED: lambda s: s.rooms_visited,
            StatType.DAMAGE_DEALT: lambda s: s.damage_dealt,
            StatType.GAMES_COMPLETED: lambda s: s.games_completed,
            StatType.EXPERIENCE_EARNED: lambda s: s.experience_earned,
        }
        
        key_fn = key_map.get(stat_type, lambda s: 0)
        sorted_stats = sorted(stats_list, key=key_fn, reverse=True)[:limit]
        
        return [{"token": s.token, "value": key_fn(s)} for s in sorted_stats]
    
    def get_xp_leaderboard(self, limit: int = 10) -> list[dict]:
        """Get top players by XP with full stats for leaderboard display."""
        stats_list = list(self._stats.values())
        sorted_stats = sorted(stats_list, key=lambda s: s.experience_earned, reverse=True)[:limit]
        
        return [
            {
                "token": s.token,
                "experience": s.experience_earned,
                "kills": s.monsters_killed,
                "nickname": s.nickname,
                "top_kill": s.get_top_kill_type(),
            }
            for s in sorted_stats
        ]
    
    async def update_nickname(self, token: str, nickname: str) -> None:
        """Update a player's nickname and reset the kill threshold."""
        stats = self.get_or_create_stats(token)
        stats.nickname = nickname
        stats.kills_at_last_nickname = stats.monsters_killed
        stats.last_updated = datetime.now().isoformat()
        self._dirty = True


# Global stats tracker instance
player_stats_tracker = PlayerStatsTracker()
