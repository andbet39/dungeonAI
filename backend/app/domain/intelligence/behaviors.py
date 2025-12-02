"""Behavior tree primitives for monster AI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Iterable, List, Optional

from ..entities import Monster
from .memory import ThreatMemory


class BehaviorStatus(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


@dataclass
class BehaviorContext:
    """Context passed to behavior nodes each tick."""

    monster: Monster
    memory: ThreatMemory
    world_state: dict
    current_tick: int


class BehaviorNode:
    """Base class for behavior tree nodes."""

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        raise NotImplementedError


class CompositeNode(BehaviorNode):
    def __init__(self, children: Optional[Iterable[BehaviorNode]] = None) -> None:
        self.children: List[BehaviorNode] = list(children or [])

    def add_child(self, node: BehaviorNode) -> None:
        self.children.append(node)


class SelectorNode(CompositeNode):
    """Runs children until one succeeds."""

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        for child in self.children:
            status = child.tick(context)
            if status != BehaviorStatus.FAILURE:
                return status
        return BehaviorStatus.FAILURE


class SequenceNode(CompositeNode):
    """Runs children sequentially until one fails."""

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        for child in self.children:
            status = child.tick(context)
            if status != BehaviorStatus.SUCCESS:
                return status
        return BehaviorStatus.SUCCESS


class ConditionNode(BehaviorNode):
    """Evaluates a predicate to gate behavior branches."""

    def __init__(self, predicate: Callable[[BehaviorContext], bool]) -> None:
        self.predicate = predicate

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        return BehaviorStatus.SUCCESS if self.predicate(context) else BehaviorStatus.FAILURE


class ActionNode(BehaviorNode):
    """Executes an action callback."""

    def __init__(self, action: Callable[[BehaviorContext], BehaviorStatus]) -> None:
        self.action = action

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        return self.action(context)
