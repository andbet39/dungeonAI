"""Threat-memory primitives used by the intelligence system."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class ThreatType(str, Enum):
    PLAYER = "player"
    TRAP = "trap"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ThreatEvent:
    """Single remembered threat entry."""

    source_id: str
    position: Tuple[int, int]
    intensity: float
    tick: int
    threat_type: ThreatType = ThreatType.UNKNOWN

    def decay(self, current_tick: int, rate: float) -> None:
        delta = max(0, current_tick - self.tick)
        self.intensity *= max(0.0, 1.0 - rate * delta)
        self.tick = current_tick


@dataclass
class ThreatMemory:
    """Finite-capacity memory that stores recent dangers."""

    capacity: int = 5
    decay_rate: float = 0.05
    events: List[ThreatEvent] = field(default_factory=list)
    last_updated_tick: int = 0

    def remember(self, event: ThreatEvent) -> None:
        if len(self.events) >= self.capacity:
            self.events.pop(0)
        self.events.append(event)

    def decay(self, current_tick: int) -> None:
        if current_tick == self.last_updated_tick:
            return
        for event in list(self.events):
            event.decay(current_tick, self.decay_rate)
            if event.intensity <= 0.05:
                self.events.remove(event)
        self.last_updated_tick = current_tick

    def most_recent_threat(self) -> Optional[ThreatEvent]:
        if not self.events:
            return None
        return max(self.events, key=lambda e: e.tick)

    def strongest_threat(self) -> Optional[ThreatEvent]:
        if not self.events:
            return None
        return max(self.events, key=lambda e: e.intensity)

    def share_with(self, other: "ThreatMemory", blend: float = 0.5) -> None:
        """Merge this memory into another to enable pack behavior."""
        if not self.events:
            return
        blend = max(0.0, min(1.0, blend))
        for event in self.events:
            scaled_event = ThreatEvent(
                source_id=event.source_id,
                position=event.position,
                intensity=event.intensity * blend,
                tick=event.tick,
                threat_type=event.threat_type,
            )
            other.remember(scaled_event)

    def serialize(self) -> List[dict]:
        return [
            {
                "source_id": e.source_id,
                "position": list(e.position),
                "intensity": e.intensity,
                "tick": e.tick,
                "threat_type": e.threat_type.value,
            }
            for e in self.events
        ]

    @classmethod
    def deserialize(cls, payload: List[dict], *, capacity: int, decay_rate: float) -> "ThreatMemory":
        memory = cls(capacity=capacity, decay_rate=decay_rate)
        for item in payload or []:
            memory.remember(
                ThreatEvent(
                    source_id=item.get("source_id", "unknown"),
                    position=tuple(item.get("position", (0, 0))),
                    intensity=float(item.get("intensity", 0)),
                    tick=int(item.get("tick", 0)),
                    threat_type=ThreatType(item.get("threat_type", ThreatType.UNKNOWN.value)),
                )
            )
        return memory
