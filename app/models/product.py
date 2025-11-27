"""Product model for database operations."""
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    Enum,
    Integer,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped

from app.db.mysql import Base

# If you use SQLite in dev, consider native_enum=False in Enum(...) to store as VARCHAR
ConditionEnum = Enum(
    "new", "like_new", "good", "fair", "needs_repair",
    name="condition_enum",
    native_enum=True,
)
PriceTypeEnum = Enum(
    "fixed", "negotiable", "auction",
    name="price_type_enum",
    native_enum=True,
)
StatusEnum = Enum(
    "active", "sold", "paused", "draft",
    name="status_enum",
    native_enum=True,
)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(ConditionEnum, nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    price_type: Mapped[str] = mapped_column(PriceTypeEnum, nullable=False, default="fixed")

    status: Mapped[str] = mapped_column(StatusEnum, nullable=False, default="active", index=True)

    width_cm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    depth_cm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    seller = relationship("User", back_populates="products")
    category = relationship("Category")
    location = relationship("Location", back_populates="products")

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    price_changes = relationship(
        "ProductPriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    colors = relationship("Color", secondary="product_colors", back_populates="products")
    materials = relationship("Material", secondary="product_materials", back_populates="products")
    tags = relationship("Tag", secondary="product_tags", back_populates="products")
    favorites = relationship("Favorite", back_populates="product", cascade="all, delete-orphan")
    views = relationship("ItemView", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "(price_amount IS NULL AND price_currency IS NULL) OR "
            "(price_amount IS NOT NULL AND price_currency IS NOT NULL)",
            name="ck_price_amount_currency_nullness",
        ),
        CheckConstraint("quantity >= 0", name="ck_quantity_non_negative"),
        Index("ix_products_price_currency_amount", "price_currency", "price_amount"),
    )

    def __repr__(self) -> str:
        return (
            f"<Product(id={self.id}, title='{self.title}', "
            f"price={self.price_amount}, seller_id={self.seller_id})>"
        )