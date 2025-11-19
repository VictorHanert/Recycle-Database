"""MongoDB database connection and utilities."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from app.config import get_settings

settings = get_settings()

# Global MongoDB client
_mongodb_client: Optional[AsyncIOMotorClient] = None


def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client (creates if not exists)."""
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
    return _mongodb_client


def get_mongodb() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    client = get_mongodb_client()
    return client[settings.mongodb_database]


async def close_mongodb():
    """Close MongoDB connection."""
    global _mongodb_client
    if _mongodb_client:
        _mongodb_client.close()
        _mongodb_client = None


async def init_mongodb():
    """Initialize MongoDB indexes and constraints."""
    db = get_mongodb()
    
    # Users collection indexes
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)
    
    # Products collection indexes
    await db.products.create_index("seller_id")
    await db.products.create_index("status")
    await db.products.create_index([("title", "text"), ("description", "text")])  # Full-text search
    
    # Favorites and messages are not migrated to MongoDB (only users and products)
    # These collections would be created if you add MongoDB-specific features
    # await db.favorites.create_index([("user_id", 1), ("product_id", 1)], unique=True)
    # await db.messages.create_index("conversation_id")
    # await db.messages.create_index("participants.user_id")    print("MongoDB indexes created")
