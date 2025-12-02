"""Decision orchestration layer tying personalities, memory, and learning together."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from ..entities import Monster
from .debug import AIDebugger
from .learning import AIAction, QLearningAgent, QLearningConfig, StateEncoder
from .memory import ThreatMemory
from .personality import PersonalityProfile

# Intelligence threshold below which monsters are "oblivious" to player threats
OBLIVIOUS_INTELLIGENCE_THRESHOLD = 6


@dataclass(slots=True)
class DecisionContext:
    monster: Monster
    memory: ThreatMemory
    personality: PersonalityProfile
    q_table: np.ndarray
    current_tick: int
    world_state: Dict[str, object]
    cached_state_index: Optional[int] = None


@dataclass(slots=True)
class DecisionResult:
    action: AIAction
    state_index: int
    discrete_state: Tuple[int, int, int, int, int, int, int]  # Updated for 7 dimensions
    confidence: float = 1.0


class DecisionEngine:
    """High-level AI brain used by each monster instance."""

    def __init__(
        self,
        config: QLearningConfig | None = None,
        encoder: StateEncoder | None = None,
    ) -> None:
        self.encoder = encoder or StateEncoder()
        self.agent = QLearningAgent(config or QLearningConfig(), self.encoder)

    def decide(self, context: DecisionContext) -> DecisionResult:
        state_index, multi_index = self._encode_state(context)
        action = self.agent.select_action(
            context.q_table,
            state_index,
            personality=context.personality,
        )
        q_values = context.q_table[state_index]
        q_max = float(np.max(q_values))
        # Use float() to convert numpy float to Python float for JSON serialization
        confidence = float(1.0 / (1.0 + np.exp(-q_max))) if q_max != 0 else 0.5
        AIDebugger.log_decision(context.monster.id, state_index, action, multi_index)
        return DecisionResult(
            action=action,
            state_index=state_index,
            discrete_state=multi_index,
            confidence=confidence,
        )

    def learn(
        self,
        q_table: np.ndarray,
        *,
        state_index: int,
        next_state_index: int,
        action: AIAction,
        reward: float,
    ) -> None:
        self.agent.update(q_table, state_index, action, reward, next_state_index)
        self.agent.decay_exploration()
        AIDebugger.log_reward(state_index, action, reward, next_state_index)

    def _encode_state(self, context: DecisionContext) -> Tuple[int, Tuple[int, int, int, int, int, int, int]]:
        """
        Encode the current world state into a discrete state index.
        
        Handles intelligence-based awareness gating: low-intelligence monsters
        (intelligence <= OBLIVIOUS_INTELLIGENCE_THRESHOLD) are "oblivious" to players
        and will see nearby_enemies=0, threat_direction=NONE.
        """
        monster = context.monster
        hp_ratio = monster.stats.hp / max(1, monster.stats.max_hp)
        
        # Get raw values from world state
        raw_enemy_count = int(context.world_state.get("nearby_enemies", 0))
        ally_count = int(context.world_state.get("nearby_allies", 0))
        room_type = context.world_state.get("room_type", "chamber")
        raw_distance = int(context.world_state.get("distance_to_threat", 8))
        raw_threat_direction = int(context.world_state.get("threat_direction", 8))  # 8 = NONE
        in_corridor = bool(context.world_state.get("in_corridor", False))
        
        # Intelligence gating: low-intelligence monsters are oblivious to players
        monster_intelligence = getattr(monster.stats, "intelligence", 10)  # Default 10 if not set
        if monster_intelligence <= OBLIVIOUS_INTELLIGENCE_THRESHOLD:
            # Monster is too dumb to notice the player
            enemy_count = 0
            distance_to_threat = 999  # Far away (will bin to FAR)
            threat_direction = 8  # NONE - no threat visible
        else:
            enemy_count = raw_enemy_count
            distance_to_threat = raw_distance
            threat_direction = raw_threat_direction
        
        return self.encoder.encode(
            hp_ratio=max(0.0, min(1.0, hp_ratio)),
            enemy_count=max(0, enemy_count),
            ally_count=max(0, ally_count),
            room_type=room_type,
            distance_to_threat=max(0, distance_to_threat),
            threat_direction=threat_direction,
            in_corridor=in_corridor,
        )
