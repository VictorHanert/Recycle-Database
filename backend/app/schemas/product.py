"""Product schemas for request/response validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


# --- Details schemas ---
class ColorInfo(BaseModel):
    """Schema for color information"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class MaterialInfo(BaseModel):
    """Schema for material information"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class TagInfo(BaseModel):
    """Schema for tag information"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SellerInfo(BaseModel):
    """Schema for seller information in products"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str


class LocationInfo(BaseModel):
    """Schema for location information in products"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    city: str
    postcode: str


class ProductDetailsResponse(BaseModel):
    colors: List[ColorInfo]
    materials: List[MaterialInfo]
    tags: List[TagInfo]
    locations: List[LocationInfo] = Field(default_factory=list)


class ProductImageInfo(BaseModel):
    """Schema for product image information"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    url: str
    sort_order: int


class ProductBase(BaseModel):
    """Base product schema with common fields"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price_amount: Decimal = Field(..., gt=0, decimal_places=2)


class ProductCreate(BaseModel):
    """Schema for product creation"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    price_amount: Decimal = Field(..., gt=0, decimal_places=2)
    price_currency: str = Field("DKK", pattern="^[A-Z]{3}$", description="Currency code (e.g., DKK, EUR, USD)")
    category_id: int = Field(..., gt=0)

    # Optional fields
    condition: Optional[str] = Field(None, pattern="^(new|like_new|good|fair|needs_repair)$")
    quantity: Optional[int] = Field(1, ge=1)
    location_id: Optional[int] = Field(None, gt=0)
    width_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    height_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    depth_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    weight_kg: Optional[Decimal] = Field(None, gt=0, decimal_places=3)
    color_ids: Optional[List[int]] = Field(None)
    material_ids: Optional[List[int]] = Field(None)
    tag_ids: Optional[List[int]] = Field(None)
    image_urls: Optional[List[str]] = Field(None)


class ProductUpdate(BaseModel):
    """Schema for product updates"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    price_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$", description="Currency code (e.g., DKK, EUR, USD)")
    category_id: Optional[int] = Field(None, gt=0)

    # Status and condition updates
    status: Optional[str] = Field(None, pattern="^(active|sold|paused|draft)$")
    condition: Optional[str] = Field(None, pattern="^(new|like_new|good|fair|needs_repair)$")

    # Location and dimensions
    location_id: Optional[int] = Field(None, gt=0)
    width_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    height_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    depth_cm: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    weight_kg: Optional[Decimal] = Field(None, gt=0, decimal_places=3)

    # Quantity and details
    quantity: Optional[int] = Field(None, ge=1)

    # Related entities
    color_ids: Optional[List[int]] = Field(None)
    material_ids: Optional[List[int]] = Field(None)
    tag_ids: Optional[List[int]] = Field(None)
    image_urls: Optional[List[str]] = Field(None)


class ProductResponse(BaseModel):
    """Schema for product response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    price_amount: Decimal
    price_currency: Optional[str] = "DKK"
    category_id: int
    condition: str
    quantity: int
    likes_count: int
    status: str
    seller_id: int
    location_id: Optional[int] = None
    sold_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Dimensions and weight
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    depth_cm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    
    # Nested relationships
    seller: Optional[SellerInfo] = None
    location: Optional[LocationInfo] = None
    images: List[ProductImageInfo] = []
    views_count: int = 0
    favorites_count: int = 0
    colors: List[ColorInfo] = []
    materials: List[MaterialInfo] = []
    tags: List[TagInfo] = []
    price_changes: List["PriceHistoryInfo"] = []


class ProductWithSeller(ProductResponse):
    """Schema for product with seller information"""
    seller_username: str
    seller_email: str


# Search and filter schemas
class CategoryInfo(BaseModel):
    """Schema for category information"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class ProductFilter(BaseModel):
    """Schema for product filtering"""
    category: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    location_id: Optional[int] = None
    condition: Optional[str] = None
    sort_by: Optional[str] = "newest"
    status: Optional[str] = None
    search_term: Optional[str] = Field(None, max_length=100)


class ProductListResponse(BaseModel):
    """Schema for paginated product list response"""
    products: list[ProductResponse]
    total: int
    page: int
    size: int
    total_pages: int


class PriceHistoryInfo(BaseModel):
    """Schema for price history information"""
    model_config = ConfigDict(from_attributes=True)

    changed_at: datetime
    amount: Decimal
    currency: str
