from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.mysql import Base

class ProductPriceHistory(Base):
    __tablename__ = "product_price_history"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    changed_at = Column(DateTime, primary_key=True, default=lambda: datetime.now(timezone.utc))
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)

    product = relationship("Product", back_populates="price_changes")

    __table_args__ = (Index("ix_price_hist_product_time", "product_id", "changed_at"),)
