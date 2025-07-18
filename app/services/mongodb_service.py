from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure
from typing import Optional
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class MongoDBService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.settings = get_settings()

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.settings.mongodb_uri)
            self.database = self.client["ai-driven-recruitment"]
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Get a collection from the database"""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]


_mongodb_service = MongoDBService()


async def get_mongodb() -> MongoDBService:
    """Dependency to get MongoDB service"""
    return _mongodb_service
