from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import relationship
from app.db.mysql import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(120), nullable=False)
    postcode = Column(String(32), nullable=False)

    __table_args__ = (
        Index("ix_locations_postcode_city", "postcode", "city"),
    )

    users = relationship("User", back_populates="location")
    products = relationship("Product", back_populates="location")
