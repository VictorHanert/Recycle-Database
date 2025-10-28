"""Profile router for user profile CRUD operations."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.models.user import User
from app.dependencies import (
    get_current_active_user, 
    get_current_user_optional, 
    get_profile_service
)
from app.schemas.user import UserProfileResponse, ProfileUpdate, PublicUserProfile
from app.schemas.location import LocationCreate
from app.schemas.product import ProductResponse
from app.services.profile_service import ProfileService

router = APIRouter()

# Profile management endpoints
@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get current user's detailed profile"""
    return profile_service.get_user_profile(current_user.id)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Update current user's profile information"""
    profile_service.update_profile(current_user.id, profile_update)
    return profile_service.get_user_profile(current_user.id)


@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Delete current user's account and all associated data"""
    profile_service.delete_user_account(current_user.id)
    return {"message": "Account deleted successfully"}

@router.get("/me/products", response_model=List[ProductResponse])
async def get_my_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get current user's products (all statuses)"""
    products = profile_service.get_user_products(current_user.id, skip, limit)
    return products


# Location management endpoints
@router.post("/me/location", response_model=UserProfileResponse)
async def add_my_location(
    location_data: LocationCreate,
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Add or update current user's location"""
    profile_service.add_user_location(current_user.id, location_data)
    return profile_service.get_user_profile(current_user.id)


@router.delete("/me/location", response_model=UserProfileResponse)
async def remove_my_location(
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Remove current user's location"""
    profile_service.remove_user_location(current_user.id)
    return profile_service.get_user_profile(current_user.id)


# Public profile endpoints
@router.get("/{user_id}", response_model=PublicUserProfile)
async def get_public_profile(
    user_id: int,
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get public user profile (visible to all users)"""
    return profile_service.get_public_profile(user_id)


@router.get("/{user_id}/products", response_model=List[ProductResponse])
async def get_user_products(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get products for a specific user (only active products for public view)"""
    products = profile_service.get_user_products(user_id, skip, limit
    )
    return products
