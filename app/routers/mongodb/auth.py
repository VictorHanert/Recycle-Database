"""MongoDB-backed Authentication Router (register/login with JWT)."""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_mongodb
from app.repositories.mongodb.user_repository import MongoDBUserRepository
from app.models.mongodb.user import UserCreate as MongoUserCreate, UserMongo, UserResponse as MongoUserResponse
from app.models.mongodb.token import TokenMongo
from pydantic import BaseModel
from app.auth import AuthService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def get_user_repo(db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> MongoDBUserRepository:
    return MongoDBUserRepository(db)


class LoginRequest(BaseModel):
    identifier: str
    password: str


@router.post("/register", response_model=TokenMongo, status_code=status.HTTP_201_CREATED)
async def register_user(user: MongoUserCreate, repo: MongoDBUserRepository = Depends(get_user_repo)):
    """Register a MongoDB user and issue a JWT."""
    if await repo.check_username_exists(user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if await repo.check_email_exists(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    created = await repo.create(user)

    access_token_expires = timedelta(minutes=30000)
    access_token = AuthService.create_access_token(data={"sub": created.username}, expires_delta=access_token_expires)

    return TokenMongo(
        access_token=access_token,
        expires_in=30000 * 60,
        user=created,
    )


@router.post("/login", response_model=TokenMongo)
@limiter.limit("5/minute")
async def login_user(request: Request, payload: LoginRequest, repo: MongoDBUserRepository = Depends(get_user_repo)):
    """Login by username or email against MongoDB and issue JWT."""
    # Fetch user by username/email
    user: Optional[UserMongo] = await repo.get_by_username(payload.identifier)
    if not user:
        user = await repo.get_by_email(payload.identifier)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username/email or password")

    # Verify password
    if not AuthService.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username/email or password")

    if not bool(user.is_active):
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token_expires = timedelta(minutes=30000)
    access_token = AuthService.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return TokenMongo(
        access_token=access_token,
        expires_in=30000 * 60,
        user=MongoUserResponse(
            _id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_active=bool(user.is_active),
            is_admin=bool(user.is_admin),
            product_count=user.product_count or 0,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )
