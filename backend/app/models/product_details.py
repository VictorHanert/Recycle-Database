from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.mysql import Base

class Color(Base):
    __tablename__ = "colors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), unique=True, nullable=False)
    products = relationship("Product", secondary="product_colors", back_populates="colors")

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", secondary="product_materials", back_populates="materials")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", secondary="product_tags", back_populates="tags")

class ProductColor(Base):
    __tablename__ = "product_colors"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    color_id = Column(Integer, ForeignKey("colors.id", ondelete="RESTRICT"), primary_key=True)
    __table_args__ = (Index("ix_product_colors_color", "color_id"),)

class ProductMaterial(Base):
    __tablename__ = "product_materials"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="RESTRICT"), primary_key=True)
    __table_args__ = (Index("ix_product_materials_material", "material_id"),)

class ProductTag(Base):
    __tablename__ = "product_tags"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True)
    __table_args__ = (Index("ix_product_tags_tag", "tag_id"),)
