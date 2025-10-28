from fastapi import APIRouter, Depends, status
from datetime import timedelta

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.dependencies import get_auth_service

router = APIRouter()

# Authentication endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    """Register a new user"""
    db_user = auth_service.register_user(user)
    return db_user

@router.post("/login", response_model=Token)
async def login_user(user: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    """Login user and return JWT token"""
    # Authenticate user
    db_user = auth_service.authenticate_user(user.username, user.password)

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
