"""
Dice rolling utilities for D&D-style combat.
"""
import random
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DiceRoll:
    """Result of a dice roll."""
    dice_notation: str  # e.g., "1d20", "2d6+3"
    rolls: List[int]    # Individual die results
    modifier: int       # Bonus/penalty
    total: int          # Final result
    
    def to_dict(self) -> dict:
        return {
            "dice": self.dice_notation,
            "rolls": self.rolls,
            "modifier": self.modifier,
            "total": self.total
        }
    
    def __str__(self) -> str:
        if len(self.rolls) == 1:
            roll_str = str(self.rolls[0])
        else:
            roll_str = f"({'+'.join(map(str, self.rolls))})"
        
        if self.modifier > 0:
            return f"{roll_str}+{self.modifier} = {self.total}"
        elif self.modifier < 0:
            return f"{roll_str}{self.modifier} = {self.total}"
        else:
            return f"{roll_str} = {self.total}"


def roll_dice(notation: str) -> DiceRoll:
    """
    Roll dice using standard notation.
    Examples: "1d20", "2d6", "1d8+3", "1d20-2"
    
    Returns a DiceRoll with all details.
    """
    # Parse notation: NdS+M or NdS-M or NdS
    pattern = r'^(\d+)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, notation.lower().replace(' ', ''))
    
    if not match:
        # Invalid notation, return a single d20
        roll = random.randint(1, 20)
        return DiceRoll(
            dice_notation="1d20",
            rolls=[roll],
            modifier=0,
            total=roll
        )
    
    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    
    # Roll the dice
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    
    return DiceRoll(
        dice_notation=notation,
        rolls=rolls,
        modifier=modifier,
        total=max(0, total)  # Minimum 0
    )


def roll_d20(modifier: int = 0) -> DiceRoll:
    """Roll a d20 with optional modifier."""
    roll = random.randint(1, 20)
    notation = f"1d20{'+' + str(modifier) if modifier > 0 else str(modifier) if modifier < 0 else ''}"
    return DiceRoll(
        dice_notation=notation.strip('+'),
        rolls=[roll],
        modifier=modifier,
        total=roll + modifier
    )


def roll_attack(attack_bonus: int, target_ac: int) -> Tuple[DiceRoll, bool, bool]:
    """
    Roll a d20 attack roll against a target AC.
    
    Returns: (roll_result, hit, is_critical)
    - hit: True if attack succeeds
    - is_critical: True if natural 20
    """
    roll = roll_d20(attack_bonus)
    natural_roll = roll.rolls[0]
    
    is_critical = natural_roll == 20
    is_fumble = natural_roll == 1
    
    # Natural 20 always hits, natural 1 always misses
    if is_critical:
        hit = True
    elif is_fumble:
        hit = False
    else:
        hit = roll.total >= target_ac
    
    return roll, hit, is_critical


def roll_damage(damage_dice: str, is_critical: bool = False) -> DiceRoll:
    """
    Roll damage dice. Double dice on critical hit.
    
    Example: "1d6+2" normally, "2d6+2" on crit
    """
    if is_critical:
        # Double the number of dice
        pattern = r'^(\d+)d(\d+)([+-]\d+)?$'
        match = re.match(pattern, damage_dice.lower().replace(' ', ''))
        if match:
            num_dice = int(match.group(1)) * 2
            die_size = match.group(2)
            modifier = match.group(3) if match.group(3) else ''
            damage_dice = f"{num_dice}d{die_size}{modifier}"
    
    return roll_dice(damage_dice)
