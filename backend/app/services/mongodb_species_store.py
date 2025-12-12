"""
MongoDB-based species knowledge persistence for learning monsters.
Provides the same API as SpeciesKnowledgeStore but uses MongoDB for storage.
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional
import logging

import numpy as np
from bson import Binary

from ..db import mongodb_manager
from ..domain.intelligence.learning import SCHEMA_VERSION
from ..domain.intelligence.generations import (
    SpeciesKnowledgeRecord,
    LearningHistoryEntry,
    HISTORY_LIMIT
)

logger = logging.getLogger(__name__)


class MongoDBSpeciesKnowledgeStore:
    """
    MongoDB-based species knowledge store.
    Maintains compatibility with file-based SpeciesKnowledgeStore API.
    """

    def __init__(self) -> None:
        self.records: Dict[str, SpeciesKnowledgeRecord] = {}
        self._schema_version: int = SCHEMA_VERSION
        self._loaded = False
        logger.info("[MongoDBSpeciesStore] Initialized")
        # Load existing knowledge from MongoDB
        self._load()

    @property
    def db(self):
        """Get MongoDB database instance."""
        return mongodb_manager.db

    @property
    def _data(self) -> Dict[str, SpeciesKnowledgeRecord]:
        """For compatibility with existing code."""
        return self.records

    def _load(self) -> None:
        """
        Load species knowledge from MongoDB (synchronous wrapper).
        Called during initialization.
        """
        if self._loaded:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from async context, schedule it
                asyncio.create_task(self._async_load())
            else:
                loop.run_until_complete(self._async_load())
        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Error in _load: {e}")
        finally:
            self._loaded = True

    async def _async_load(self) -> None:
        """Load all species knowledge from MongoDB."""
        try:
            cursor = self.db.species_knowledge.find()
            count = 0

            async for doc in cursor:
                count += 1
                monster_type = doc.get("monster_type")
                if not monster_type:
                    continue

                # Check schema version
                stored_version = doc.get("schema_version", 1)
                if stored_version != SCHEMA_VERSION:
                    logger.warning(
                        f"[MongoDBSpeciesStore] Schema mismatch for {monster_type}: "
                        f"{stored_version} != {SCHEMA_VERSION}, resetting"
                    )
                    # Delete outdated record
                    await self.db.species_knowledge.delete_one({"monster_type": monster_type})
                    await self.db.species_history.delete_one({"monster_type": monster_type})
                    continue

                # Deserialize Q-table from Binary
                q_table_binary = doc.get("q_table")
                q_table_shape = tuple(doc.get("q_table_shape", [0, 0]))

                if q_table_binary and q_table_shape[0] > 0:
                    q_table = np.frombuffer(q_table_binary, dtype=np.float32)
                    q_table = q_table.reshape(q_table_shape).copy()  # Create writable copy
                else:
                    q_table = np.zeros(q_table_shape, dtype=np.float32)

                # Create record (history loaded lazily)
                self.records[monster_type] = SpeciesKnowledgeRecord(
                    monster_type=monster_type,
                    generation=int(doc.get("generation", 0)),
                    encounters=int(doc.get("encounters", 0)),
                    total_learning_steps=int(doc.get("total_learning_steps", 0)),
                    q_table=q_table,
                    history=[],  # Loaded lazily
                    _history_loaded=False,
                )

            print(f"[MongoDBSpeciesStore] ✓ Loaded {len(self.records)} species knowledge records from MongoDB")
            logger.info(f"[MongoDBSpeciesStore] Loaded {len(self.records)} species records")

        except Exception as e:
            print(f"[MongoDBSpeciesStore] ✗ Error loading species knowledge: {e}")
            logger.error(f"[MongoDBSpeciesStore] Error loading species knowledge: {e}")

    def _load_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Lazily load history for a species from MongoDB (synchronous wrapper)."""
        if record._history_loaded:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context - need to run synchronously using create_task and wait
                # Create new event loop in thread for synchronous loading
                import asyncio
                try:
                    # Try to run in current loop if possible
                    asyncio.run_coroutine_threadsafe(self._async_load_history(record), loop).result(timeout=5)
                except:
                    # Fallback: schedule task but mark as loaded to avoid infinite loop
                    asyncio.create_task(self._async_load_history(record))
            else:
                loop.run_until_complete(self._async_load_history(record))
        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Error in _load_history: {e}")
            record._history_loaded = True

    async def _async_load_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Internal async implementation of history loading."""
        if record._history_loaded:
            return

        try:
            doc = await self.db.species_history.find_one({"monster_type": record.monster_type})

            if not doc:
                record._history_loaded = True
                return

            # Check schema version
            if doc.get("schema_version", 1) != SCHEMA_VERSION:
                logger.warning(
                    f"[MongoDBSpeciesStore] History schema mismatch for {record.monster_type}, clearing"
                )
                await self.db.species_history.delete_one({"monster_type": record.monster_type})
                record._history_loaded = True
                return

            # Load history entries
            for h in doc.get("history", []):
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
            logger.info(f"[MongoDBSpeciesStore] Loaded {len(record.history)} history entries for {record.monster_type}")

        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Failed to load history for {record.monster_type}: {e}")
            record._history_loaded = True

    def _save_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Save history for a species to MongoDB (synchronous wrapper)."""
        if not record._history_dirty:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_save_history(record))
            else:
                loop.run_until_complete(self._async_save_history(record))
        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Error in _save_history: {e}")

    async def _async_save_history(self, record: SpeciesKnowledgeRecord) -> None:
        """Internal async implementation of history saving."""
        try:
            history_data = {
                "monster_type": record.monster_type,
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
                    for h in record.history[-HISTORY_LIMIT:]  # Limit history size
                ],
                "last_updated": datetime.now()
            }

            await self.db.species_history.update_one(
                {"monster_type": record.monster_type},
                {"$set": history_data},
                upsert=True
            )

            record._history_dirty = False
            logger.debug(f"[MongoDBSpeciesStore] Saved history for {record.monster_type}")

        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Error saving history for {record.monster_type}: {e}")

    def save(self) -> None:
        """Persist all species knowledge to MongoDB (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_save())
            else:
                loop.run_until_complete(self._async_save())
        except Exception as e:
            logger.error(f"[MongoDBSpeciesStore] Error in save: {e}")

    async def _async_save(self) -> None:
        """Internal async implementation of save."""
        try:
            from pymongo import UpdateOne

            ops = []

            for monster_type, record in self.records.items():
                # Serialize Q-table to Binary
                q_table_binary = Binary(record.q_table.tobytes())

                doc = {
                    "monster_type": monster_type,
                    "generation": record.generation,
                    "encounters": record.encounters,
                    "total_learning_steps": record.total_learning_steps,
                    "q_table_shape": list(record.q_table.shape),
                    "q_table": q_table_binary,
                    "schema_version": SCHEMA_VERSION,
                    "last_updated": datetime.now()
                }

                ops.append(UpdateOne(
                    {"monster_type": monster_type},
                    {
                        "$set": doc,
                        "$setOnInsert": {"created_at": datetime.now()}
                    },
                    upsert=True
                ))

                # Save history if dirty
                if record._history_dirty:
                    await self._async_save_history(record)

            if ops:
                await self.db.species_knowledge.bulk_write(ops)
                print(f"[MongoDBSpeciesStore] ✓ Saved {len(ops)} species knowledge records to MongoDB")
                logger.info(f"[MongoDBSpeciesStore] Saved {len(ops)} species records")

        except Exception as e:
            print(f"[MongoDBSpeciesStore] ✗ Error saving species knowledge: {e}")
            logger.error(f"[MongoDBSpeciesStore] Error saving species knowledge: {e}")

    def save_history(self, monster_type: str) -> None:
        """Save history for a specific species."""
        record = self.records.get(monster_type)
        if record and record._history_dirty:
            self._save_history(record)

    def get_history(self, monster_type: str, limit: int = 0):
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

        # Lazy load history from MongoDB
        self._load_history(record)

        if limit > 0:
            return record.history[-limit:]
        return record.history

    async def get_history_async(self, monster_type: str, limit: int = 0):
        """
        Get learning history for a species (async version for API endpoints).

        Args:
            monster_type: Species to get history for
            limit: If > 0, return only the last N entries

        Returns:
            List of history entries (newest last)
        """
        record = self.records.get(monster_type)
        if not record:
            return []

        # Lazy load history from MongoDB
        await self._async_load_history(record)

        if limit > 0:
            return record.history[-limit:]
        return record.history

    def get_or_create(
        self,
        monster_type: str,
        *,
        state_space: int,
        action_count: int,
    ) -> SpeciesKnowledgeRecord:
        """
        Get existing record or create new one for a monster species.

        Automatically resizes Q-table if state space changed.
        """
        if monster_type not in self.records:
            table = np.zeros((state_space, action_count), dtype=np.float32)
            self.records[monster_type] = SpeciesKnowledgeRecord(
                monster_type=monster_type,
                generation=0,
                q_table=table,
            )

        record = self.records[monster_type]

        # Resize table if needed
        if record.q_table.shape != (state_space, action_count):
            logger.info(
                f"[MongoDBSpeciesStore] Resizing {monster_type} Q-table: "
                f"{record.q_table.shape} -> ({state_space}, {action_count})"
            )
            padded = np.zeros((state_space, action_count), dtype=np.float32)
            min_states = min(state_space, record.q_table.shape[0])
            min_actions = min(action_count, record.q_table.shape[1])
            padded[:min_states, :min_actions] = record.q_table[:min_states, :min_actions]
            record.q_table = padded

        return record

    def bump_generation(self, monster_type: str, max_generation: Optional[int] = None) -> None:
        """Increment generation counter for a species (capped at max_generation)."""
        record = self.records.get(monster_type)
        if not record:
            return

        record.generation += 1

        if max_generation is not None and record.generation > max_generation:
            record.generation = max_generation

        logger.debug(f"[MongoDBSpeciesStore] {monster_type} generation: {record.generation}")

    def record_learning_event(
        self,
        monster_type: str,
        reward: float,
        state_index: int,
        action: str,
        q_value_before: float,
        q_value_after: float
    ) -> None:
        """Record a learning event to history."""
        record = self.records.get(monster_type)
        if not record:
            return

        # Ensure history is loaded
        if not record._history_loaded:
            self._load_history(record)

        record.add_history_entry(
            reward=reward,
            state_index=state_index,
            action=action,
            q_value_before=q_value_before,
            q_value_after=q_value_after
        )
