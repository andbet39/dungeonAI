"""
Event system for DungeonAI.
Provides a simple pub/sub mechanism for game events.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional
from datetime import datetime
import asyncio


class EventType(Enum):
    """Types of game events."""
    # Player events
    PLAYER_JOINED = auto()
    PLAYER_LEFT = auto()
    PLAYER_MOVED = auto()
    PLAYER_INTERACTED = auto()
    PLAYER_ENTERED_ROOM = auto()
    PLAYER_TOOK_DAMAGE = auto()
    PLAYER_DIED = auto()
    
    # Monster events
    MONSTER_SPAWNED = auto()
    MONSTER_MOVED = auto()
    MONSTER_ATTACKED = auto()
    MONSTER_DIED = auto()
    
    # Game events
    STATE_CHANGED = auto()
    MAP_REGENERATED = auto()
    GAME_SAVED = auto()
    GAME_LOADED = auto()
    
    # Room events
    DOOR_OPENED = auto()
    DOOR_CLOSED = auto()
    ROOM_DISCOVERED = auto()
    
    # Combat events (future)
    COMBAT_STARTED = auto()
    COMBAT_ENDED = auto()
    DAMAGE_DEALT = auto()
    
    # Item events (future)
    ITEM_PICKED_UP = auto()
    ITEM_USED = auto()
    ITEM_DROPPED = auto()


@dataclass
class GameEvent:
    """Represents a game event."""
    type: EventType
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source_id: Optional[str] = None  # ID of entity that triggered event
    target_id: Optional[str] = None  # ID of entity affected by event
    
    def to_dict(self) -> dict:
        """Serialize event to dictionary."""
        return {
            "type": self.type.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "target_id": self.target_id,
        }


class EventBus:
    """
    Simple event bus for pub/sub messaging.
    Allows game systems to communicate without tight coupling.
    """
    
    _instance: Optional["EventBus"] = None
    
    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._handlers: dict[EventType, list[Callable]] = {}
        self._async_handlers: dict[EventType, list[Callable]] = {}
        self._event_history: list[GameEvent] = []
        self._max_history = 1000
        self._initialized = True
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """
        Subscribe to an event type with a synchronous handler.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event is emitted
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def     subscribe_async(self, event_type: EventType, handler: Callable) -> None:
        """
        Subscribe to an event type with an async handler.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event is emitted
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass
        if event_type in self._async_handlers:
            try:
                self._async_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    def emit(self, event: GameEvent) -> None:
        """
        Emit an event synchronously.
        
        Args:
            event: The event to emit
        """
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Call sync handlers
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"[EventBus] Error in handler for {event.type}: {e}")
    
    async def emit_async(self, event: GameEvent) -> None:
        """
        Emit an event asynchronously.
        
        Args:
            event: The event to emit
        """
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Call sync handlers
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"[EventBus] Error in sync handler for {event.type}: {e}")
        
        # Call async handlers
        if event.type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event.type]:
                tasks.append(handler(event))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"[EventBus] Error in async handler for {event.type}: {result}")
    
    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> list[GameEvent]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self._event_history if e.type == event_type]
        else:
            filtered = self._event_history
        return filtered[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()


# Global event bus instance
event_bus = EventBus()
