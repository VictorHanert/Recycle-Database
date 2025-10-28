from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.mysql import Base


class SoldItemArchive(Base):
    """
    Immutable snapshot of a sale at the time it happened.
    Keeps history even if the Product later changes or is deleted.
    """
    __tablename__ = "sold_item_archive"

    id = Column(Integer, primary_key=True, index=True)           # sale id
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)

    price_amount = Column(Numeric(12, 2), nullable=True)
    price_currency = Column(String(3), nullable=True)

    sold_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    buyer = relationship("User")
    category = relationship("Category")
    location = relationship("Location")
