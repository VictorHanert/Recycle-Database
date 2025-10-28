from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.mysql import Base

class ItemView(Base):
    __tablename__ = "item_views"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    viewer_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)  # null for anonymous views
    viewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session_id = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    referer = Column(String(255), nullable=True)

    product = relationship("Product", back_populates="views")
    viewer = relationship("User")

    __table_args__ = (Index("ix_item_views_product_time", "product_id", "viewed_at"),)
