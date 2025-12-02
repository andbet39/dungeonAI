"""
Shared pytest fixtures for DungeonAI backend tests.
These fixtures provide common test data and mock objects used across multiple test modules.
"""
import asyncio
import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Domain entities
from app.domain.entities import (
    Player, Monster, MonsterStats, MonsterBehavior, 
    MonsterIntelligenceState, Room
)
from app.domain.combat import Fight, FightStatus

# Intelligence module
from app.domain.intelligence import (
    AIAction, DecisionContext, DecisionEngine, DecisionResult,
    PersonalityProfile, QLearningAgent, QLearningConfig,
    StateEncoder, ThreatMemory, ThreatEvent, ThreatType
)


# ============================================================================
# EVENT LOOP FIXTURE
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# PLAYER FIXTURES
# ============================================================================

@pytest.fixture
def basic_player():
    """Create a basic player at origin with default stats."""
    return Player(
        id="player-001",
        x=5,
        y=5,
        color="#ff0",
        current_room_id="room-1",
        hp=30,
        max_hp=30,
        ac=12,
        str=12,
        dex=12,
        con=12
    )


@pytest.fixture
def wounded_player():
    """Create a player with low HP for testing damage/healing."""
    return Player(
        id="player-002",
        x=10,
        y=10,
        color="#0ff",
        hp=5,
        max_hp=30,
        ac=12
    )


@pytest.fixture
def defending_player():
    """Create a player in defensive stance."""
    player = Player(
        id="player-003",
        x=8,
        y=8,
        color="#f0f",
        hp=25,
        max_hp=30,
        ac=14
    )
    player.is_defending = True
    return player


# ============================================================================
# MONSTER FIXTURES
# ============================================================================

@pytest.fixture
def basic_monster():
    """Create a basic goblin monster for testing."""
    return Monster(
        id="monster-001",
        monster_type="goblin",
        name="Test Goblin",
        x=5,
        y=5,
        room_id="room-1",
        symbol="g",
        color="#0f0",
        stats=MonsterStats(
            hp=10, max_hp=10, ac=12,
            str=8, dex=14, con=10, int=8, wis=10, cha=6,
            challenge_rating=0.25
        ),
        behavior=MonsterBehavior.PATROL,
        description="A sneaky goblin"
    )


@pytest.fixture
def strong_monster():
    """Create a stronger orc monster."""
    return Monster(
        id="monster-002",
        monster_type="orc",
        name="Fierce Orc",
        x=15,
        y=15,
        room_id="room-2",
        symbol="o",
        color="#f00",
        stats=MonsterStats(
            hp=15, max_hp=15, ac=13,
            str=16, dex=10, con=14, int=7, wis=8, cha=8,
            challenge_rating=0.5
        ),
        behavior=MonsterBehavior.AGGRESSIVE,
        description="A brutish orc warrior"
    )


@pytest.fixture
def wounded_monster():
    """Create a monster with low HP for testing flee behavior."""
    return Monster(
        id="monster-003",
        monster_type="goblin",
        name="Wounded Goblin",
        x=7,
        y=7,
        room_id="room-1",
        symbol="g",
        color="#0f0",
        stats=MonsterStats(
            hp=2, max_hp=10, ac=12,
            str=8, dex=14, con=10, int=8, wis=10, cha=6,
            challenge_rating=0.25
        ),
        behavior=MonsterBehavior.PATROL
    )


# ============================================================================
# ROOM FIXTURES
# ============================================================================

@pytest.fixture
def basic_room():
    """Create a basic chamber room."""
    return Room(
        id="room-1",
        x=2,
        y=2,
        width=10,
        height=8,
        room_type="chamber",
        name="Test Chamber",
        description="A dusty test chamber",
        visited=False
    )


@pytest.fixture
def library_room():
    """Create a library room with furniture."""
    return Room(
        id="room-2",
        x=15,
        y=2,
        width=12,
        height=10,
        room_type="library",
        name="Ancient Library",
        description="Shelves of dusty tomes line the walls",
        furniture=[(17, 4, 6), (19, 4, 6)],  # bookshelves
        visited=True
    )


@pytest.fixture
def small_room():
    """Create a small room that won't spawn monsters (under min area)."""
    return Room(
        id="room-3",
        x=30,
        y=2,
        width=4,
        height=4,
        room_type="dungeon_cell",
        name="Tiny Cell",
        description="A cramped prison cell"
    )


# ============================================================================
# INTELLIGENCE FIXTURES
# ============================================================================

@pytest.fixture
def encoder():
    """Create a fresh StateEncoder."""
    return StateEncoder()


@pytest.fixture
def q_config():
    """Q-learning config with zero exploration for deterministic tests."""
    return QLearningConfig(
        learning_rate=0.1,
        discount_factor=0.95,
        exploration_rate=0.0,  # No exploration for deterministic tests
        min_exploration_rate=0.0,
        exploration_decay=1.0
    )


@pytest.fixture
def exploring_q_config():
    """Q-learning config with exploration enabled."""
    return QLearningConfig(
        learning_rate=0.1,
        discount_factor=0.95,
        exploration_rate=1.0,  # Always explore
        min_exploration_rate=0.01,
        exploration_decay=0.99
    )


@pytest.fixture
def agent(q_config, encoder):
    """Create a Q-learning agent with deterministic behavior."""
    return QLearningAgent(q_config, encoder)


@pytest.fixture
def aggressive_personality():
    """Create an aggressive personality profile."""
    return PersonalityProfile(
        aggression=0.9,
        caution=0.2,
        cunning=0.5,
        pack_mentality=0.7
    )


@pytest.fixture
def cautious_personality():
    """Create a cautious personality profile."""
    return PersonalityProfile(
        aggression=0.2,
        caution=0.9,
        cunning=0.6,
        pack_mentality=0.3
    )


@pytest.fixture
def balanced_personality():
    """Create a balanced personality profile."""
    return PersonalityProfile(
        aggression=0.5,
        caution=0.5,
        cunning=0.5,
        pack_mentality=0.5
    )


@pytest.fixture
def threat_memory():
    """Create an empty threat memory."""
    return ThreatMemory(capacity=5, decay_rate=0.05)


@pytest.fixture
def populated_memory():
    """Create a threat memory with some events."""
    memory = ThreatMemory(capacity=5, decay_rate=0.05)
    memory.remember(ThreatEvent(
        source_id="player-001",
        position=(5, 5),
        intensity=1.0,
        tick=100,
        threat_type=ThreatType.PLAYER
    ))
    memory.remember(ThreatEvent(
        source_id="player-002",
        position=(7, 7),
        intensity=0.8,
        tick=105,
        threat_type=ThreatType.PLAYER
    ))
    return memory


# ============================================================================
# COMBAT FIXTURES
# ============================================================================

@pytest.fixture
def active_fight(basic_player, basic_monster):
    """Create an active fight between a player and monster."""
    fight = Fight.create(
        monster_id=basic_monster.id,
        initiator_player_id=basic_player.id,
        turn_duration=120
    )
    return fight


@pytest.fixture
def multiplayer_fight(basic_monster):
    """Create a fight with multiple players."""
    fight = Fight.create(
        monster_id=basic_monster.id,
        initiator_player_id="player-001",
        turn_duration=120
    )
    fight.add_player("player-002")
    fight.add_player("player-003")
    return fight


# ============================================================================
# STORAGE FIXTURES
# ============================================================================

@pytest.fixture
def temp_save_dir(tmp_path):
    """Create a temporary directory for save files."""
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    games_dir = save_dir / "games"
    games_dir.mkdir()
    return save_dir


@pytest.fixture
def sample_game_state(basic_room, basic_player, basic_monster):
    """Create a sample game state dictionary for save/load testing."""
    return {
        "game_id": "test-game-001",
        "name": "Test Dungeon",
        "map": {
            "width": 50,
            "height": 40,
            "tiles": [[0] * 50 for _ in range(40)],
            "spawn_x": 5,
            "spawn_y": 5,
            "seed": 12345
        },
        "rooms": [basic_room.to_dict()],
        "players": {basic_player.id: basic_player.to_dict()},
        "monsters": {basic_monster.id: basic_monster.to_dict()},
        "token_to_player": {"test-token": basic_player.id}
    }


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service."""
    with patch('app.services.ai_service.ai_service') as mock:
        mock.is_enabled = False
        mock.generate_room_description = AsyncMock(return_value="A dark room")
        mock.generate_room_descriptions = AsyncMock(side_effect=lambda rooms: [
            {**r, "description": "Test description"} for r in rooms
        ])
        mock.generate_game_name = AsyncMock(return_value="Test Dungeon")
        mock.generate_player_nickname = AsyncMock(return_value="The Test Hero")
        yield mock
