"""User schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from .location_schema import LocationResponse


# ============================================
# BASE SCHEMAS
# ============================================

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    full_name: Optional[str] = Field(None, max_length=100)


# ============================================
# REQUEST SCHEMAS (Input)
# ============================================

class UserCreate(UserBase):
    """Schema for user registration (auth/register)"""
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login (auth/login) - accepts either username or email"""
    identifier: str = Field(..., min_length=3, max_length=100, description="Username or email address")
    password: str = Field(..., min_length=1, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user updates (admin can update all fields)"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=64)
    location_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class ProfileUpdate(BaseModel):
    """Schema for profile updates (users can only update their own profile fields)"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None


# ============================================
# RESPONSE SCHEMAS (Output)
# ============================================

class UserResponse(UserBase):
    """Standard user response (used in most endpoints)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: Optional[str] = None
    location_id: Optional[int] = None
    location: Optional[LocationResponse] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime


class UserProfileResponse(UserResponse):
    """Enhanced user profile response (profile/me endpoint)"""
    model_config = ConfigDict(from_attributes=True)
    
    product_count: Optional[int] = None


class PublicUserProfile(BaseModel):
    """Public user profile visible to all users (profile/{user_id} endpoint)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    full_name: Optional[str] = None
    location: Optional[LocationResponse] = None
    created_at: datetime
    product_count: Optional[int] = None


class UserListResponse(BaseModel):
    """Paginated user list response (admin/users endpoint)"""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ============================================
# AUTHENTICATION SCHEMAS
# ============================================

class Token(BaseModel):
    """JWT Token response (auth/login endpoint)"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse
