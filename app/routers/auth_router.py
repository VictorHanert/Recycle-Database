from fastapi import APIRouter, Depends, status, Request
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.dependencies import get_auth_service

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)

# Authentication endpoints
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    """Register a new user and automatically log them in"""
    db_user = auth_service.register_user(user)
    
    # Automatically log in the user after registration
    access_token_expires = timedelta(minutes=30000)
    access_token = AuthService.create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30000 * 60,  # 30 minutes in seconds
        user=UserResponse.model_validate(db_user)
    )

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_user(request: Request, user: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    """Login user and return JWT token"""
    # Authenticate user
    db_user = auth_service.authenticate_user(user.identifier, user.password)

    # Create access token
    access_token_expires = timedelta(minutes=30000)
    access_token = AuthService.create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30000 * 60,  # 30 minutes in seconds
        user=UserResponse.model_validate(db_user)
    )
