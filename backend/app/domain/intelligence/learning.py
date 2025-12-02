"""
Q-Learning Intelligence System for DungeonAI Monsters
=====================================================

This module implements a tabular Q-learning algorithm that enables monsters
to learn and adapt their combat behavior over time. Knowledge is shared at
the species level, meaning all goblins learn from each goblin's experiences.

ALGORITHM OVERVIEW
------------------
Q-learning is a model-free reinforcement learning algorithm that learns
the value of actions in states without requiring a model of the environment.

The Q-value update formula (Bellman equation):

    Q(s, a) ← Q(s, a) + α * [r + γ * max(Q(s', a')) - Q(s, a)]

Where:
    - Q(s, a)  = Current estimated value of taking action 'a' in state 's'
    - α (alpha) = Learning rate (0.1 default) - how fast we update estimates
    - r         = Reward received after taking action
    - γ (gamma) = Discount factor (0.95 default) - importance of future rewards
    - s'        = Next state after action
    - max(Q(s', a')) = Best expected future value from next state

STATE SPACE (432 total states)
------------------------------
The world is discretized into 5 dimensions:

1. HP Ratio (3 bins): How healthy is the monster?
   - 0: LOW (0-33%) - Critical health, may flee
   - 1: MEDIUM (34-66%) - Wounded but fighting
   - 2: HIGH (67-100%) - Healthy, aggressive

2. Enemy Count (4 bins): How many threats nearby?
   - 0: None  - Safe to patrol/ambush
   - 1: One   - Standard combat
   - 2: Two   - Outnumbered, consider fleeing
   - 3: Three+ - Heavily outnumbered

3. Ally Count (4 bins): How many allies nearby?
   - 0: Alone - No pack tactics
   - 1-3: Pack size for coordination

4. Room Type (3 categories): What environment?
   - 0: COMBAT (armory, guard_post, throne_room) - Fight-oriented
   - 1: SAFE (bedroom, library, storage, dining_hall) - Defensive/patrol
   - 2: DANGEROUS (crypt, dungeon_cell, treasury, alchemy_lab) - Cautious

5. Distance to Threat (3 bins): How close is danger?
   - 0: CLOSE (0-1 tiles) - In melee range
   - 1: MEDIUM (2-4 tiles) - Can close or flee
   - 2: FAR (5+ tiles) - Safe distance

Total: 3 × 4 × 4 × 3 × 3 = 432 states

ACTION SPACE (7 actions)
------------------------
- ATTACK_AGGRESSIVE (0): All-out attack, bonus damage, reduced defense
- ATTACK_DEFENSIVE (1): Balanced attack with some defense
- DEFEND (2): Focus on defense, reduced damage
- FLEE (3): Attempt to escape combat
- CALL_ALLIES (4): Alert nearby monsters for help
- AMBUSH (5): Wait for optimal attack opportunity
- PATROL (6): Move around territory, no combat

REWARD STRUCTURE
----------------
- Deal damage to player: +damage_amount (×2 for critical)
- Take damage from player: -damage_amount (×2 for critical)
- Miss an attack: -1.0
- Monster dies: -100.0
- Monster kills player: +50.0 (not yet implemented)

USAGE
-----
Monsters don't call this directly. Instead:
1. MonsterService creates monsters with Q-tables from SpeciesKnowledgeStore
2. DecisionEngine uses StateEncoder to convert world state to index
3. QLearningAgent selects actions (epsilon-greedy with personality bias)
4. Combat events trigger learn() to update Q-values

SCHEMA VERSION
--------------
Increment SCHEMA_VERSION when changing state space dimensions.
This triggers a Q-table reset on load to prevent dimension mismatches.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .personality import PersonalityProfile

# Increment this when changing state space dimensions to trigger Q-table reset
SCHEMA_VERSION = 3


class AIAction(Enum):
    """
    Discrete actions available to monsters during AI decision-making.
    
    Each action has different tactical implications:
    - Aggressive actions (0, 1, 5) prioritize damage output
    - Defensive actions (2) prioritize survival
    - Escape actions (3) attempt to disengage
    - Social actions (4) coordinate with allies
    - Neutral actions (6) for non-combat situations
    - Movement actions (7, 8, 9) for navigation behavior
    """
    ATTACK_AGGRESSIVE = 0  # All-out attack, high risk/reward
    ATTACK_DEFENSIVE = 1   # Balanced attack with some caution
    DEFEND = 2             # Minimize damage taken, reduced offense
    FLEE = 3               # Attempt to escape from combat
    CALL_ALLIES = 4        # Alert nearby monsters for assistance
    AMBUSH = 5             # Wait for optimal attack opportunity
    PATROL = 6             # Move around territory, standard behavior
    MOVE_TOWARD_THREAT = 7 # Chase/approach the nearest threat
    MOVE_AWAY_FROM_THREAT = 8  # Retreat from threat (tactical repositioning)
    PATROL_WAYPOINT = 9    # Move toward patrol waypoint (corridor exploration)

    @classmethod
    def list(cls) -> List["AIAction"]:
        """Return all actions as a list for iteration."""
        return list(cls)
    
    @classmethod
    def combat_actions(cls) -> List["AIAction"]:
        """Return actions that are valid during active combat."""
        return [cls.ATTACK_AGGRESSIVE, cls.ATTACK_DEFENSIVE, cls.DEFEND, cls.FLEE]
    
    @classmethod
    def aggressive_actions(cls) -> List["AIAction"]:
        """Return actions that initiate or continue attacks."""
        return [cls.ATTACK_AGGRESSIVE, cls.ATTACK_DEFENSIVE, cls.AMBUSH]
    
    @classmethod
    def movement_actions(cls) -> List["AIAction"]:
        """Return actions that involve movement."""
        return [cls.PATROL, cls.MOVE_TOWARD_THREAT, cls.MOVE_AWAY_FROM_THREAT, cls.PATROL_WAYPOINT, cls.FLEE]


@dataclass(slots=True)
class QLearningConfig:
    """
    Configuration parameters for the Q-learning algorithm.
    
    These hyperparameters control how quickly and effectively
    monsters learn from their experiences.
    
    Attributes:
        learning_rate (α): How much new information overrides old.
            - Higher (0.5+): Fast learning, but unstable
            - Lower (0.05-): Slow learning, but stable
            - Default 0.1: Good balance for episodic learning
        
        discount_factor (γ): Importance of future rewards.
            - Higher (0.99): Long-term planning, slower convergence
            - Lower (0.5): Short-term focus, faster but myopic
            - Default 0.95: Values future rewards highly
        
        exploration_rate (ε): Probability of random action.
            - Higher: More exploration, discovers new strategies
            - Lower: More exploitation, uses learned strategies
            - Default 0.3: Explores 30% of the time initially
        
        min_exploration_rate: Floor for exploration after decay.
            - Default 0.05: Always 5% random to avoid local optima
        
        exploration_decay: Multiplier applied after each learning step.
            - Default 0.995: Slowly reduces exploration over time
    """
    learning_rate: float = 0.1       # α - step size for Q-value updates
    discount_factor: float = 0.95    # γ - future reward importance
    exploration_rate: float = 0.3    # ε - random action probability
    min_exploration_rate: float = 0.05  # minimum ε after decay
    exploration_decay: float = 0.995    # ε multiplier per learning step

    def clamp(self) -> None:
        """Ensure all parameters are within valid ranges."""
        self.learning_rate = max(1e-4, min(1.0, self.learning_rate))
        self.discount_factor = max(0.0, min(0.999, self.discount_factor))
        self.exploration_rate = max(0.0, min(1.0, self.exploration_rate))
        self.min_exploration_rate = max(0.0, min(self.exploration_rate, self.min_exploration_rate))
        self.exploration_decay = max(0.9, min(0.9999, self.exploration_decay))


# Room type categories for simplified state space
# Maps individual room types to broader tactical categories
ROOM_CATEGORIES = {
    # COMBAT (0): Rooms designed for fighting, monsters are more aggressive
    "armory": 0,
    "guard_post": 0,
    "throne_room": 0,
    
    # SAFE (1): Neutral rooms, balanced behavior
    "chamber": 1,
    "bedroom": 1,
    "library": 1,
    "storage": 1,
    "dining_hall": 1,
    
    # DANGEROUS (2): Hazardous rooms, monsters are more cautious
    "crypt": 2,
    "dungeon_cell": 2,
    "treasury": 2,
    "alchemy_lab": 2,
}

ROOM_CATEGORY_NAMES = ["combat", "safe", "dangerous"]

# Threat direction names for state descriptions
DIRECTION_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "NONE"]


@dataclass
class StateEncoder:
    """
    Encodes continuous world observations into discrete state indices.
    
    This is the bridge between the complex game world and the Q-table.
    Each dimension is "binned" to reduce the state space to a manageable size
    while preserving tactically relevant information.
    
    State Space Dimensions (total: 7,776 states):
    ---------------------------------------------
    1. HP Ratio: 3 bins (low/medium/high)
    2. Enemy Count: 4 bins (0/1/2/3+)
    3. Ally Count: 4 bins (0/1/2/3+)
    4. Room Category: 3 categories (combat/safe/dangerous)
    5. Distance to Threat: 3 bins (close/medium/far)
    6. Threat Direction: 9 bins (8 compass directions + NONE)
    7. In Corridor: 2 bins (True/False)
    
    The flat index is computed as:
        index = hp * (4*4*3*3*9*2) + enemy * (4*3*3*9*2) + ally * (3*3*9*2) 
                + room * (3*9*2) + distance * (9*2) + direction * 2 + corridor
    """
    
    # HP ratio thresholds: [0-0.33]=LOW, [0.34-0.66]=MEDIUM, [0.67-1.0]=HIGH
    hp_bins: Sequence[float] = (0.33, 0.66, 1.0)
    
    # Enemy count thresholds: 0, 1, 2, 3+
    enemy_bins: Sequence[int] = (0, 1, 2, 3)
    
    # Ally count thresholds: 0, 1, 2, 3+
    ally_bins: Sequence[int] = (0, 1, 2, 3)
    
    # Room categories (derived from room_type via ROOM_CATEGORIES)
    room_category_count: int = 3
    
    # Distance thresholds: [0-1]=CLOSE, [2-4]=MEDIUM, [5+]=FAR
    distance_bins: Sequence[int] = (1, 4, 999)
    
    # Threat direction: 9 values (8 compass + NONE)
    direction_count: int = 9
    
    # In corridor: 2 values (True/False)
    corridor_count: int = 2
    
    # Computed fields
    state_shape: tuple = None
    state_space: int = 0

    def __post_init__(self) -> None:
        """Calculate state space dimensions after initialization."""
        self.state_shape = (
            len(self.hp_bins),           # 3 HP levels
            len(self.enemy_bins),         # 4 enemy counts
            len(self.ally_bins),          # 4 ally counts
            self.room_category_count,     # 3 room categories
            len(self.distance_bins),      # 3 distance levels
            self.direction_count,         # 9 threat directions
            self.corridor_count,          # 2 corridor states
        )
        self.state_space = math.prod(self.state_shape)  # 3*4*4*3*3*9*2 = 7776

    def encode(
        self,
        *,
        hp_ratio: float,
        enemy_count: int,
        ally_count: int,
        room_type: str,
        distance_to_threat: int,
        threat_direction: int = 8,  # Default: NONE (8)
        in_corridor: bool = False,
    ) -> Tuple[int, Tuple[int, int, int, int, int, int, int]]:
        """
        Convert world state to a flat index and multi-dimensional index.
        
        Args:
            hp_ratio: Monster's current HP / max HP (0.0 to 1.0)
            enemy_count: Number of hostile entities nearby
            ally_count: Number of friendly monsters nearby
            room_type: Type of room monster is in (e.g., "armory")
            distance_to_threat: Chebyshev distance to nearest threat
            threat_direction: Direction to threat (0-7 compass, 8=NONE)
            in_corridor: Whether monster is in a corridor (not in a room)
        
        Returns:
            Tuple of (flat_index, (hp_idx, enemy_idx, ally_idx, room_idx, dist_idx, dir_idx, corr_idx))
            - flat_index: Single integer for Q-table lookup (0 to 7775)
            - multi_index: Tuple of individual dimension indices for debugging
        """
        # Bin HP ratio: LOW (0), MEDIUM (1), HIGH (2)
        hp_idx = self._bucket(hp_ratio, self.hp_bins)
        
        # Bin enemy count: 0, 1, 2, 3+
        enemy_idx = self._bucket(enemy_count, self.enemy_bins)
        
        # Bin ally count: 0, 1, 2, 3+
        ally_idx = self._bucket(ally_count, self.ally_bins)
        
        # Map room type to category (combat=0, safe=1, dangerous=2)
        room_idx = ROOM_CATEGORIES.get(room_type, 1)  # Default to "safe"
        
        # Bin distance: CLOSE (0), MEDIUM (1), FAR (2)
        distance_idx = self._bucket(distance_to_threat, self.distance_bins)
        
        # Threat direction: 0-8 (clamp to valid range)
        direction_idx = max(0, min(8, threat_direction))
        
        # In corridor: 0 or 1
        corridor_idx = 1 if in_corridor else 0

        multi_index = (hp_idx, enemy_idx, ally_idx, room_idx, distance_idx, direction_idx, corridor_idx)
        flat_index = self._flatten_index(multi_index)
        return flat_index, multi_index
    
    def _bucket(self, value: float, bins: Sequence) -> int:
        """
        Assign a value to a bin index based on thresholds.
        
        Example: _bucket(0.5, (0.33, 0.66, 1.0)) -> 1 (MEDIUM)
        """
        for idx, threshold in enumerate(bins):
            if value <= threshold:
                return idx
        return len(bins) - 1

    def _flatten_index(self, indices: Tuple[int, ...]) -> int:
        """
        Convert multi-dimensional index to flat index for Q-table lookup.
        
        Uses row-major (C-style) ordering where rightmost index varies fastest.
        """
        flat = 0
        stride = 1
        for size, index in zip(reversed(self.state_shape), reversed(indices)):
            flat += index * stride
            stride *= size
        return flat
    
    def decode(self, flat_index: int) -> Tuple[int, int, int, int, int, int, int]:
        """
        Convert flat index back to multi-dimensional index (for debugging).
        """
        indices = []
        remaining = flat_index
        for size in reversed(self.state_shape):
            indices.append(remaining % size)
            remaining //= size
        return tuple(reversed(indices))
    
    def describe_state(self, flat_index: int) -> dict:
        """
        Get human-readable description of a state index (for debugging).
        """
        hp_idx, enemy_idx, ally_idx, room_idx, dist_idx, dir_idx, corr_idx = self.decode(flat_index)
        hp_labels = ["LOW", "MEDIUM", "HIGH"]
        dist_labels = ["CLOSE", "MEDIUM", "FAR"]
        return {
            "hp": hp_labels[hp_idx],
            "enemies": enemy_idx if enemy_idx < 3 else "3+",
            "allies": ally_idx if ally_idx < 3 else "3+",
            "room_category": ROOM_CATEGORY_NAMES[room_idx],
            "distance": dist_labels[dist_idx],
            "threat_direction": DIRECTION_NAMES[dir_idx],
            "in_corridor": bool(corr_idx),
        }


class QLearningAgent:
    """
    Applies tabular Q-learning to update monster combat policies.
    
    This is the core learning engine that:
    1. Selects actions using epsilon-greedy strategy with personality biases
    2. Updates Q-values using the Bellman equation after receiving rewards
    3. Decays exploration rate over time to shift from exploring to exploiting
    
    The agent doesn't own the Q-table - tables are stored per-species in
    SpeciesKnowledgeStore and passed in for each operation. This allows
    all monsters of the same species to share learned knowledge.
    """

    def __init__(self, config: QLearningConfig, encoder: StateEncoder):
        """
        Initialize the Q-learning agent.
        
        Args:
            config: Hyperparameters (learning rate, discount factor, etc.)
            encoder: StateEncoder for discretizing world observations
        """
        self.config = config
        self.encoder = encoder
        self.config.clamp()  # Ensure valid parameter ranges
        self.exploration_rate = self.config.exploration_rate
        self.action_count = len(AIAction)

    def init_table(self) -> np.ndarray:
        """
        Create a new Q-table initialized to zeros.
        
        Returns:
            np.ndarray of shape (state_space, action_count) = (432, 7)
        """
        return np.zeros((self.encoder.state_space, self.action_count), dtype=np.float32)

    def select_action(
        self,
        q_table: np.ndarray,
        state_index: int,
        *,
        personality: Optional["PersonalityProfile"] = None,
    ) -> AIAction:
        """
        Select an action using epsilon-greedy strategy with personality bias.
        
        Algorithm:
        1. With probability ε (exploration_rate), choose random action
        2. Otherwise, choose action with highest weighted Q-value
        
        Personality Influence:
        - If Q-values are near zero (untrained), use personality biases directly
        - If Q-values are learned, multiply Q-values by personality biases
        - This allows personality to guide early behavior while learning overrides it
        
        Args:
            q_table: The species' Q-table to read values from
            state_index: Current state's flat index (0-431)
            personality: Optional personality profile for bias
        
        Returns:
            Selected AIAction
        """
        # Exploration: random action with probability ε
        if random.random() < self.exploration_rate:
            return random.choice(AIAction.list())

        # Exploitation: choose best action based on Q-values + personality
        q_values = q_table[state_index].copy()
        
        if personality:
            # Get personality bias for each action (e.g., aggressive monsters prefer ATTACK)
            biases = np.array(
                [personality.action_bias(action) for action in AIAction],
                dtype=np.float32,
            )
            
            # Check if Q-values have been learned yet
            q_magnitude = np.max(np.abs(q_values))
            
            if q_magnitude < 0.1:
                # Q-table is essentially empty - use personality biases directly
                # This provides reasonable behavior before any learning occurs
                weighted = biases
            else:
                # Q-values have been learned - combine with personality
                # Multiply so personality amplifies/dampens learned preferences
                weighted = q_values * biases
        else:
            weighted = q_values
        
        # Select action with highest weighted value (greedy)
        action_idx = int(np.argmax(weighted))
        return AIAction(action_idx)

    def update(
        self,
        q_table: np.ndarray,
        state_index: int,
        action: AIAction,
        reward: float,
        next_state_index: int,
    ) -> float:
        """
        Update Q-value using the Bellman equation.
        
        Q(s, a) ← Q(s, a) + α * [r + γ * max(Q(s', a')) - Q(s, a)]
        
        Where:
            α = learning_rate (how much to update)
            γ = discount_factor (importance of future rewards)
            r = reward received
            s = current state
            s' = next state
            a = action taken
        
        Args:
            q_table: The species' Q-table to update
            state_index: State where action was taken
            action: Action that was taken
            reward: Reward received (positive or negative)
            next_state_index: State after action was taken
        
        Returns:
            The change in Q-value (delta) for monitoring learning progress
        """
        learning_rate = self.config.learning_rate      # α
        discount_factor = self.config.discount_factor  # γ
        
        # Current Q-value estimate
        old_value = q_table[state_index, action.value]
        
        # Best expected future value from next state
        next_max = float(np.max(q_table[next_state_index]))
        
        # Bellman equation: new estimate = old + α * (target - old)
        # where target = r + γ * max(Q(s', a'))
        target = reward + discount_factor * next_max
        delta = learning_rate * (target - old_value)
        new_value = old_value + delta
        
        # Update the Q-table
        q_table[state_index, action.value] = new_value
        
        return delta  # Return delta for monitoring/debugging

    def decay_exploration(self) -> None:
        """
        Reduce exploration rate by decay factor.
        
        Called after each learning step to gradually shift from
        exploration (trying new things) to exploitation (using knowledge).
        
        exploration_rate = max(min_rate, exploration_rate * decay)
        """
        self.exploration_rate = max(
            self.config.min_exploration_rate,
            self.exploration_rate * self.config.exploration_decay,
        )

    def export_table(self, q_table: np.ndarray) -> List[List[float]]:
        """Convert Q-table to JSON-serializable list of lists."""
        return q_table.tolist()

    def import_table(self, data: Sequence[Sequence[float]]) -> np.ndarray:
        """
        Import Q-table from serialized data, handling dimension mismatches.
        
        If the loaded table has different dimensions (e.g., old schema),
        creates a new table and copies what fits.
        """
        arr = np.array(data, dtype=np.float32)
        if arr.shape != (self.encoder.state_space, self.action_count):
            # Dimension mismatch - likely schema version change
            # Create new table and don't copy (reset learning)
            return self.init_table()
        return arr
