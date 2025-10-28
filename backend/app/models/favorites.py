from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.mysql import Base

class Favorite(Base):
    __tablename__ = "favorites"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorites")

    __table_args__ = (
        Index("ix_favorites_user", "user_id"),
        Index("ix_favorites_product", "product_id"),
    )
