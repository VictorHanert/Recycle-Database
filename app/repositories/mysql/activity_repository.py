"""MySQL Activity Repository - calls stored procedures for activity/history."""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class MySQLActivityRepository:
    """Repository for activity and history operations using stored procedures."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_view_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's view history using stored procedure.
        Calls: GetUserViewHistory(user_id, limit)
        """
        query = text("CALL GetUserViewHistory(:user_id, :limit)")
        result = self.db.execute(query, {"user_id": user_id, "limit": limit})
        
        # Fetch all rows and convert to dict
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_recent_signups(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent user signups using stored procedure.
        Calls: GetRecentSignups(limit)
        """
        query = text("CALL GetRecentSignups(:limit)")
        result = self.db.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_recent_product_creations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent product creations using stored procedure.
        Calls: GetRecentProductCreations(limit)
        """
        query = text("CALL GetRecentProductCreations(:limit)")
        result = self.db.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_recent_favorites(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent favorites using stored procedure.
        Calls: GetRecentFavorites(limit)
        """
        query = text("CALL GetRecentFavorites(:limit)")
        result = self.db.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_product_recommendations(self, product_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get product recommendations using stored procedure.
        Calls: GetProductRecommendations(product_id, limit)
        """
        query = text("CALL GetProductRecommendations(:product_id, :limit)")
        result = self.db.execute(query, {"product_id": product_id, "limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular products from view.
        Queries: vw_popular_products
        """
        query = text("""
            SELECT id, title, price_amount, price_currency, status, 
                   favorite_count, view_count, popularity_score, image_url
            FROM vw_popular_products
            LIMIT :limit
        """)
        result = self.db.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        columns = result.keys()
        
        return [dict(zip(columns, row)) for row in rows]
