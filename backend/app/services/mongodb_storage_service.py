"""
MongoDB-based game persistence service.
Provides the same API interface as StorageService but uses MongoDB instead of JSON files.
"""
import asyncio
from datetime import datetime
from typing import Optional
import logging

from ..db import mongodb_manager

logger = logging.getLogger(__name__)


class MongoDBStorageService:
    """MongoDB-based storage service maintaining compatibility with JSON-based API."""

    _instance: Optional["MongoDBStorageService"] = None

    def __new__(cls) -> "MongoDBStorageService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._save_lock = asyncio.Lock()
        self._initialized = True
        logger.info("[MongoDBStorageService] Initialized")

    @property
    def db(self):
        """Get MongoDB database instance."""
        return mongodb_manager.db

    # ============== Per-Game Save Methods ==============

    async def save_game_by_id(
        self,
        game_id: str,
        game_state: dict,
        reason: str = "manual"
    ) -> bool:
        """
        Save game state to MongoDB.

        Args:
            game_id: Unique identifier for the game
            game_state: Dictionary containing complete game state
            reason: Reason for saving (for logging)

        Returns:
            True if save was successful
        """
        async with self._save_lock:
            try:
                save_data = {
                    "game_id": game_id,
                    "saved_at": datetime.now(),
                    "save_reason": reason,
                    **game_state  # Flatten game state into document
                }

                # Upsert game document
                result = await self.db.games.update_one(
                    {"game_id": game_id},
                    {"$set": save_data},
                    upsert=True
                )

                print(f"[MongoDBStorage] ✓ Saved game {game_id} to MongoDB (reason: {reason})")
                logger.info(f"[MongoDBStorage] Saved game {game_id} (reason: {reason})")
                return True

            except Exception as e:
                logger.error(f"[MongoDBStorage] Error saving game {game_id}: {e}")
                return False

    async def load_game_by_id(self, game_id: str) -> Optional[dict]:
        """
        Load game state from MongoDB.

        Args:
            game_id: Identifier of the game to load

        Returns:
            Game state dictionary, or None if not found
        """
        try:
            doc = await self.db.games.find_one({"game_id": game_id})

            if not doc:
                logger.info(f"[MongoDBStorage] No save found for game {game_id}")
                return None

            # Remove MongoDB-specific fields
            doc.pop("_id", None)
            doc.pop("game_id", None)
            doc.pop("saved_at", None)
            doc.pop("save_reason", None)

            logger.info(f"[MongoDBStorage] Loaded game {game_id}")
            return doc

        except Exception as e:
            logger.error(f"[MongoDBStorage] Error loading game {game_id}: {e}")
            return None

    async def delete_game_save(self, game_id: str) -> bool:
        """
        Delete a game save from MongoDB.

        Args:
            game_id: Identifier of the game to delete

        Returns:
            True if deletion was successful
        """
        try:
            result = await self.db.games.delete_one({"game_id": game_id})

            if result.deleted_count > 0:
                logger.info(f"[MongoDBStorage] Deleted game save: {game_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"[MongoDBStorage] Error deleting game {game_id}: {e}")
            return False

    def list_game_saves(self) -> list[dict]:
        """
        List all game saves from MongoDB (synchronous wrapper).

        Returns:
            List of save metadata dictionaries
        """
        # This method is called synchronously in some places, so we need to handle it
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't use run_until_complete
                # Return empty list and log warning
                logger.warning("[MongoDBStorage] list_game_saves called from async context")
                return []
            return loop.run_until_complete(self._async_list_game_saves())
        except Exception as e:
            logger.error(f"[MongoDBStorage] Error in list_game_saves: {e}")
            return []

    async def _async_list_game_saves(self) -> list[dict]:
        """Internal async implementation of list_game_saves."""
        try:
            saves = []
            cursor = self.db.games.find().sort("saved_at", -1)

            async for doc in cursor:
                saves.append({
                    "game_id": doc.get("game_id"),
                    "file": f"mongodb://{doc.get('game_id')}",  # Virtual path
                    "version": "2.0",
                    "saved_at": doc.get("saved_at").isoformat() if doc.get("saved_at") else None,
                    "name": doc.get("name", "Unknown")
                })

            return saves

        except Exception as e:
            logger.error(f"[MongoDBStorage] Error listing game saves: {e}")
            return []

    # ============== Player Registry Methods ==============

    async def save_player_registry(self, registry_data: dict) -> bool:
        """
        Save player registry to MongoDB.

        Args:
            registry_data: Dictionary containing registry data with 'players' and 'stats'

        Returns:
            True if save was successful
        """
        async with self._save_lock:
            try:
                players_data = registry_data.get("players", {})
                stats_data = registry_data.get("stats", {})

                # Bulk upsert players
                if players_data:
                    from pymongo import UpdateOne

                    player_ops = [
                        UpdateOne(
                            {"token": token},
                            {"$set": {**data, "token": token, "updated_at": datetime.now()}},
                            upsert=True
                        )
                        for token, data in players_data.items()
                    ]

                    if player_ops:
                        await self.db.players.bulk_write(player_ops)

                # Bulk upsert player stats
                if stats_data:
                    from pymongo import UpdateOne

                    stat_ops = [
                        UpdateOne(
                            {"token": token},
                            {"$set": {**data, "token": token, "updated_at": datetime.now()}},
                            upsert=True
                        )
                        for token, data in stats_data.items()
                    ]

                    if stat_ops:
                        await self.db.player_stats.bulk_write(stat_ops)

                print(f"[MongoDBStorage] ✓ Saved player registry to MongoDB: {len(players_data)} players, {len(stats_data)} stats")
                logger.info(f"[MongoDBStorage] Saved player registry: {len(players_data)} players, {len(stats_data)} stats")
                return True

            except Exception as e:
                logger.error(f"[MongoDBStorage] Error saving player registry: {e}")
                return False

    async def load_player_registry(self) -> Optional[dict]:
        """
        Load player registry from MongoDB.

        Returns:
            Registry dictionary with 'players' and 'stats', or None if error
        """
        try:
            # Load all players
            players = {}
            cursor = self.db.players.find()
            async for doc in cursor:
                token = doc.get("token")
                if token:
                    doc.pop("_id", None)
                    doc.pop("token", None)
                    doc.pop("updated_at", None)
                    players[token] = doc

            # Load all player stats
            stats = {}
            cursor = self.db.player_stats.find()
            async for doc in cursor:
                token = doc.get("token")
                if token:
                    doc.pop("_id", None)
                    doc.pop("token", None)
                    doc.pop("updated_at", None)
                    stats[token] = doc

            logger.info(f"[MongoDBStorage] Loaded player registry: {len(players)} players, {len(stats)} stats")

            return {
                "players": players,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"[MongoDBStorage] Error loading player registry: {e}")
            return None

    # ============== Legacy Methods (for backward compatibility) ==============

    async def save_game(
        self,
        game_state: dict,
        save_id: str = "current",
        reason: str = "manual"
    ) -> bool:
        """
        Save complete game state (legacy method).
        Maps to per-game save with save_id as game_id.

        Args:
            game_state: Dictionary containing complete game state
            save_id: Identifier for the save (used as game_id)
            reason: Reason for saving

        Returns:
            True if save was successful
        """
        return await self.save_game_by_id(save_id, game_state, reason)

    async def load_game(self, save_id: str = "current") -> Optional[dict]:
        """
        Load game state (legacy method).

        Args:
            save_id: Identifier of the save to load

        Returns:
            Game state dictionary, or None if not found
        """
        return await self.load_game_by_id(save_id)

    def list_saves(self) -> list[dict]:
        """
        List all available saves (legacy method).

        Returns:
            List of save metadata dictionaries
        """
        return self.list_game_saves()

    async def delete_save(self, save_id: str) -> bool:
        """
        Delete a save (legacy method).

        Args:
            save_id: Identifier of the save to delete

        Returns:
            True if deletion was successful
        """
        return await self.delete_game_save(save_id)

    async def create_backup(self, save_id: str = "current") -> Optional[str]:
        """
        Create a backup of a save.

        Args:
            save_id: Identifier of the save to backup

        Returns:
            Backup save ID, or None if backup failed
        """
        try:
            game_state = await self.load_game(save_id)
            if not game_state:
                return None

            backup_id = f"backup_{save_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            success = await self.save_game(game_state, backup_id, reason="backup")

            return backup_id if success else None

        except Exception as e:
            logger.error(f"[MongoDBStorage] Error creating backup: {e}")
            return None
