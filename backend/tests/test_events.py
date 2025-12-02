"""
Tests for Event System (EventBus, GameEvent, EventType).

Tests cover:
- GameEvent creation and serialization
- EventBus subscription (sync and async)
- Event emission and handler invocation
- Event history management
- Unsubscription
- Error handling in handlers
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from app.core.events import EventType, GameEvent, EventBus


# ============================================================================
# GAMEEVENT TESTS
# ============================================================================

class TestGameEventCreation:
    """Tests for GameEvent dataclass."""
    
    def test_create_event_with_type(self):
        """Creating an event should set the type correctly."""
        event = GameEvent(type=EventType.PLAYER_MOVED)
        
        assert event.type == EventType.PLAYER_MOVED
        assert event.data == {}
        assert event.source_id is None
        assert event.target_id is None
    
    def test_create_event_with_all_fields(self):
        """Event should store all provided fields."""
        event = GameEvent(
            type=EventType.DAMAGE_DEALT,
            data={"amount": 10, "damage_type": "slashing"},
            source_id="player-001",
            target_id="monster-001"
        )
        
        assert event.type == EventType.DAMAGE_DEALT
        assert event.data["amount"] == 10
        assert event.data["damage_type"] == "slashing"
        assert event.source_id == "player-001"
        assert event.target_id == "monster-001"
    
    def test_event_has_timestamp(self):
        """Event should have a timestamp on creation."""
        before = datetime.now()
        event = GameEvent(type=EventType.PLAYER_JOINED)
        after = datetime.now()
        
        assert event.timestamp >= before
        assert event.timestamp <= after
    
    def test_event_to_dict(self):
        """to_dict should serialize event correctly."""
        event = GameEvent(
            type=EventType.MONSTER_SPAWNED,
            data={"monster_type": "goblin"},
            source_id="game",
            target_id="monster-001"
        )
        
        data = event.to_dict()
        
        assert data["type"] == "MONSTER_SPAWNED"
        assert data["data"] == {"monster_type": "goblin"}
        assert data["source_id"] == "game"
        assert data["target_id"] == "monster-001"
        assert "timestamp" in data


# ============================================================================
# EVENTBUS TESTS
# ============================================================================

@pytest.fixture
def fresh_event_bus():
    """Create a fresh EventBus for testing (bypass singleton)."""
    # Create a non-singleton instance for testing
    bus = object.__new__(EventBus)
    bus._handlers = {}
    bus._async_handlers = {}
    bus._event_history = []
    bus._max_history = 1000
    bus._initialized = True
    return bus


class TestEventBusSubscription:
    """Tests for subscribing to events."""
    
    def test_subscribe_sync_handler(self, fresh_event_bus):
        """Subscribing should register a sync handler."""
        handler = MagicMock()
        
        fresh_event_bus.subscribe(EventType.PLAYER_MOVED, handler)
        
        assert EventType.PLAYER_MOVED in fresh_event_bus._handlers
        assert handler in fresh_event_bus._handlers[EventType.PLAYER_MOVED]
    
    def test_subscribe_async_handler(self, fresh_event_bus):
        """Subscribing async should register an async handler."""
        handler = AsyncMock()
        
        fresh_event_bus.subscribe_async(EventType.PLAYER_MOVED, handler)
        
        assert EventType.PLAYER_MOVED in fresh_event_bus._async_handlers
        assert handler in fresh_event_bus._async_handlers[EventType.PLAYER_MOVED]
    
    def test_multiple_handlers_same_event(self, fresh_event_bus):
        """Multiple handlers can subscribe to same event type."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        fresh_event_bus.subscribe(EventType.COMBAT_STARTED, handler1)
        fresh_event_bus.subscribe(EventType.COMBAT_STARTED, handler2)
        
        assert len(fresh_event_bus._handlers[EventType.COMBAT_STARTED]) == 2
    
    def test_unsubscribe_handler(self, fresh_event_bus):
        """Unsubscribing should remove the handler."""
        handler = MagicMock()
        fresh_event_bus.subscribe(EventType.PLAYER_DIED, handler)
        
        fresh_event_bus.unsubscribe(EventType.PLAYER_DIED, handler)
        
        assert handler not in fresh_event_bus._handlers.get(EventType.PLAYER_DIED, [])
    
    def test_unsubscribe_nonexistent_handler(self, fresh_event_bus):
        """Unsubscribing non-existent handler should not raise."""
        handler = MagicMock()
        
        # Should not raise
        fresh_event_bus.unsubscribe(EventType.ITEM_DROPPED, handler)


class TestEventBusEmit:
    """Tests for emitting events."""
    
    def test_emit_calls_handler(self, fresh_event_bus):
        """Emitting an event should call subscribed handlers."""
        handler = MagicMock()
        fresh_event_bus.subscribe(EventType.PLAYER_JOINED, handler)
        
        event = GameEvent(type=EventType.PLAYER_JOINED, data={"player_id": "p1"})
        fresh_event_bus.emit(event)
        
        handler.assert_called_once_with(event)
    
    def test_emit_calls_multiple_handlers(self, fresh_event_bus):
        """Emitting should call all subscribed handlers."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        fresh_event_bus.subscribe(EventType.MONSTER_DIED, handler1)
        fresh_event_bus.subscribe(EventType.MONSTER_DIED, handler2)
        
        event = GameEvent(type=EventType.MONSTER_DIED)
        fresh_event_bus.emit(event)
        
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
    
    def test_emit_does_not_call_unrelated_handlers(self, fresh_event_bus):
        """Emitting should not call handlers for different event types."""
        move_handler = MagicMock()
        damage_handler = MagicMock()
        fresh_event_bus.subscribe(EventType.PLAYER_MOVED, move_handler)
        fresh_event_bus.subscribe(EventType.DAMAGE_DEALT, damage_handler)
        
        event = GameEvent(type=EventType.PLAYER_MOVED)
        fresh_event_bus.emit(event)
        
        move_handler.assert_called_once()
        damage_handler.assert_not_called()
    
    def test_emit_stores_in_history(self, fresh_event_bus):
        """Emitting should store event in history."""
        event = GameEvent(type=EventType.GAME_SAVED)
        fresh_event_bus.emit(event)
        
        assert event in fresh_event_bus._event_history
    
    def test_handler_error_does_not_stop_other_handlers(self, fresh_event_bus, capsys):
        """Error in one handler should not prevent others from running."""
        failing_handler = MagicMock(side_effect=ValueError("Test error"))
        working_handler = MagicMock()
        
        fresh_event_bus.subscribe(EventType.STATE_CHANGED, failing_handler)
        fresh_event_bus.subscribe(EventType.STATE_CHANGED, working_handler)
        
        event = GameEvent(type=EventType.STATE_CHANGED)
        fresh_event_bus.emit(event)
        
        failing_handler.assert_called_once()
        working_handler.assert_called_once()  # Should still be called


class TestEventBusAsyncEmit:
    """Tests for async event emission."""
    
    @pytest.mark.asyncio
    async def test_emit_async_calls_sync_handlers(self, fresh_event_bus):
        """emit_async should call sync handlers."""
        handler = MagicMock()
        fresh_event_bus.subscribe(EventType.PLAYER_LEFT, handler)
        
        event = GameEvent(type=EventType.PLAYER_LEFT)
        await fresh_event_bus.emit_async(event)
        
        handler.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_emit_async_calls_async_handlers(self, fresh_event_bus):
        """emit_async should await async handlers."""
        handler = AsyncMock()
        fresh_event_bus.subscribe_async(EventType.COMBAT_ENDED, handler)
        
        event = GameEvent(type=EventType.COMBAT_ENDED)
        await fresh_event_bus.emit_async(event)
        
        handler.assert_awaited_once_with(event)
    
    @pytest.mark.asyncio
    async def test_emit_async_calls_both_handler_types(self, fresh_event_bus):
        """emit_async should call both sync and async handlers."""
        sync_handler = MagicMock()
        async_handler = AsyncMock()
        
        fresh_event_bus.subscribe(EventType.ITEM_PICKED_UP, sync_handler)
        fresh_event_bus.subscribe_async(EventType.ITEM_PICKED_UP, async_handler)
        
        event = GameEvent(type=EventType.ITEM_PICKED_UP)
        await fresh_event_bus.emit_async(event)
        
        sync_handler.assert_called_once()
        async_handler.assert_awaited_once()


class TestEventBusHistory:
    """Tests for event history management."""
    
    def test_get_recent_events(self, fresh_event_bus):
        """get_recent_events should return events from history."""
        event1 = GameEvent(type=EventType.PLAYER_MOVED)
        event2 = GameEvent(type=EventType.MONSTER_MOVED)
        fresh_event_bus.emit(event1)
        fresh_event_bus.emit(event2)
        
        events = fresh_event_bus.get_recent_events()
        
        assert event1 in events
        assert event2 in events
    
    def test_get_recent_events_filtered_by_type(self, fresh_event_bus):
        """get_recent_events should filter by event type."""
        move_event = GameEvent(type=EventType.PLAYER_MOVED)
        damage_event = GameEvent(type=EventType.DAMAGE_DEALT)
        fresh_event_bus.emit(move_event)
        fresh_event_bus.emit(damage_event)
        
        events = fresh_event_bus.get_recent_events(EventType.PLAYER_MOVED)
        
        assert move_event in events
        assert damage_event not in events
    
    def test_get_recent_events_respects_limit(self, fresh_event_bus):
        """get_recent_events should respect limit parameter."""
        for i in range(10):
            fresh_event_bus.emit(GameEvent(type=EventType.STATE_CHANGED))
        
        events = fresh_event_bus.get_recent_events(limit=5)
        
        assert len(events) == 5
    
    def test_history_max_size_enforced(self, fresh_event_bus):
        """History should not exceed max size."""
        fresh_event_bus._max_history = 5
        
        for i in range(10):
            fresh_event_bus.emit(GameEvent(
                type=EventType.PLAYER_MOVED,
                data={"index": i}
            ))
        
        assert len(fresh_event_bus._event_history) == 5
        # Should keep the most recent ones
        assert fresh_event_bus._event_history[0].data["index"] == 5
        assert fresh_event_bus._event_history[-1].data["index"] == 9
    
    def test_clear_history(self, fresh_event_bus):
        """clear_history should empty the history."""
        fresh_event_bus.emit(GameEvent(type=EventType.GAME_LOADED))
        fresh_event_bus.emit(GameEvent(type=EventType.PLAYER_JOINED))
        
        fresh_event_bus.clear_history()
        
        assert len(fresh_event_bus._event_history) == 0


class TestEventBusSingleton:
    """Tests for EventBus singleton behavior."""
    
    def test_event_bus_is_singleton(self):
        """Multiple EventBus() calls should return same instance."""
        bus1 = EventBus()
        bus2 = EventBus()
        
        assert bus1 is bus2


# ============================================================================
# EVENTTYPE TESTS
# ============================================================================

class TestEventType:
    """Tests for EventType enum."""
    
    def test_player_events_exist(self):
        """Player event types should be defined."""
        assert EventType.PLAYER_JOINED
        assert EventType.PLAYER_LEFT
        assert EventType.PLAYER_MOVED
        assert EventType.PLAYER_TOOK_DAMAGE
        assert EventType.PLAYER_DIED
    
    def test_monster_events_exist(self):
        """Monster event types should be defined."""
        assert EventType.MONSTER_SPAWNED
        assert EventType.MONSTER_MOVED
        assert EventType.MONSTER_ATTACKED
        assert EventType.MONSTER_DIED
    
    def test_combat_events_exist(self):
        """Combat event types should be defined."""
        assert EventType.COMBAT_STARTED
        assert EventType.COMBAT_ENDED
        assert EventType.DAMAGE_DEALT
    
    def test_event_type_name(self):
        """EventType name property should work."""
        assert EventType.ROOM_DISCOVERED.name == "ROOM_DISCOVERED"
