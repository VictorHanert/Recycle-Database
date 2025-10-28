from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.services.product_service import ProductService
from app.services.profile_service import ProfileService
from app.services.location_service import LocationService
from app.db.mysql import get_db
from app.models.user import User
from app.repositories.mysql.factory import get_repository_factory, RepositoryFactory

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


# Repository Dependencies
def get_repository_factory_dep(db: Session = Depends(get_db)) -> RepositoryFactory:
    """Get repository factory instance"""
    return get_repository_factory(db)


# Service Dependencies
def get_auth_service(repo_factory: RepositoryFactory = Depends(get_repository_factory_dep)) -> AuthService:
    """Get auth service instance"""
    return AuthService(repo_factory.get_user_repository())


def get_product_service(repo_factory: RepositoryFactory = Depends(get_repository_factory_dep)) -> ProductService:
    """Get product service instance"""
    return ProductService(
        repo_factory.get_product_repository(),
        repo_factory.get_user_repository()
    )


def get_profile_service(repo_factory: RepositoryFactory = Depends(get_repository_factory_dep)) -> ProfileService:
    """Get profile service instance"""
    return ProfileService(
        repo_factory.get_user_repository(),
        repo_factory.get_product_repository(),
        repo_factory.get_location_repository()
    )


def get_location_service(repo_factory: RepositoryFactory = Depends(get_repository_factory_dep)) -> LocationService:
    """Get location service instance"""
    return LocationService(repo_factory.get_location_repository())


# Authentication Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user"""
    username = AuthService.verify_token(credentials.credentials)
    user = auth_service.get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        username = AuthService.verify_token(credentials.credentials)
        user = auth_service.get_user_by_username(username)
        if user and user.is_active:
            return user
    except HTTPException:
        pass
    
    return None
