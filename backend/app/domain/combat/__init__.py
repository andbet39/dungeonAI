"""
Combat system module for DungeonAI.
Contains combat mechanics, fight tracking, and damage calculations.
"""

from .fight import Fight, FightStatus
from .dice import DiceRoll, roll_dice, roll_d20, roll_attack, roll_damage

__all__ = [
    "Fight",
    "FightStatus",
    "DiceRoll",
    "roll_dice",
    "roll_d20",
    "roll_attack",
    "roll_damage",
]
