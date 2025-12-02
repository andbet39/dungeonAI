"""
Species-level knowledge persistence for learning monsters.

This module maintains Q-tables per monster species, enabling knowledge
transfer across individual monster instances. When a monster dies, its
species' Q-table is updated, allowing new spawns to benefit from
accumulated experience.

Schema versioning ensures Q-tables are reset when the state space changes.
History tracking provides evolution metrics for visualization.

FILE STRUCTURE
--------------
- species_knowledge.json: Main file with Q-tables and metadata
- species_history/{species}.json: Per-species learning history files

This separation keeps the main knowledge file small and fast to load,
while allowing history to grow independently per species.
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ...config import settings
from .learning import SCHEMA_VERSION

# Maximum history entries per species (configurable via settings if needed)
HISTORY_LIMIT = 1000


@dataclass
class LearningHistoryEntry:
    """Single learning event for tracking evolution over time."""
    timestamp: str
    generation: int
    reward: float
    state_index: int
    action: str
    q_value_before: float
    q_value_after: float


@dataclass
class SpeciesKnowledgeRecord:
    """
    Persistent knowledge record for a monster species.
    
    Attributes:
        monster_type: Identifier for this species (e.g., "goblin", "skeleton")
        generation: Increments each time a monster of this species dies
        q_table: NumPy array of shape (state_space, action_count) holding Q-values
        encounters: Total combat encounters for this species
        total_learning_steps: Cumulative Q-table updates across all generations
        history: Recent learning events (loaded lazily from separate file)
        _history_dirty: Flag indicating history needs to be saved
    """
    monster_type: str
    generation: int
    q_table: np.ndarray
    encounters: int = 0
    total_learning_steps: int = 0
    history: List[LearningHistoryEntry] = field(default_factory=list)
    _history_dirty: bool = field(default=False, repr=False)
    _history_loaded: bool = field(default=False, repr=False)

    def to_dict(self) -> dict:
        """Serialize for main knowledge file (excludes history)."""
        return {
            "monster_type": self.monster_type,
            "generation": self.generation,
            "encounters": self.encounters,
            "total_learning_steps": self.total_learning_steps,
            "q_table": self.q_table.tolist(),
            # History is stored separately, not in main file
        }
    
    def history_to_dict(self) -> dict:
        """Serialize history for separate history file."""
        return {
            "monster_type": self.monster_type,
            "schema_version": SCHEMA_VERSION,
            "history": [
                {
                    "timestamp": h.timestamp,
                    "generation": h.generation,
                    "reward": h.reward,
                    "state_index": h.state_index,
                    "action": h.action,
                    "q_value_before": h.q_value_before,
                    "q_value_after": h.q_value_after,
                }
                for h in self.history
            ],
        }
    
    def add_history_entry(
        self,
        reward: float,
        state_index: int,
        action: str,
        q_value_before: float,
        q_value_after: float,
    ) -> None:
        """Add a learning event to history, maintaining HISTORY_LIMIT."""
        entry = LearningHistoryEntry(
            timestamp=datetime.now().isoformat(),
            generation=self.generation,
            reward=reward,
            state_index=state_index,
            action=action,
            q_value_before=q_value_before,
            q_value_after=q_value_after,
        )
        self.history.append(entry)
        self._history_dirty = True
        # Trim to limit
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]


class SpeciesKnowledgeStore:
    """
    Loads and persists species knowledge across sessions.
    
    Handles:
    - Schema version checking (resets Q-tables on state space changes)
    - Automatic Q-table resizing if dimensions change
    - History tracking for evolution visualization (stored in separate files)
    
    File Structure:
    - {storage_path}: Main knowledge file with Q-tables
    - {storage_path.parent}/species_history/{species}.json: Per-species history
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or settings.config_data_dir / "species_knowledge.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create history directory
        self.history_dir = self.storage_path.parent / "species_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        self.records: Dict[str, SpeciesKnowledgeRecord] = {}
        self._schema_version: int = 0
        self._load()

    @property
    def _data(self) -> Dict[str, SpeciesKnowledgeRecord]:
        return self.records
    
    def _get_history_path(self, monster_type: str) -> Path:
        """Get path to history file for a species."""
        # Sanitize monster type for filename
        safe_name = monster_type.replace("/", "_").replace("\\", "_")
        return self.history_dir / f"{safe_name}.json"

    def _load(self) -> None:
        """Load species knowledge from disk, handling schema migrations."""
        if not self.storage_path.exists():
            self._schema_version = SCHEMA_VERSION
            self._save_raw({})
            return
        
        try:
            raw_data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[SpeciesKnowledgeStore] Corrupted JSON, resetting")
            self._schema_version = SCHEMA_VERSION
            self._save_raw({})
            return
        
        # Check schema version
        stored_version = raw_data.get("_schema_version", 1)
        if stored_version != SCHEMA_VERSION:
            print(f"[SpeciesKnowledgeStore] Schema version changed ({stored_version} -> {SCHEMA_VERSION}), resetting all Q-tables")
            self._schema_version = SCHEMA_VERSION
            self._clear_all_history()  # Clear history files too
            self._save_raw({})
            return
        
        self._schema_version = SCHEMA_VERSION
        
        # Load species records (without history - loaded lazily)
        for monster_type, payload in raw_data.items():
            if monster_type.startswith("_"):
                continue  # Skip metadata keys
            
            table = np.array(payload.get("q_table", []), dtype=np.float32)
            
            # Migrate: if old format had inline history, move it to separate file
            if "history" in payload and payload["history"]:
                self._migrate_inline_history(monster_type, payload["history"])
            
            self.records[monster_type] = SpeciesKnowledgeRecord(
                monster_type=monster_type,
                generation=int(payload.get("generation", 0)),
                encounters=int(payload.get("encounters", 0)),
                total_learning_steps=int(payload.get("total_learning_steps", 0)),
                q_table=table,
                history=[],  # Loaded lazily
                _history_loaded=False,
            )
    
    def _migrate_inline_history(self, monster_type: str, history_data: list) -> None:
        """Migrate inline history from old format to separate file."""
        history_path = self._get_history_path(monster_type)
        if history_path.exists():
            return  # Already migrated
        
        print(f"[SpeciesKnowledgeStore] Migrating {monster_type} history to separate file")
        history = []
        for h in history_data:
            history.append({
                "timestamp": h.get("timestamp", ""),
                "generation": h.get("generation", 0),
                "reward": h.get("reward", 0.0),
                "state_index": h.get("state_index", 0),
                "action": h.get("action", ""),
                "q_value_before": h.get("q_value_before", 0.0),
                "q_value_after": h.get("q_value_after", 0.0),
            })
        
        data = {
            "monster_type": monster_type,
            "schema_version": SCHEMA_VERSION,
            "history": history[-HISTORY_LIMIT:],  # Trim to limit
        }
        history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def _load_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Lazily load history for a species from its separate file."""
        if record._history_loaded:
            return
        
        history_path = self._get_history_path(record.monster_type)
        if not history_path.exists():
            record._history_loaded = True
            return
        
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            
            # Check schema version
            if data.get("schema_version", 1) != SCHEMA_VERSION:
                print(f"[SpeciesKnowledgeStore] History schema mismatch for {record.monster_type}, clearing")
                history_path.unlink()
                record._history_loaded = True
                return
            
            for h in data.get("history", []):
                record.history.append(LearningHistoryEntry(
                    timestamp=h.get("timestamp", ""),
                    generation=h.get("generation", 0),
                    reward=h.get("reward", 0.0),
                    state_index=h.get("state_index", 0),
                    action=h.get("action", ""),
                    q_value_before=h.get("q_value_before", 0.0),
                    q_value_after=h.get("q_value_after", 0.0),
                ))
            record._history_loaded = True
        except (json.JSONDecodeError, Exception) as e:
            print(f"[SpeciesKnowledgeStore] Failed to load history for {record.monster_type}: {e}")
            record._history_loaded = True
    
    def _save_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Save history for a species to its separate file."""
        if not record._history_dirty:
            return
        
        history_path = self._get_history_path(record.monster_type)
        data = record.history_to_dict()
        history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        record._history_dirty = False
    
    def _clear_all_history(self) -> None:
        """Clear all history files (used on schema version change)."""
        if self.history_dir.exists():
            for f in self.history_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
    
    def _save_raw(self, data: dict) -> None:
        """Save raw data with schema version."""
        data["_schema_version"] = SCHEMA_VERSION
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save(self) -> None:
        """Persist all species knowledge to disk."""
        serializable = {
            "_schema_version": SCHEMA_VERSION,
        }
        for mtype, record in self.records.items():
            serializable[mtype] = record.to_dict()
            # Save history to separate file if dirty
            if record._history_dirty:
                self._save_history(record)
        self.storage_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    
    def save_history(self, monster_type: str) -> None:
        """Save history for a specific species (call after batch learning events)."""
        record = self.records.get(monster_type)
        if record and record._history_dirty:
            self._save_history(record)

    def get_or_create(
        self,
        monster_type: str,
        *,
        state_space: int,
        action_count: int,
    ) -> SpeciesKnowledgeRecord:
        """
        Get existing record or create new one for a monster species.
        
        Automatically resizes Q-table if state space changed (preserving
        as much learned knowledge as possible through truncation/padding).
        """
        if monster_type not in self.records:
            table = np.zeros((state_space, action_count), dtype=np.float32)
            self.records[monster_type] = SpeciesKnowledgeRecord(
                monster_type=monster_type,
                generation=0,
                q_table=table,
            )
        record = self.records[monster_type]
        # Resize table if encoder changed (e.g., new bins).
        if record.q_table.shape != (state_space, action_count):
            print(f"[SpeciesKnowledgeStore] Resizing {monster_type} Q-table: {record.q_table.shape} -> ({state_space}, {action_count})")
            padded = np.zeros((state_space, action_count), dtype=np.float32)
            min_states = min(state_space, record.q_table.shape[0])
            min_actions = min(action_count, record.q_table.shape[1])
            padded[:min_states, :min_actions] = record.q_table[:min_states, :min_actions]
            record.q_table = padded
        return record

    def bump_generation(self, monster_type: str, max_generation: int | None = None) -> None:
        """Increment generation counter for a species (capped at max_generation)."""
        record = self.records.get(monster_type)
        if not record:
            return
        if max_generation is not None and record.generation >= max_generation:
            return
        record.generation += 1

    def reset(self, monster_type: str) -> None:
        """Remove all knowledge for a species."""
        if monster_type in self.records:
            del self.records[monster_type]
            # Also remove history file
            history_path = self._get_history_path(monster_type)
            if history_path.exists():
                history_path.unlink()
            self.save()

    def reset_species(
        self,
        monster_type: str,
        *,
        state_space: int,
        action_count: int,
    ) -> SpeciesKnowledgeRecord:
        """Reset a species Q-table to zeros while keeping the generation."""
        gen = 0
        if monster_type in self.records:
            gen = self.records[monster_type].generation
        table = np.zeros((state_space, action_count), dtype=np.float32)
        record = SpeciesKnowledgeRecord(
            monster_type=monster_type,
            generation=gen,
            q_table=table,
            _history_loaded=True,  # Empty history is "loaded"
        )
        self.records[monster_type] = record
        # Clear history file
        history_path = self._get_history_path(monster_type)
        if history_path.exists():
            history_path.unlink()
        return record
    
    def reset_all(self, *, state_space: int, action_count: int) -> None:
        """Reset all species Q-tables (used after schema version change)."""
        print(f"[SpeciesKnowledgeStore] Resetting all species Q-tables")
        self._clear_all_history()  # Clear all history files
        for monster_type in list(self.records.keys()):
            self.reset_species(monster_type, state_space=state_space, action_count=action_count)
        self.save()
    
    def get_history(self, monster_type: str, limit: int = 0) -> List[LearningHistoryEntry]:
        """
        Get learning history for a species.
        
        Args:
            monster_type: Species to get history for
            limit: If > 0, return only the last N entries
        
        Returns:
            List of history entries (newest last)
        """
        record = self.records.get(monster_type)
        if not record:
            return []
        
        # Lazy load history from file
        self._load_history(record)
        
        if limit > 0:
            return record.history[-limit:]
        return record.history
    
    def record_learning_event(
        self,
        monster_type: str,
        *,
        reward: float,
        state_index: int,
        action: str,
        q_value_before: float,
        q_value_after: float,
    ) -> None:
        """
        Record a learning event for history tracking.
        
        Note: Call save_history(monster_type) periodically to persist.
        This allows batching multiple events before writing to disk.
        """
        record = self.records.get(monster_type)
        if not record:
            return
        
        # Ensure history is loaded before adding
        self._load_history(record)
        
        record.add_history_entry(
            reward=reward,
            state_index=state_index,
            action=action,
            q_value_before=q_value_before,
            q_value_after=q_value_after,
        )
        record.total_learning_steps += 1
