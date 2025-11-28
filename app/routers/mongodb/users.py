"""MongoDB Users API Router."""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_mongodb
from app.repositories.mongodb.user_repository import MongoDBUserRepository
from app.models.mongodb.user import UserCreate, UserResponse
from app.dependencies import get_current_user, AuthenticatedUser


router = APIRouter()


def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> MongoDBUserRepository:
    """Dependency to get user repository."""
    return MongoDBUserRepository(db)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    repo: MongoDBUserRepository = Depends(get_user_repository)
):
    """Create a new user in MongoDB."""
    # Check if username exists
    if await repo.check_username_exists(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    if await repo.check_email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    return await repo.create(user_data)


@router.get("", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    repo: MongoDBUserRepository = Depends(get_user_repository)
):
    """Get all users from MongoDB."""
    return await repo.get_all(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    repo: MongoDBUserRepository = Depends(get_user_repository)
):
    """Get user by ID from MongoDB."""
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/username/{username}", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    repo: MongoDBUserRepository = Depends(get_user_repository)
):
    """Get user by username from MongoDB."""
    user = await repo.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    repo: MongoDBUserRepository = Depends(get_user_repository),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete user from MongoDB (admin only)."""
    if not bool(current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    success = await repo.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
