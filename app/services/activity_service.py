"""Activity service for handling view history and recent activity using stored procedures and views."""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.mysql.activity_repository import MySQLActivityRepository


class ActivityService:
    """Service for activity-related operations. Delegates to repository layer."""
    
    def __init__(self, db: Session):
        self.db = db
        self.activity_repo = MySQLActivityRepository(db)
    
    # ============================================
    # VIEW HISTORY
    # ============================================
    
    def get_user_view_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's product view history (last viewed products).
        Calls repository which uses stored procedure GetUserViewHistory.
        """
        return self.activity_repo.get_user_view_history(user_id, limit)
    
    # ============================================
    # RECENT ACTIVITY FEED (Admin Dashboard)
    # ============================================
    
    def get_recent_user_signups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently registered users via stored procedure."""
        return self.activity_repo.get_recent_signups(limit)
    
    def get_recent_product_creations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently created products via stored procedure."""
        return self.activity_repo.get_recent_product_creations(limit)
    
    def get_recent_favorites(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently added favorites via stored procedure."""
        return self.activity_repo.get_recent_favorites(limit)
    
    def get_combined_activity_feed(self, limit_each: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get combined recent activity feed for admin dashboard.
        Returns recent signups, products, and favorites.
        """
        return {
            "recent_signups": self.get_recent_user_signups(limit_each),
            "recent_products": self.get_recent_product_creations(limit_each),
            "recent_favorites": self.get_recent_favorites(limit_each)
        }
        
    # ============================================
    # POPULAR PRODUCTS
    # ============================================
    
    def get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular products using the vw_popular_products view.
        This view is created in init_database.sql.
        """
        return self.activity_repo.get_popular_products(limit)
    
    # ============================================
    # PRODUCT RECOMMENDATIONS
    # ============================================
    
    def get_product_recommendations(self, product_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get product recommendations using stored procedure.
        Returns recommended products based on similarity score.
        """
        return self.activity_repo.get_product_recommendations(product_id, limit)
