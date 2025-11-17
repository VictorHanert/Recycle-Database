"""Location Router: Endpoints for managing locations."""
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.dependencies import get_location_service
from app.schemas.location_schema import LocationCreate, LocationResponse, LocationUpdate
from app.services.location_service import LocationService

router = APIRouter()

@router.get("/search", response_model=List[LocationResponse])
async def search_locations(
    q: str = Query(..., min_length=1, description="Search query for city or postcode"),
    location_service: LocationService = Depends(get_location_service)
):
    """Search locations by city or postcode"""
    return location_service.search_locations(q)


@router.get("/", response_model=List[LocationResponse])
async def get_all_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    location_service: LocationService = Depends(get_location_service)
):
    """Get all locations with pagination"""
    return location_service.get_all_locations(skip, limit)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    location_service: LocationService = Depends(get_location_service)
):
    """Get location by ID"""
    location = location_service.get_location_by_id(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    return location


@router.post("/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    location_service: LocationService = Depends(get_location_service)
):
    """Create a new location (authenticated users only)"""
    return location_service.create_location(location)

@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_update: LocationUpdate,
    location_service: LocationService = Depends(get_location_service)
):
    """Update an existing location (authenticated users only)"""
    return location_service.update_location(location_id, location_update)


@router.delete("/{location_id}")
async def delete_location(
    location_id: int,
    location_service: LocationService = Depends(get_location_service)
):
    """Delete a location (authenticated users only)"""
    return location_service.delete_location(location_id)
