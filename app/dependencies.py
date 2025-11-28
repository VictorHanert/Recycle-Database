from typing import Optional
from types import SimpleNamespace
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth_service import AuthService
from app.db.mongodb import get_mongodb
from app.repositories.mongodb.user_repository import MongoDBUserRepository

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

AuthenticatedUser = SimpleNamespace

# Authentication Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current authenticated principal from JWT without MySQL.
    Looks up MongoDB user for flags when available; otherwise defaults.
    Returns a lightweight object with username/is_active/is_admin attributes.
    """
    username = AuthService.verify_token(credentials.credentials)

    # Try to enrich with MongoDB user flags
    try:
        db = get_mongodb()
        user_repo = MongoDBUserRepository(db)
        mongo_user = await user_repo.get_by_username(username)
        if mongo_user:
            return SimpleNamespace(
                id=None,
                username=str(mongo_user.username),
                is_active=bool(mongo_user.is_active),
                is_admin=bool(mongo_user.is_admin),
            )
    except Exception:
        # Fallback below if MongoDB unavailable or user missing
        pass

    # Fallback principal if user not found in MongoDB
    return SimpleNamespace(
        id=None,
        username=username,
        is_active=True,
        is_admin=False,
    )


async def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(current_user = Depends(get_current_active_user)):
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
):
    """Get current principal if authenticated, else None (no MySQL)."""
    if not credentials:
        return None
    try:
        username = AuthService.verify_token(credentials.credentials)
        db = get_mongodb()
        user_repo = MongoDBUserRepository(db)
        mongo_user = await user_repo.get_by_username(username)
        if mongo_user and bool(mongo_user.is_active):
            return SimpleNamespace(
                id=None,
                username=str(mongo_user.username),
                is_active=bool(mongo_user.is_active),
                is_admin=bool(mongo_user.is_admin),
            )
        # Fallback principal if token valid but mongo user missing
        return SimpleNamespace(id=None, username=username, is_active=True, is_admin=False)
    except HTTPException:
        return None
