"""Tests for the monster intelligence module."""
import numpy as np
import pytest

from app.domain.intelligence import (
    AIAction,
    DecisionContext,
    DecisionEngine,
    DecisionResult,
    PersonalityProfile,
    QLearningAgent,
    QLearningConfig,
    SpeciesKnowledgeRecord,
    SpeciesKnowledgeStore,
    StateEncoder,
    ThreatMemory,
    ThreatEvent,
    ThreatType,
)
from app.domain.entities import Monster, MonsterStats, MonsterBehavior


# ---------- Fixtures ----------


@pytest.fixture
def encoder():
    return StateEncoder()


@pytest.fixture
def q_config():
    return QLearningConfig(
        learning_rate=0.1,
        discount_factor=0.95,
        exploration_rate=0.0,  # no exploration for deterministic tests
        min_exploration_rate=0.0,
        exploration_decay=1.0,
    )


@pytest.fixture
def agent(q_config, encoder):
    return QLearningAgent(q_config, encoder)


@pytest.fixture
def sample_monster():
    return Monster(
        id="test-m-001",
        monster_type="goblin",
        name="Test Goblin",
        x=5,
        y=5,
        room_id="room-1",
        symbol="g",
        color="#0f0",
        stats=MonsterStats(hp=10, max_hp=10, ac=12, str=8, dex=14, con=10, int=8, wis=10, cha=6),
        behavior=MonsterBehavior.PATROL,
    )


@pytest.fixture
def sample_personality():
    return PersonalityProfile(
        aggression=0.7,
        caution=0.4,
        cunning=0.6,
        pack_mentality=0.5,
    )


@pytest.fixture
def sample_memory():
    return ThreatMemory(capacity=5, decay_rate=0.05)


# ---------- StateEncoder Tests ----------


class TestStateEncoder:
    def test_encode_basic(self, encoder):
        idx, multi = encoder.encode(
            hp_ratio=0.8,
            enemy_count=1,
            ally_count=0,
            room_type="chamber",
            distance_to_threat=2,
            threat_direction=8,  # NONE
            in_corridor=False,
        )
        assert isinstance(idx, int)
        assert 0 <= idx < encoder.state_space
        assert len(multi) == 7  # Updated: 5 original + 2 new dimensions

    def test_encode_full_hp(self, encoder):
        idx, multi = encoder.encode(
            hp_ratio=1.0,
            enemy_count=0,
            ally_count=0,
            room_type="library",
            distance_to_threat=8,
        )
        assert multi[0] == len(encoder.hp_bins) - 1

    def test_encode_unknown_room_defaults(self, encoder):
        """Unknown room types should default to 'safe' category (index 1)."""
        idx, multi = encoder.encode(
            hp_ratio=0.5,
            enemy_count=1,
            ally_count=1,
            room_type="unknown_room",
            distance_to_threat=3,
        )
        assert multi[3] == 1  # defaults to 'safe' category


# ---------- QLearningAgent Tests ----------


class TestQLearningAgent:
    def test_init_table_shape(self, agent, encoder):
        table = agent.init_table()
        assert table.shape == (encoder.state_space, len(AIAction))

    def test_select_action_greedy(self, agent, encoder):
        table = agent.init_table()
        state_idx = 0
        table[state_idx, AIAction.FLEE.value] = 100.0
        action = agent.select_action(table, state_idx)
        assert action == AIAction.FLEE

    def test_update_increases_q(self, agent, encoder):
        table = agent.init_table()
        state_idx = 0
        next_idx = 1
        action = AIAction.ATTACK_AGGRESSIVE
        initial_val = table[state_idx, action.value]
        agent.update(table, state_idx, action, reward=10.0, next_state_index=next_idx)
        assert table[state_idx, action.value] > initial_val

    def test_decay_exploration(self, q_config, encoder):
        cfg = QLearningConfig(exploration_rate=0.5, exploration_decay=0.9, min_exploration_rate=0.1)
        ag = QLearningAgent(cfg, encoder)
        original = ag.exploration_rate
        ag.decay_exploration()
        assert ag.exploration_rate < original
        for _ in range(100):
            ag.decay_exploration()
        assert ag.exploration_rate == pytest.approx(cfg.min_exploration_rate, rel=0.01)


# ---------- ThreatMemory Tests ----------


class TestThreatMemory:
    def test_record_and_get_recent(self, sample_memory):
        sample_memory.remember(ThreatEvent(source_id="p1", position=(5, 5), intensity=1.0, tick=100))
        sample_memory.remember(ThreatEvent(source_id="p2", position=(6, 6), intensity=0.8, tick=101))
        assert len(sample_memory.events) == 2
        recent = sample_memory.most_recent_threat()
        assert recent.source_id == "p2"

    def test_capacity_respected(self, sample_memory):
        for i in range(10):
            sample_memory.remember(ThreatEvent(source_id=f"p{i}", position=(i, i), intensity=1.0, tick=i))
        assert len(sample_memory.events) == sample_memory.capacity

    def test_decay_purges_old(self, sample_memory):
        sample_memory.remember(ThreatEvent(source_id="p1", position=(5, 5), intensity=0.1, tick=0))
        sample_memory.decay(current_tick=500)
        assert len(sample_memory.events) == 0


# ---------- PersonalityProfile Tests ----------


class TestPersonalityProfile:
    def test_action_bias_attack(self, sample_personality):
        bias = sample_personality.action_bias(AIAction.ATTACK_AGGRESSIVE)
        assert bias > 1.0

    def test_action_bias_flee(self, sample_personality):
        bias = sample_personality.action_bias(AIAction.FLEE)
        # low caution reduces flee weight
        assert bias < 1.0


# ---------- DecisionEngine Tests ----------


class TestDecisionEngine:
    def test_decide_returns_result(self, sample_monster, sample_personality, sample_memory, encoder, q_config):
        engine = DecisionEngine(config=q_config, encoder=encoder)
        q_table = engine.agent.init_table()
        context = DecisionContext(
            monster=sample_monster,
            memory=sample_memory,
            personality=sample_personality,
            q_table=q_table,
            current_tick=100,
            world_state={"nearby_enemies": 1, "nearby_allies": 0, "room_type": "chamber", "distance_to_threat": 2},
        )
        result = engine.decide(context)
        assert isinstance(result, DecisionResult)
        assert isinstance(result.action, AIAction)
        assert 0 <= result.state_index < encoder.state_space

    def test_learn_updates_table(self, encoder, q_config):
        engine = DecisionEngine(config=q_config, encoder=encoder)
        q_table = engine.agent.init_table()
        engine.learn(q_table, state_index=0, next_state_index=1, action=AIAction.DEFEND, reward=50.0)
        assert q_table[0, AIAction.DEFEND.value] > 0


# ---------- SpeciesKnowledgeStore Tests ----------


class TestSpeciesKnowledgeStore:
    def test_get_or_create(self, tmp_path, encoder):
        store = SpeciesKnowledgeStore(tmp_path / "knowledge.json")
        rec = store.get_or_create("goblin", state_space=encoder.state_space, action_count=len(AIAction))
        assert rec.monster_type == "goblin"
        assert rec.q_table.shape == (encoder.state_space, len(AIAction))

    def test_bump_generation(self, tmp_path, encoder):
        store = SpeciesKnowledgeStore(tmp_path / "knowledge.json")
        store.get_or_create("skeleton", state_space=encoder.state_space, action_count=len(AIAction))
        store.bump_generation("skeleton", max_generation=5)
        assert store.records["skeleton"].generation == 1

    def test_reset_species(self, tmp_path, encoder):
        store = SpeciesKnowledgeStore(tmp_path / "knowledge.json")
        rec = store.get_or_create("orc", state_space=encoder.state_space, action_count=len(AIAction))
        rec.q_table[0, 0] = 100.0
        store.reset_species("orc", state_space=encoder.state_space, action_count=len(AIAction))
        assert store.records["orc"].q_table[0, 0] == 0.0
