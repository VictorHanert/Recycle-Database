"""MongoDB User Repository."""
from typing import Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.mongodb.user import UserMongo, UserCreate, UserResponse
from app.auth import AuthService


class MongoDBUserRepository:
    """MongoDB implementation of user repository."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users
    
    async def create(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        # Hash password
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        now = datetime.now(timezone.utc)
        
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "is_active": True,
            "is_admin": False,
            "product_count": 0,
            "created_at": now,
            "updated_at": now
        }
        
        result = await self.collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        
        return UserResponse(**user_dict)
    
    async def get_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        if not ObjectId.is_valid(user_id):
            return None
        
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
            return UserResponse(**user)
        return None
    
    async def get_by_username(self, username: str) -> Optional[UserMongo]:
        """Get user by username."""
        user = await self.collection.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
            return UserMongo(**user)
        return None
    
    async def get_by_email(self, email: str) -> Optional[UserMongo]:
        """Get user by email."""
        user = await self.collection.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
            return UserMongo(**user)
        return None
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get all users with pagination."""
        cursor = self.collection.find().skip(skip).limit(limit)
        users = []
        async for user in cursor:
            user["_id"] = str(user["_id"])
            users.append(UserResponse(**user))
        return users
    
    async def update(self, user_id: str, update_data: dict) -> Optional[UserResponse]:
        """Update user."""
        if not ObjectId.is_valid(user_id):
            return None
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_data:
            return await self.get_by_id(user_id)
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return UserResponse(**result)
        return None
    
    async def delete(self, user_id: str) -> bool:
        """Delete user."""
        if not ObjectId.is_valid(user_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0
    
    async def check_username_exists(self, username: str) -> bool:
        """Check if username exists."""
        count = await self.collection.count_documents({"username": username})
        return count > 0
    
    async def check_email_exists(self, email: str) -> bool:
        """Check if email exists."""
        count = await self.collection.count_documents({"email": email})
        return count > 0
    
    async def increment_product_count(self, user_id: str):
        """Increment user's product count."""
        if ObjectId.is_valid(user_id):
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"product_count": 1}}
            )
    
    async def decrement_product_count(self, user_id: str):
        """Decrement user's product count."""
        if ObjectId.is_valid(user_id):
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"product_count": -1}}
            )
