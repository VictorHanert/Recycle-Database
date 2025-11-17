"""Activity router for view history and recent activity endpoints."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.services.activity_service import ActivityService
from app.schemas.activity_schema import (
    ViewHistoryResponse,
    ViewHistoryItem,
    RecentActivityFeed,
    RecentUserSignup,
    RecentProductCreation,
    RecentFavoriteActivity,
    PopularProductsResponse,
    PopularProduct,
    ProductRecommendationsResponse,
    RecommendedProduct
)

router = APIRouter()


# ============================================
# USER VIEW HISTORY
# ============================================

@router.get("/history/views", response_model=ViewHistoryResponse)
async def get_my_view_history(
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's product view history.
    Returns the last viewed products ordered by most recent first.
    """
    activity_service = ActivityService(db)
    history_data = activity_service.get_user_view_history(current_user.id, limit)
    
    items = [ViewHistoryItem(**item) for item in history_data]
    
    return ViewHistoryResponse(
        items=items,
        total=len(items)
    )

# ============================================
# ADMIN RECENT ACTIVITY FEED
# ============================================

@router.get("/admin/recent-activity", response_model=RecentActivityFeed)
async def get_recent_activity_feed(
    limit: int = Query(5, ge=1, le=20, description="Number of items per category"),
    _admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get recent activity feed for admin dashboard (admin only).
    Returns recent user signups, product creations, and favorites.
    """
    activity_service = ActivityService(db)
    activity_data = activity_service.get_combined_activity_feed(limit)
    
    return RecentActivityFeed(
        recent_signups=[RecentUserSignup(**item) for item in activity_data["recent_signups"]],
        recent_products=[RecentProductCreation(**item) for item in activity_data["recent_products"]],
        recent_favorites=[RecentFavoriteActivity(**item) for item in activity_data["recent_favorites"]]
    )

# ============================================
# POPULAR PRODUCTS
# ============================================

@router.get("/popular-products", response_model=PopularProductsResponse)
async def get_popular_products(
    limit: int = Query(10, ge=1, le=50, description="Number of products to return"),
    db: Session = Depends(get_db)
):
    """
    Get popular products using the vw_popular_products view.
    Products are ranked by a popularity score based on favorites and views.
    """
    activity_service = ActivityService(db)
    products_data = activity_service.get_popular_products(limit)
    
    products = [PopularProduct(**product) for product in products_data]
    
    return PopularProductsResponse(products=products)

# ============================================
# PRODUCT RECOMMENDATIONS
# ============================================

@router.get("/products/{product_id}/recommendations", response_model=ProductRecommendationsResponse)
async def get_product_recommendations(
    product_id: int,
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations to return"),
    db: Session = Depends(get_db)
):
    """
    Get product recommendations using stored procedure.
    Calls GetProductRecommendations stored procedure.
    Returns similar products based on category, price range, and condition.
    """
    activity_service = ActivityService(db)
    recommendations_data = activity_service.get_product_recommendations(product_id, limit)
    
    recommendations = [RecommendedProduct(**item) for item in recommendations_data]
    
    return ProductRecommendationsResponse(recommendations=recommendations)
    
    return {"product_id": product_id, "age_days": age_days}
