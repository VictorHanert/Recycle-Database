"""Product model for database operations."""
from datetime import datetime, timezone

from sqlalchemy import (Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey,CheckConstraint, Index, Enum)
from sqlalchemy.orm import relationship

from app.db.mysql import Base


# If you use SQLite in dev, consider native_enum=False in Enum(...) to store as VARCHAR
ConditionEnum = Enum("new","like_new","good","fair","needs_repair", name="condition_enum", native_enum=True)
PriceTypeEnum = Enum("fixed","negotiable","auction", name="price_type_enum", native_enum=True)
StatusEnum    = Enum("active","sold","paused","draft", name="status_enum", native_enum=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    condition = Column(ConditionEnum, nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    likes_count = Column(Integer, nullable=False, default=0)
    views_count = Column(Integer, nullable=False, default=0)

    price_amount = Column(Numeric(12, 2), nullable=True)
    price_currency = Column(String(3), nullable=True)
    price_type = Column(PriceTypeEnum, nullable=False, default="fixed")

    status = Column(StatusEnum, nullable=False, default="active", index=True)

    width_cm = Column(Numeric(8, 2), nullable=True)
    height_cm = Column(Numeric(8, 2), nullable=True)
    depth_cm = Column(Numeric(8, 2), nullable=True)
    weight_kg = Column(Numeric(10, 3), nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    is_flagged = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    sold_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    seller = relationship("User", back_populates="products")
    category = relationship("Category")
    location = relationship("Location", back_populates="products")

    images = relationship("ProductImage", back_populates="product",
                          cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    price_changes = relationship("ProductPriceHistory", back_populates="product",
                                 cascade="all, delete-orphan")
    colors = relationship("Color", secondary="product_colors", back_populates="products")
    materials = relationship("Material", secondary="product_materials", back_populates="products")
    tags = relationship("Tag", secondary="product_tags", back_populates="products")
    favorites = relationship("Favorite", back_populates="product", cascade="all, delete-orphan")
    views = relationship("ItemView", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "(price_amount IS NULL AND price_currency IS NULL) OR "
            "(price_amount IS NOT NULL AND price_currency IS NOT NULL)",
            name="ck_price_amount_currency_nullness"
        ),
        CheckConstraint("quantity >= 0", name="ck_quantity_non_negative"),
        Index("ix_products_price_currency_amount", "price_currency", "price_amount"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}', price={self.price_amount}, seller_id={self.seller_id})>"

