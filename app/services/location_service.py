"""Location service for CRUD operations."""
from typing import List, Optional
from fastapi import HTTPException, status

from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate
from app.repositories.base import LocationRepositoryInterface


class LocationService:
    """Service class for location operations"""

    def __init__(self, location_repository: LocationRepositoryInterface):
        self.location_repository = location_repository

    def create_location(self, location: LocationCreate) -> Location:
        """Create a new location or return existing one"""
        return self.location_repository.get_or_create(location.city, location.postcode)

    def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID"""
        return self.location_repository.get_by_id(location_id)

    def get_all_locations(self, skip: int = 0, limit: int = 100) -> List[Location]:
        """Get all locations with pagination"""
        return self.location_repository.get_all(skip, limit)

    def search_locations(self, query: str) -> List[Location]:
        """Search locations by city or postcode"""
        return self.location_repository.search_locations(query, 10)

    def update_location(self, location_id: int, location_update: LocationUpdate) -> Location:
        """Update location information"""
        update_data = location_update.model_dump(exclude_unset=True)
        
        updated_location = self.location_repository.update(
            location_id, 
            city=update_data.get('city'),
            postcode=update_data.get('postcode')
        )
        
        if not updated_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        
        return updated_location

    def delete_location(self, location_id: int) -> bool:
        """Delete a location"""
        success = self.location_repository.delete(location_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        return success
