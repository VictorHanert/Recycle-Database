"""User schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from .location import LocationResponse


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user updates"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=64)
    location_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class UserResponse(UserBase):
    """Schema for user response (without sensitive data)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: Optional[str] = None
    location_id: Optional[int] = None
    location: Optional[LocationResponse] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """Schema for user in database (with hashed password)"""
    hashed_password: str


# Token schemas for authentication
class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    expires: Optional[datetime] = None


# Profile-specific schemas
class ProfileUpdate(BaseModel):
    """Schema for profile updates"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserProfileResponse(UserResponse):
    """Enhanced user profile response with additional data"""
    model_config = ConfigDict(from_attributes=True)
    
    # This would include product count, etc.
    product_count: Optional[int] = None


class PublicUserProfile(BaseModel):
    """Public user profile (visible to all users)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    full_name: Optional[str] = None
    location: Optional[LocationResponse] = None
    created_at: datetime
    product_count: Optional[int] = None


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    total_pages: int
