# DungeonAI - Intelligence System Documentation

## Overview

DungeonAI implements a Q-learning based artificial intelligence system for monsters. Monsters learn optimal behaviors through experience, adapting their combat strategies based on rewards and punishments received during gameplay.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Intelligence System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Monster   │───>│  Decision   │───>│    Q-Learning Engine    │ │
│  │   Entity    │    │   Engine    │    │   (learning.py)         │ │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘ │
│         │                  │                       │                │
│         │                  │                       │                │
│         ▼                  ▼                       ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Memory    │    │  Behavior   │    │    Species Knowledge    │ │
│  │   System    │    │   Profile   │    │   (generations.py)      │ │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Q-Learning Engine (`learning.py`)

The heart of the intelligence system. Implements tabular Q-learning with the Bellman equation.

#### Algorithm Overview

```
Q(s,a) ← Q(s,a) + α × [r + γ × max_a' Q(s',a') - Q(s,a)]
```

Where:
- `Q(s,a)` = Q-value for state `s` and action `a`
- `α` (alpha) = Learning rate (default: 0.1)
- `r` = Reward received
- `γ` (gamma) = Discount factor (default: 0.95)
- `max_a' Q(s',a')` = Maximum Q-value for next state

#### State Space Design

The state space is carefully designed to balance:
- **Granularity**: Enough detail for meaningful decisions
- **Size**: Small enough for reasonable Q-table convergence

**Total States: 432** (3 × 4 × 4 × 3 × 3)

| Dimension | Bins | Values |
|-----------|------|--------|
| HP Ratio | 3 | [0.33, 0.66, 1.0] |
| Nearby Enemies | 4 | [0, 1, 2, 3+] |
| Nearby Allies | 4 | [0, 1, 2, 3+] |
| Room Type | 3 | Combat, Safe, Treasure |
| Distance to Threat | 3 | [2, 5, 10+] |

##### HP Bins
- **Low (0)**: HP ≤ 33% - Critical health, favor defensive actions
- **Medium (1)**: 33% < HP ≤ 66% - Standard engagement
- **High (2)**: HP > 66% - Full aggression possible

##### Room Categories
Rooms are grouped by tactical significance:

| Category | Rooms | Index |
|----------|-------|-------|
| Combat | armory, guard_post, throne_room | 0 |
| Safe | bedroom, library, dining_hall, storage | 1 |
| Treasure | treasury, crypt, alchemy_lab, chamber, dungeon_cell | 2 |

##### Distance Bins
- **Close (0)**: distance ≤ 2 - Melee range
- **Medium (1)**: 2 < distance ≤ 5 - Charge distance
- **Far (2)**: distance > 5 - Out of immediate range

#### Actions

| Action | Description | Typical Use |
|--------|-------------|-------------|
| ATTACK_AGGRESSIVE | Full attack, no defense | High HP, advantage |
| ATTACK_DEFENSIVE | Balanced attack/defense | Medium situation |
| DEFEND | Focus on defense | Low HP, outnumbered |
| FLEE | Attempt escape | Critical HP |
| CALL_ALLIES | Alert nearby allies | Multiple enemies |
| AMBUSH | Wait for opportunity | High cunning |
| PATROL | Standard movement | No threats |

#### Reward Structure

Rewards guide learning by signaling good and bad outcomes:

| Event | Reward | Rationale |
|-------|--------|-----------|
| Damage dealt | +damage × 0.1 | Encourage effective attacks |
| Kill enemy | +5.0 | Strong positive reinforcement |
| Damage taken | -damage × 0.05 | Discourage getting hit |
| Death | -10.0 | Strong negative reinforcement |

### 2. State Encoder

The `StateEncoder` class converts world state into a single integer index for Q-table lookup.

```python
# Example encoding
world_state = {
    'hp_ratio': 0.75,        # → bin 2 (high)
    'nearby_enemies': 1,      # → bin 1
    'nearby_allies': 0,       # → bin 0
    'room_type': 'armory',    # → category 0 (combat)
    'distance_to_threat': 3   # → bin 1 (medium)
}

state_index = encoder.encode(world_state)
# Result: integer 0-431
```

### 3. Decision Engine (`decision_engine.py`)

Orchestrates the decision-making process for monsters.

```python
class DecisionEngine:
    def decide(self, monster: Monster, game_state: dict) -> MonsterAction:
        # 1. Build world state from game state
        world_state = self._build_world_state(monster, game_state)
        
        # 2. Encode state to index
        state_index = self.encoder.encode(world_state)
        
        # 3. Get Q-values for this state
        q_values = species_knowledge.get_q_values(monster.type, state_index)
        
        # 4. Choose action (ε-greedy)
        if random() < exploration_rate:
            action = random_action()  # Explore
        else:
            action = argmax(q_values)  # Exploit
        
        # 5. Apply personality modifiers
        action = self._apply_personality(action, monster.personality)
        
        return action
```

### 4. Species Knowledge (`generations.py`)

Manages Q-tables and learning history for each monster species.

#### Schema Versioning

```python
SCHEMA_VERSION = 2  # Current schema version
```

When loading saved data, if the schema version doesn't match, Q-tables are reset to allow the new state space to learn from scratch.

#### Learning History

Each species maintains a history of recent learning events:

```python
@dataclass
class LearningHistoryEntry:
    tick: int              # Game tick when learning occurred
    state_index: int       # Encoded state (0-431)
    action: str            # Action taken
    reward: float          # Reward received
    q_value_before: float  # Q-value before update
    q_value_after: float   # Q-value after update
    q_max_next: float      # Max Q-value of next state
```

History is limited to `HISTORY_LIMIT` (default: 100) entries per species.

### 5. Behavior Profiles (`behaviors.py`)

Personality-based behavior modifiers that influence action selection.

```python
class MonsterPersonality:
    aggression: float      # 0.0-1.0: Attack tendency
    caution: float         # 0.0-1.0: Defense tendency
    pack_mentality: float  # 0.0-1.0: Ally coordination
    cunning: float         # 0.0-1.0: Ambush preference
```

#### Example Profiles

| Profile | Aggression | Caution | Pack | Cunning |
|---------|------------|---------|------|---------|
| Goblin | 0.3 | 0.2 | 0.7 | 0.6 |
| Orc | 0.8 | 0.2 | 0.5 | 0.2 |
| Skeleton | 0.5 | 0.1 | 0.3 | 0.1 |
| Spider | 0.6 | 0.4 | 0.2 | 0.8 |

### 6. Memory System (`memory.py`)

Short-term memory for recent threat events.

```python
class MonsterMemory:
    last_threat_position: Tuple[int, int]
    last_seen_tick: int
    threat_events: List[ThreatEvent]  # Last N events
```

## Learning Flow

### During Combat

```
1. Monster decides action based on current Q-values
2. Action is executed in game
3. Outcomes are observed (damage dealt/taken, kills)
4. Combat events emit with ai_snapshot
5. monster_service applies rewards
6. Q-table is updated via Bellman equation
7. History is recorded for visualization
```

### Reward Application

```python
def _apply_reward_from_snapshot(snapshot: dict, reward: float):
    if not snapshot:
        return
    
    species = snapshot.get('monster_type')
    state_index = snapshot.get('state_index')
    action = snapshot.get('action')
    
    # Get Q-values before update
    q_before = species_knowledge.get_q_value(species, state_index, action)
    
    # Update Q-table
    species_knowledge.apply_reward(
        species=species,
        state_index=state_index,
        action_index=action_to_index(action),
        reward=reward,
        next_state_index=state_index,  # Simplified
        learning_rate=0.1,
        discount_factor=0.95
    )
    
    # Get Q-values after update
    q_after = species_knowledge.get_q_value(species, state_index, action)
    
    # Record in history
    species_knowledge.record_learning_event(
        species=species,
        tick=current_tick,
        state_index=state_index,
        action=action,
        reward=reward,
        q_before=q_before,
        q_after=q_after
    )
```

## Sandbox System

The sandbox provides an isolated environment for testing AI behavior.

### Features

1. **Manual Monster Spawning**: Click to spawn monsters of any type
2. **Threat Placement**: Position a player-like threat
3. **Step-by-Step Execution**: Observe decisions tick by tick
4. **Combat Simulation**: Optional dice-based combat

### Combat Simulation

When enabled, the sandbox simulates real combat:

```python
class SandboxThreatStats:
    hp: int = 50
    max_hp: int = 50
    ac: int = 12
    attack_bonus: int = 3
    damage_dice: str = "1d8"
```

Monsters adjacent to the threat will:
1. Roll d20 + attack bonus vs threat AC
2. On hit, roll damage dice
3. Threat HP is reduced
4. Q-learning rewards are applied

## API Endpoints

### Species History

```
GET /api/admin/ai/species-history/{species}?limit=100
```

Returns learning history for visualization:

```json
{
    "species": "goblin",
    "total": 87,
    "history": [
        {
            "tick": 1234,
            "state_index": 156,
            "action": "ATTACK_AGGRESSIVE",
            "reward": 2.5,
            "q_value_before": 0.12,
            "q_value_after": 0.35,
            "q_delta": 0.23
        }
    ]
}
```

### Sandbox Combat Toggle

```
POST /api/admin/sandbox/toggle-combat
Content-Type: application/json

{"combat_enabled": true}
```

## Visualization (AITestArena.vue)

### Evolution Tab

Shows learning progress with interactive charts:

1. **Reward History**: Line chart of rewards over time
2. **Q-Value Changes**: Before/after Q-values for each update
3. **Action Distribution**: Bar chart of action frequency
4. **Summary Stats**: Total/average rewards, Q-delta

### Tooltips

Every value has a tooltip explaining its meaning:
- State space components explained
- Q-value interpretation
- Reward structure clarification

## Configuration

### Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| learning_rate | 0.1 | How fast Q-values update |
| discount_factor | 0.95 | Future reward importance |
| exploration_rate | 0.3 | Random action probability |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| SCHEMA_VERSION | 2 | Current state space schema |
| HISTORY_LIMIT | 100 | Max history entries per species |
| STATE_SPACE_SIZE | 432 | Total possible states |
| ACTION_COUNT | 7 | Number of possible actions |

## Debugging

### Check Q-Table Contents

```python
from backend.app.domain.intelligence import species_knowledge

# Get Q-table summary
for species, data in species_knowledge.knowledge.items():
    q_table = data.q_table
    non_zero = np.count_nonzero(q_table)
    print(f"{species}: {non_zero}/{q_table.size} non-zero values")
```

### Verify State Encoding

```python
from backend.app.domain.intelligence.learning import StateEncoder

encoder = StateEncoder()
state = {
    'hp_ratio': 0.5,
    'nearby_enemies': 1,
    'nearby_allies': 0,
    'room_type': 'armory',
    'distance_to_threat': 3
}
index = encoder.encode(state)
decoded = encoder.decode(index)
print(f"Encoded: {index}, Decoded: {decoded}")
```

### Monitor Learning Events

Use the Evolution tab in the AI Test Arena to watch learning in real-time.

## Future Improvements

1. **Deep Q-Network**: Replace table with neural network for continuous state space
2. **Experience Replay**: Store and replay past experiences
3. **Multi-Agent Learning**: Coordinate learning across allied monsters
4. **Transfer Learning**: Apply knowledge from one species to similar ones
5. **Curriculum Learning**: Start with simpler scenarios, gradually increase difficulty

## Glossary

| Term | Definition |
|------|------------|
| Q-table | 2D array mapping (state, action) → expected value |
| State | Encoded representation of world from monster's perspective |
| Action | Possible behavior the monster can take |
| Reward | Numeric feedback signal after action execution |
| Episode | One complete encounter from start to end |
| Exploration | Taking random actions to discover new strategies |
| Exploitation | Using learned knowledge to maximize reward |
| ε-greedy | Policy mixing exploration and exploitation |
| Bellman Equation | Recursive formula for optimal Q-values |
