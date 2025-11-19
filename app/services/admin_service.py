"""Service for admin statistics and analytics."""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.product import Product
from app.models.category import Category
from app.models.user import User


class AdminService:
    """Service for admin-related operations including statistics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get comprehensive platform statistics with trends and distributions."""
        
        # Basic product stats
        total_products = self.db.query(Product).count()
        sold_products = self.db.query(Product).filter(Product.status == "sold").count()
        active_products = self.db.query(Product).filter(Product.status == "active").count()
        
        # Financial stats
        revenue_from_sold_products = self.db.query(func.sum(Product.price_amount)).filter(
            Product.status == "sold"
        ).scalar() or 0
        
        average_price = self.db.query(func.avg(Product.price_amount)).filter(
            Product.status == "active"
        ).scalar() or 0
        
        # Category distribution
        category_stats = self.db.query(
            Category.name,
            func.count(Product.id).label('count')
        ).join(Product, Product.category_id == Category.id).group_by(
            Category.name
        ).order_by(func.count(Product.id).desc()).all()
        
        # Monthly trends for the last 6 months
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        
        # Products created per month
        monthly_products = self.db.query(
            func.date_format(Product.created_at, '%Y-%m').label('month'),
            func.count(Product.id).label('count')
        ).filter(
            Product.created_at >= six_months_ago
        ).group_by('month').order_by('month').all()
        
        # Sales per month with revenue
        monthly_sales = self.db.query(
            func.date_format(Product.updated_at, '%Y-%m').label('month'),
            func.count(Product.id).label('count'),
            func.sum(Product.price_amount).label('revenue')
        ).filter(
            and_(Product.status == "sold", Product.updated_at >= six_months_ago)
        ).group_by('month').order_by('month').all()
        
        return {
            "total_products": total_products,
            "sold_products": sold_products,
            "active_products": active_products,
            "conversion_rate": round((sold_products / total_products * 100) if total_products > 0 else 0, 2),
            "revenue_from_sold_products": float(revenue_from_sold_products),
            "average_price": float(round(average_price, 2)) if average_price else 0,
            "category_distribution": [
                {"category": category_name, "count": count} 
                for category_name, count in category_stats
            ],
            "monthly_trends": {
                "products": [
                    {"month": month, "count": count} 
                    for month, count in monthly_products
                ],
                "sales": [
                    {"month": month, "count": count, "revenue": float(revenue or 0)} 
                    for month, count, revenue in monthly_sales
                ]
            }
        }
