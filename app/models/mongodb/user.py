"""MongoDB models using Pydantic."""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Annotated
from datetime import datetime, timezone
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic v2."""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        
        return core_schema.with_info_before_validator_function(
            cls.validate,
            core_schema.str_schema(),
        )

    @classmethod
    def validate(cls, v, _info):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId")
        raise ValueError("Invalid ObjectId type")



class LocationEmbedded(BaseModel):
    """Embedded location in user document."""
    city: str
    postcode: str
    country: Optional[str] = "Denmark"


class UserMongo(BaseModel):
    """MongoDB User model with embedded data."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: EmailStr
    hashed_password: str
    full_name: str
    phone: Optional[str] = None
    location: Optional[LocationEmbedded] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Denormalized stats
    product_count: int = 0
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserCreate(BaseModel):
    """Schema for creating users."""
    username: str
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    id: str = Field(alias="_id")
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    location: Optional[LocationEmbedded] = None
    is_active: bool
    is_admin: bool
    product_count: int = 0
    created_at: datetime
    
    class Config:
        populate_by_name = True
