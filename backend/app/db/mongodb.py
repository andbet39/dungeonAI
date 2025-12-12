"""
MongoDB connection management for DungeonAI.
Uses Motor (async MongoDB driver) for FastAPI compatibility.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging
import certifi

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Singleton MongoDB connection manager."""

    _instance: Optional["MongoDBManager"] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None

    def __new__(cls) -> "MongoDBManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(
        self,
        connection_string: str,
        database_name: str = "dungeonai_db"
    ) -> None:
        """
        Connect to MongoDB with connection pooling.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use

        Raises:
            Exception: If connection fails
        """
        if self._client is not None:
            logger.info("[MongoDB] Already connected")
            return

        logger.info(f"[MongoDB] Attempting to connect to database: {database_name}")
        try:
            self._client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=45000,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where()  # Use certifi's CA bundle for SSL verification
            )

            self._db = self._client[database_name]

            # Verify connection
            logger.info("[MongoDB] Verifying connection with ping...")
            await self._client.admin.command('ping')
            logger.info(f"[MongoDB] Connected to database: {database_name}")

            # Create indexes
            await self._create_indexes()

        except Exception as e:
            logger.error(f"[MongoDB] Connection failed: {e}")
            self._client = None
            self._db = None
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("[MongoDB] Disconnected")

    async def _create_indexes(self) -> None:
        """Create all necessary indexes for optimal query performance."""
        if self._db is None:
            return

        try:
            # Games collection indexes
            await self._db.games.create_index("game_id", unique=True)
            await self._db.games.create_index("last_activity")
            await self._db.games.create_index("created_at")

            # Users collection indexes
            await self._db.users.create_index("user_id", unique=True)
            await self._db.users.create_index("email", unique=True)

            # Players collection indexes
            await self._db.players.create_index("token", unique=True)
            await self._db.players.create_index("user_id")  # For querying all profiles of a user

            # Player stats collection indexes
            await self._db.player_stats.create_index("token", unique=True)
            await self._db.player_stats.create_index(
                [("experience_earned", -1)]  # For leaderboard queries
            )

            # Species knowledge collection indexes
            await self._db.species_knowledge.create_index("monster_type", unique=True)
            await self._db.species_knowledge.create_index("schema_version")

            # Species history collection indexes
            await self._db.species_history.create_index("monster_type", unique=True)

            # Spawn rates collection indexes
            await self._db.spawn_rates.create_index("config_version", unique=True)

            # Sandbox collection indexes
            await self._db.sandbox.create_index("singleton", unique=True)

            logger.info("[MongoDB] Indexes created successfully")

        except Exception as e:
            logger.error(f"[MongoDB] Error creating indexes: {e}")
            raise

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance.

        Returns:
            AsyncIOMotorDatabase instance

        Raises:
            RuntimeError: If MongoDB is not connected
        """
        if self._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._db

    @property
    def is_connected(self) -> bool:
        """Check if MongoDB connection is active."""
        return self._client is not None and self._db is not None

    def get_collection(self, collection_name: str):
        """Get a MongoDB collection by name."""
        if self._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._db[collection_name]


# Global MongoDB manager instance
mongodb_manager = MongoDBManager()
