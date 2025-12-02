"""Thin debug/logging helpers for the intelligence stack."""
from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, Tuple

from ...config import settings
from .learning import AIAction


@dataclass(slots=True)
class DebugEntry:
    timestamp: datetime
    monster_id: str
    state_index: int
    action: AIAction
    feature_index: Tuple[int, int, int, int, int]
    reward: float | None = None
    next_state_index: int | None = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "monster_id": self.monster_id,
            "state_index": self.state_index,
            "action": self.action.name,
            "feature_index": self.feature_index,
            "reward": self.reward,
            "next_state_index": self.next_state_index,
        }


class AIDebugger:
    """Centralized debugging/logging toggled via env/settings."""

    _enabled = settings.debug or os.getenv("AI_DEBUG", "false").lower() == "true"
    _entries: Deque[DebugEntry] = deque(maxlen=500)

    @classmethod
    def enable(cls) -> None:
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        cls._enabled = False
        cls._entries.clear()

    @classmethod
    def log_decision(
        cls,
        monster_id: str,
        state_index: int,
        action: AIAction,
        feature_index: Tuple[int, int, int, int, int],
    ) -> None:
        if not cls._enabled:
            return
        cls._entries.append(
            DebugEntry(
                timestamp=datetime.utcnow(),
                monster_id=monster_id,
                state_index=state_index,
                action=action,
                feature_index=feature_index,
            )
        )

    @classmethod
    def log_reward(
        cls,
        state_index: int,
        action: AIAction,
        reward: float,
        next_state_index: int,
    ) -> None:
        if not cls._enabled or not cls._entries:
            return
        entry = cls._entries[-1]
        entry.reward = reward
        entry.next_state_index = next_state_index

    @classmethod
    def dump(cls, limit: int = 100) -> list[dict]:
        return [entry.to_dict() for entry in list(cls._entries)[-limit:]]
