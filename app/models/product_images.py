from datetime import datetime, timezone

from sqlalchemy import Integer, String, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.mysql import Base


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    product = relationship("Product", back_populates="images")

    __table_args__ = (
        Index("ix_product_images_product_sort", "product_id", "sort_order"),
    )