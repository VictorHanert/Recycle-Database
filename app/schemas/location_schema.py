"""Location schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================
# BASE SCHEMAS
# ============================================

class LocationBase(BaseModel):
    """Base location schema with common fields"""
    city: str = Field(..., min_length=1, max_length=120)
    postcode: str = Field(..., min_length=1, max_length=32)


# ============================================
# REQUEST SCHEMAS (Input)
# ============================================

class LocationCreate(LocationBase):
    """Schema for location creation (locations/ POST endpoint)"""
    pass


class LocationUpdate(BaseModel):
    """Schema for location updates (locations/{id} PUT endpoint)"""
    city: Optional[str] = Field(None, min_length=1, max_length=120)
    postcode: Optional[str] = Field(None, min_length=1, max_length=32)


# ============================================
# RESPONSE SCHEMAS (Output)
# ============================================

class LocationResponse(LocationBase):
    """Standard location response (used in most endpoints)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
