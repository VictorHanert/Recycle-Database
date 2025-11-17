"""Activity and history related schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ============================================
# VIEW HISTORY SCHEMAS
# ============================================

class ViewHistoryItem(BaseModel):
    """Single viewed product item from GetUserViewHistory stored procedure."""
    model_config = ConfigDict(from_attributes=True)
    
    product_id: int
    title: str
    price_amount: Optional[float]
    price_currency: Optional[str]
    viewed_at: datetime
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    image_url: Optional[str] = None


class ViewHistoryResponse(BaseModel):
    """Response containing user's view history."""
    items: List[ViewHistoryItem]
    total: int


# ============================================
# RECENT ACTIVITY SCHEMAS (Admin Dashboard)
# ============================================

class RecentUserSignup(BaseModel):
    """Recent user signup activity from GetRecentSignups stored procedure."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    username: str
    full_name: Optional[str]
    email: str
    created_at: datetime


class RecentProductCreation(BaseModel):
    """Recent product creation activity from GetRecentProductCreations stored procedure."""
    model_config = ConfigDict(from_attributes=True)
    
    product_id: int
    title: str
    seller_id: int
    seller_username: str
    created_at: datetime


class RecentFavoriteActivity(BaseModel):
    """Recent favorite activity from GetRecentFavorites stored procedure."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    username: str
    product_id: int
    title: str
    favorited_at: datetime


class RecentActivityFeed(BaseModel):
    """Combined recent activity feed for admin dashboard."""
    recent_signups: List[RecentUserSignup]
    recent_products: List[RecentProductCreation]
    recent_favorites: List[RecentFavoriteActivity]


# ============================================
# POPULAR PRODUCTS
# ============================================

class PopularProduct(BaseModel):
    """Popular product from vw_popular_products view."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    price_amount: Optional[float]
    price_currency: Optional[str] = None
    status: str
    favorite_count: int
    view_count: int
    popularity_score: int
    image_url: Optional[str] = None


class PopularProductsResponse(BaseModel):
    """Response containing popular products."""
    products: List[PopularProduct]


# ============================================
# PRODUCT RECOMMENDATIONS
# ============================================

class RecommendedProduct(BaseModel):
    """Recommended product from GetProductRecommendations stored procedure."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    price_amount: Optional[float]
    price_currency: Optional[str] = None
    condition: str
    image_url: Optional[str] = None
    views_count: int
    likes_count: int
    similarity_score: float


class ProductRecommendationsResponse(BaseModel):
    """Response containing recommended products."""
    recommendations: List[RecommendedProduct]
