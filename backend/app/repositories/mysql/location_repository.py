"""MySQL implementation of the Location Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.repositories.base import LocationRepositoryInterface
from app.models.location import Location


class MySQLLocationRepository(LocationRepositoryInterface):
    """MySQL implementation of location repository operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        return self.db.query(Location).filter(Location.id == location_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Location]:
        """Get all locations with pagination."""
        return self.db.query(Location).offset(skip).limit(limit).all()
    
    def get_by_city_and_postcode(self, city: str, postcode: str) -> Optional[Location]:
        """Get location by city and postcode."""
        return self.db.query(Location).filter(
            Location.city == city,
            Location.postcode == postcode
        ).first()
    
    def create(self, city: str, postcode: str) -> Location:
        """Create a new location."""
        try:
            db_location = Location(
                city=city,
                postcode=postcode
            )
            self.db.add(db_location)
            self.db.commit()
            self.db.refresh(db_location)
            return db_location
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location creation failed due to database constraint"
            ) from e
    
    def get_or_create(self, city: str, postcode: str) -> Location:
        """Get existing location or create new one."""
        # First, try to get existing location
        existing_location = self.get_by_city_and_postcode(city, postcode)
        if existing_location:
            return existing_location
        
        # If not found, create new location
        return self.create(city, postcode)
    
    def search_by_city(self, city: str, limit: int = 10) -> List[Location]:
        """Search locations by city name."""
        return self.db.query(Location).filter(
            Location.city.ilike(f"%{city}%")
        ).limit(limit).all()
    
    def search_locations(self, query: str, limit: int = 10) -> List[Location]:
        """Search locations by city or postcode."""
        return self.db.query(Location).filter(
            (Location.city.ilike(f"%{query}%")) | 
            (Location.postcode.ilike(f"%{query}%"))
        ).limit(limit).all()
    
    def count_total_locations(self) -> int:
        """Count total number of locations."""
        return self.db.query(Location).count()
    
    def update(self, location_id: int, city: Optional[str] = None, postcode: Optional[str] = None) -> Optional[Location]:
        """Update location information."""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return None
        
        if city is not None:
            location.city = city
        if postcode is not None:
            location.postcode = postcode
        
        try:
            self.db.commit()
            self.db.refresh(location)
            return location
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed due to database constraint"
            ) from e
    
    def delete(self, location_id: int) -> bool:
        """Delete a location."""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return False
        
        # Check if location is being used by users or products
        if hasattr(location, 'users') and location.users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete location that is in use by users"
            )
        
        if hasattr(location, 'products') and location.products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete location that is in use by products"
            )
        
        try:
            self.db.delete(location)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delete failed due to database constraint"
            ) from e
