"""Location schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationBase(BaseModel):
    """Base location schema with common fields"""
    city: str = Field(..., min_length=1, max_length=120)
    postcode: str = Field(..., min_length=1, max_length=32)


class LocationCreate(LocationBase):
    """Schema for location creation"""
    pass


class LocationUpdate(BaseModel):
    """Schema for location updates"""
    city: Optional[str] = Field(None, min_length=1, max_length=120)
    postcode: Optional[str] = Field(None, min_length=1, max_length=32)


class LocationResponse(LocationBase):
    """Schema for location response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class LocationInDB(LocationResponse):
    """Schema for location in database"""
    pass
