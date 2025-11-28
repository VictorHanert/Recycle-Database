"""MongoDB Product models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId

from app.models.mongodb.user import PyObjectId


class SellerEmbedded(BaseModel):
    """Embedded seller information."""
    id: str
    username: str
    full_name: str


class CategoryEmbedded(BaseModel):
    """Embedded category information."""
    id: str
    name: str
    parent_name: Optional[str] = None


class ProductImageEmbedded(BaseModel):
    """Embedded product image."""
    url: str
    is_primary: bool = False


class ProductDetailsEmbedded(BaseModel):
    """Embedded product details."""
    colors: List[str] = []
    materials: List[str] = []
    tags: List[str] = []


class ProductStatsEmbedded(BaseModel):
    """Embedded product statistics."""
    view_count: int = 0
    favorite_count: int = 0


class PriceHistoryEntry(BaseModel):
    """Price history entry."""
    amount: float
    currency: str = "DKK"
    changed_at: Optional[datetime] = None


class RecentViewEntry(BaseModel):
    """Recent view entry."""
    viewer_user_id: Optional[str] = None
    viewed_at: Optional[datetime] = None


class ProductMongo(BaseModel):
    """MongoDB Product model with embedded data."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str
    description: Optional[str] = None
    price_amount: float
    price_currency: str = "DKK"
    product_condition: str = "used"
    status: str = "active"
    
    # Embedded seller info (denormalized for performance)
    seller: SellerEmbedded
    
    # Embedded category
    category: Optional[CategoryEmbedded] = None
    
    # Embedded location
    location: Optional[dict] = None
    
    # Embedded details
    details: ProductDetailsEmbedded = Field(default_factory=ProductDetailsEmbedded)
    
    # Embedded images
    images: List[ProductImageEmbedded] = []
    
    # Stats
    stats: ProductStatsEmbedded = Field(default_factory=ProductStatsEmbedded)
    
    # Enhanced fields from migration
    price_history: List[PriceHistoryEntry] = []
    recent_views: List[RecentViewEntry] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProductCreate(BaseModel):
    """Schema for creating products."""
    title: str
    description: Optional[str] = None
    price_amount: float
    price_currency: str = "DKK"
    product_condition: str = "used"
    category_id: Optional[str] = None
    colors: List[str] = []
    materials: List[str] = []
    tags: List[str] = []


class ProductUpdate(BaseModel):
    """Schema for updating products."""
    title: Optional[str] = None
    description: Optional[str] = None
    price_amount: Optional[float] = None
    status: Optional[str] = None
    product_condition: Optional[str] = None


class ProductResponse(BaseModel):
    """Product response model."""
    id: str = Field(alias="_id")
    title: str
    description: Optional[str] = None
    price_amount: float
    price_currency: str
    product_condition: str
    status: str
    seller: SellerEmbedded
    category: Optional[CategoryEmbedded] = None
    details: ProductDetailsEmbedded
    stats: ProductStatsEmbedded
    created_at: datetime
    
    class Config:
        populate_by_name = True
