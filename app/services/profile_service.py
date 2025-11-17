"""Profile service for user profile operations."""
from typing import Optional, List
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user_schema import UserUpdate, ProfileUpdate, UserProfileResponse, PublicUserProfile
from app.schemas.location_schema import LocationCreate
from app.repositories.base import UserRepositoryInterface, ProductRepositoryInterface, LocationRepositoryInterface


class ProfileService:
    """Service class for user profile operations"""
    
    def __init__(
        self, 
        user_repository: UserRepositoryInterface, 
        product_repository: ProductRepositoryInterface,
        location_repository: LocationRepositoryInterface
    ):
        self.user_repository = user_repository
        self.product_repository = product_repository
        self.location_repository = location_repository

    def get_user_profile(self, user_id: int) -> Optional[UserProfileResponse]:
        """Get detailed user profile with product count"""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get product count
        product_count = self.product_repository.count_by_seller(user_id)

        # Convert to response model
        user_data = UserProfileResponse.model_validate(user)
        user_data.product_count = product_count
        return user_data

    def get_public_profile(self, user_id: int) -> Optional[PublicUserProfile]:
        """Get public user profile (visible to all users)"""
        user = self.user_repository.get_by_id(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )

        # Get active product count for public profile
        # Note: We would need a count_active_by_seller method in the repository for exact behavior
        # For now, using the general count method
        product_count = self.product_repository.count_by_seller(user_id)

        return PublicUserProfile(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            location=user.location,
            created_at=user.created_at,
            product_count=product_count
        )

    def update_profile(self, user_id: int, profile_update: ProfileUpdate) -> User:
        """Update user profile information"""
        # Convert ProfileUpdate to UserUpdate
        user_update_data = profile_update.model_dump(exclude_unset=True)
        user_update = UserUpdate.model_validate(user_update_data)
        
        user = self.user_repository.update(user_id, user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def add_user_location(self, user_id: int, location_data: LocationCreate) -> User:
        """Add or update user location"""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get or create location
        location = self.location_repository.get_or_create(location_data.city, location_data.postcode)
        
        # Update user with new location
        user_update = UserUpdate.model_validate({"location_id": location.id})
        updated_user = self.user_repository.update(user_id, user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user location"
            )
        
        return updated_user

    def remove_user_location(self, user_id: int) -> User:
        """Remove user location"""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update user to remove location
        user_update = UserUpdate.model_validate({"location_id": None})
        updated_user = self.user_repository.update(user_id, user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove user location"
            )
        
        return updated_user

    def get_user_products(self, user_id: int, skip: int = 0, limit: int = 20) -> List:
        """Get products by user"""
        # Verify user exists
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return self.product_repository.get_by_seller(user_id, skip, limit)

    def get_user_statistics(self, user_id: int) -> dict:
        """Get user statistics"""
        # Verify user exists
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        product_count = self.product_repository.count_by_seller(user_id)
        
        return {
            "total_products": product_count,
            "user_since": user.created_at,
            "is_active": user.is_active,
            "has_location": user.location_id is not None
        }

    def delete_user_account(self, user_id: int) -> bool:
        """Delete user account and all related data (admin only)"""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user's products first
        user_products = self.product_repository.get_by_seller(user_id, skip=0, limit=1000)
        
        for product in user_products:
            success = self.product_repository.delete(product.id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete product {product.id}"
                )
        
        success = self.user_repository.delete(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        return True
