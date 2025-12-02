"""Personality modelling utilities for intelligent monsters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:  # Avoid cyclic imports at runtime
    from .learning import AIAction


def _clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp personality values to a safe range."""
    return max(minimum, min(maximum, value))


@dataclass(slots=True)
class PersonalityProfile:
    """Represents high-level behavioral tendencies.

    Values are normalized between 0 and 1 and influence both exploration and
    action weighting within the decision engine.
    
    Attributes:
        aggression: Tendency toward attack actions (ATTACK_AGGRESSIVE, AMBUSH, MOVE_TOWARD_THREAT)
        caution: Tendency toward defensive actions (DEFEND, FLEE, MOVE_AWAY_FROM_THREAT)
        cunning: Tendency toward tactical actions (ATTACK_DEFENSIVE, AMBUSH)
        pack_mentality: Tendency toward social actions (CALL_ALLIES)
        exploration: Tendency toward movement/patrol actions (PATROL, PATROL_WAYPOINT)
    """

    aggression: float = 0.5
    caution: float = 0.5
    cunning: float = 0.5
    pack_mentality: float = 0.5
    exploration: float = 0.5  # New: tendency to explore/patrol

    def __post_init__(self) -> None:
        self.aggression = _clamp(self.aggression)
        self.caution = _clamp(self.caution)
        self.cunning = _clamp(self.cunning)
        self.pack_mentality = _clamp(self.pack_mentality)
        self.exploration = _clamp(self.exploration)

    @classmethod
    def from_dict(cls, data: Dict[str, float] | None) -> "PersonalityProfile":
        if not data:
            return cls()
        return cls(
            aggression=data.get("aggression", 0.5),
            caution=data.get("caution", 0.5),
            cunning=data.get("cunning", 0.5),
            pack_mentality=data.get("pack_mentality", 0.5),
            exploration=data.get("exploration", 0.5),
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "aggression": self.aggression,
            "caution": self.caution,
            "cunning": self.cunning,
            "pack_mentality": self.pack_mentality,
            "exploration": self.exploration,
        }

    def action_bias(self, action: "AIAction") -> float:
        """
        Return a multiplier that biases Q-values for a specific action.
        
        The bias is designed to:
        1. Provide reasonable default behavior before learning occurs
        2. Favor combat actions over non-combat when facing threats
        3. Scale social actions (CALL_ALLIES) to not dominate untrained selection
        
        All biases are normalized around 1.0, with modifiers typically ±0.2.
        """
        from .learning import AIAction  # Local import to avoid cycle

        base = 1.0
        
        # Primary combat action - most monsters should default to fighting
        if action == AIAction.ATTACK_AGGRESSIVE:
            # Strong base bias + aggression modifier
            base = 1.15 + (self.aggression - 0.5) * 0.3
        
        # Balanced combat - good default for most situations
        elif action == AIAction.ATTACK_DEFENSIVE:
            # Slightly lower base, boosted by cunning
            base = 1.10 + (self.cunning - 0.5) * 0.25
        
        # Defensive posture
        elif action == AIAction.DEFEND:
            base = 0.9 + (self.caution - 0.5) * 0.4
        
        # Escape/flee
        elif action == AIAction.FLEE:
            base = 0.7 + (self.caution - 0.5) * 0.5
        
        # Call for help - lower base to prevent dominance in untrained state
        # Only becomes preferred when pack_mentality is very high (>0.8)
        elif action == AIAction.CALL_ALLIES:
            # Lower base (0.8) and smaller multiplier (0.4) to balance with combat
            base = 0.8 + (self.pack_mentality - 0.5) * 0.4
        
        # Ambush - tactical waiting
        elif action == AIAction.AMBUSH:
            base = 1.0 + (self.cunning - 0.5) * 0.4 + (self.aggression - 0.5) * 0.15
        
        # Standard patrol
        elif action == AIAction.PATROL:
            base = 0.85 + (self.exploration - 0.5) * 0.3
        
        # Chase threat - aggressive movement
        elif action == AIAction.MOVE_TOWARD_THREAT:
            base = 1.05 + (self.aggression - 0.5) * 0.35
        
        # Retreat from threat - tactical movement
        elif action == AIAction.MOVE_AWAY_FROM_THREAT:
            base = 0.8 + (self.caution - 0.5) * 0.4
        
        # Patrol waypoint - exploration movement
        elif action == AIAction.PATROL_WAYPOINT:
            base = 0.85 + (self.exploration - 0.5) * 0.35
        
        return max(0.1, base)


@dataclass(slots=True)
class PersonalityConfig:
    """Configurable knobs for personality-driven cadence."""

    default_profile: PersonalityProfile = field(default_factory=PersonalityProfile)
    decision_cooldown_ticks: int = 2  # Minimum ticks between expensive decisions

    @classmethod
    def from_dict(cls, data: Dict[str, object] | None) -> "PersonalityConfig":
        if not data:
            return cls()
        profile_data = data.get("profile") if isinstance(data, dict) else None
        return cls(
            default_profile=PersonalityProfile.from_dict(profile_data),
            decision_cooldown_ticks=int(data.get("decision_cooldown_ticks", 2))
            if isinstance(data, dict)
            else 2,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "profile": self.default_profile.to_dict(),
            "decision_cooldown_ticks": self.decision_cooldown_ticks,
        }
