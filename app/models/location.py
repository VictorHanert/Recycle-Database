from sqlalchemy import Integer, String, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.mysql import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    postcode: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        Index("ix_locations_postcode_city", "postcode", "city"),
    )

    users = relationship("User", back_populates="location")
    products = relationship("Product", back_populates="location")