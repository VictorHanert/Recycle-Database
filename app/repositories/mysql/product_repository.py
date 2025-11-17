"""MySQL implementation of the Product Repository."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, desc, asc, or_, func, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.repositories.base import ProductRepositoryInterface
from app.models.product import Product
from app.models.category import Category
from app.models.price_history import ProductPriceHistory
from app.models.product_details import Color, Material, Tag
from app.models.product_details import ProductColor, ProductMaterial, ProductTag
from app.models.product_images import ProductImage
from app.models.item_views import ItemView
from app.models.favorites import Favorite
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductFilter


# Common loading options for different query types
PRODUCT_LIST_LOAD_OPTIONS = [
    joinedload(Product.seller),
    joinedload(Product.location),
    selectinload(Product.images)
]

PRODUCT_DETAIL_LOAD_OPTIONS = [
    joinedload(Product.seller),
    joinedload(Product.location),
    selectinload(Product.images),
    selectinload(Product.colors),
    selectinload(Product.materials),
    selectinload(Product.tags),
    selectinload(Product.favorites),
    selectinload(Product.views),
    selectinload(Product.price_changes),
]


class MySQLProductRepository(ProductRepositoryInterface):
    """MySQL implementation of product repository operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, product_id: int, load_details: bool = False) -> Optional[Product]:
        """Get product by ID with optional detailed relationships."""
        load_options = PRODUCT_DETAIL_LOAD_OPTIONS if load_details else PRODUCT_LIST_LOAD_OPTIONS
        
        return self.db.query(Product).options(*load_options).filter(
            Product.id == product_id,
            Product.deleted_at.is_(None)
        ).first()
    
    def get_all_filtered(
        self, 
        filters: Optional[ProductFilter] = None,
        skip: int = 0, 
        limit: int = 100,
        load_details: bool = False
    ) -> List[Product]:
        """Get filtered products with pagination."""
        load_options = PRODUCT_DETAIL_LOAD_OPTIONS if load_details else PRODUCT_LIST_LOAD_OPTIONS
        query = self.db.query(Product).options(*load_options).filter(Product.deleted_at.is_(None))
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply sorting
        query = self._apply_sorting(query, filters)
        
        products = query.offset(skip).limit(limit).all()
        
        return products
    
    def get_by_seller(self, seller_id: int, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products by seller ID."""
        return self.db.query(Product).options(*PRODUCT_LIST_LOAD_OPTIONS).filter(
            Product.seller_id == seller_id,
            Product.deleted_at.is_(None)
        ).order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
    
    def create(self, product_data: ProductCreate, seller_id: int) -> Product:
        """Create a new product."""
        try:
            db_product = Product(
                title=product_data.title,
                description=product_data.description,
                price_amount=product_data.price_amount,
                price_currency=product_data.price_currency,
                category_id=product_data.category_id,
                condition=product_data.condition or "new",
                quantity=product_data.quantity or 1,
                price_type="fixed",
                status="active",
                location_id=product_data.location_id or 1,  # Default location
                width_cm=product_data.width_cm,
                height_cm=product_data.height_cm,
                depth_cm=product_data.depth_cm,
                weight_kg=product_data.weight_kg,
                seller_id=seller_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(db_product)
            self.db.commit()
            self.db.refresh(db_product)
            
            # Create initial price history entry
            if product_data.price_amount is not None:
                initial_price_history = ProductPriceHistory(
                    product_id=db_product.id,
                    amount=product_data.price_amount,
                    currency=product_data.price_currency
                )
                self.db.add(initial_price_history)
            
            # Handle many-to-many relationships
            self._handle_product_relationships(db_product, product_data)
            
            # Handle images
            if hasattr(product_data, 'image_urls') and product_data.image_urls:
                for i, image_url in enumerate(product_data.image_urls):
                    image = ProductImage(
                        product_id=db_product.id,
                        url=image_url,
                        sort_order=i
                    )
                    self.db.add(image)
            
            self.db.commit()
            self.db.refresh(db_product)
            return db_product
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product creation failed due to database constraint"
            ) from e
    
    def update(self, product_id: int, product_data: ProductUpdate, new_image_urls: Optional[List[str]] = None) -> tuple[Optional[Product], List[str]]:
        """Update product information."""
        product = self.db.query(Product).options(selectinload(Product.images)).filter(
            Product.id == product_id
        ).first()
        
        if not product:
            return None, []
        
        update_data = product_data.model_dump(exclude_unset=True)
        deleted_image_urls = []
        
        # Check if price has changed and create price history entry
        if 'price_amount' in update_data or 'price_currency' in update_data:
            new_amount = update_data.get('price_amount', product.price_amount)
            new_currency = update_data.get('price_currency', product.price_currency)
            
            if new_amount != product.price_amount or new_currency != product.price_currency:
                price_history = ProductPriceHistory(
                    product_id=product_id,
                    amount=new_amount,
                    currency=new_currency
                )
                self.db.add(price_history)
        
        # Handle many-to-many relationships
        self._handle_product_relationships(product, update_data, is_update=True)
        
        # Handle image updates
        keep_image_ids = update_data.pop('keep_image_ids', None)
        update_data.pop('image_urls', None)  # Remove old field if present
        
        if keep_image_ids is not None:
            # Get current images
            current_images = self.db.query(ProductImage).filter(
                ProductImage.product_id == product_id
            ).all()
            
            # Identify images to delete (not in keep list)
            for img in current_images:
                if img.id not in keep_image_ids:
                    deleted_image_urls.append(img.url)
                    self.db.delete(img)
        
        # Add new images
        if new_image_urls:
            # Get current max sort_order
            max_sort_order = 0
            remaining_images = self.db.query(ProductImage).filter(
                ProductImage.product_id == product_id
            ).all()
            
            if remaining_images:
                max_sort_order = max(img.sort_order for img in remaining_images)
            
            for i, image_url in enumerate(new_image_urls):
                new_image = ProductImage(
                    product_id=product_id,
                    url=image_url,
                    sort_order=max_sort_order + i + 1
                )
                self.db.add(new_image)
        
        # Handle status changes
        if 'status' in update_data:
            new_status = update_data['status']
            if new_status == 'sold':
                product.sold_at = datetime.now(timezone.utc)
        
        # Update regular fields
        for field, value in update_data.items():
            if not field.endswith('_ids'):  # Skip relationship fields
                setattr(product, field, value)
        
        product.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            self.db.refresh(product)
            return product, deleted_image_urls
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed due to database constraint"
            ) from e
    
    def delete(self, product_id: int) -> Optional[List[str]]:
        """Hard delete a product and all related data."""
        product = self.db.query(Product).options(selectinload(Product.images)).filter(
            Product.id == product_id
        ).first()
        
        if not product:
            return None
        
        # Collect image URLs for cleanup
        image_urls = [img.url for img in product.images]
        
        try:
            # Delete many-to-many relationships first
            self.db.query(ProductColor).filter(ProductColor.product_id == product_id).delete()
            self.db.query(ProductMaterial).filter(ProductMaterial.product_id == product_id).delete() 
            self.db.query(ProductTag).filter(ProductTag.product_id == product_id).delete()
            self.db.query(Favorite).filter(Favorite.product_id == product_id).delete()
            self.db.delete(product)
            self.db.commit()
            return image_urls
        except Exception:
            self.db.rollback()
            return None

    def soft_delete(self, product_id: int) -> bool:
        """Soft delete a product."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
        
        product.deleted_at = datetime.now(timezone.utc)
        product.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False
    
    def count_filtered(self, filters: Optional[ProductFilter] = None) -> int:
        """Count filtered products."""
        query = self.db.query(Product).filter(Product.deleted_at.is_(None))
        
        if filters:
            query = self._apply_filters(query, filters)
        
        return query.count()
    
    def count_by_seller(self, seller_id: int) -> int:
        """Count products by seller."""
        return self.db.query(Product).filter(
            Product.seller_id == seller_id,
            Product.deleted_at.is_(None)
        ).count()
    
    def search_by_title(self, query: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """Search products by title."""
        search = f"%{query}%"
        return self.db.query(Product).options(*PRODUCT_LIST_LOAD_OPTIONS).filter(
            or_(
                Product.title.ilike(search),
                Product.description.ilike(search)
            ),
            Product.deleted_at.is_(None),
            Product.status == "active"
        ).order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
    
    def get_recent_products(self, limit: int = 10) -> List[Product]:
        """Get most recently created products."""
        return self.db.query(Product).options(*PRODUCT_LIST_LOAD_OPTIONS).filter(
            Product.deleted_at.is_(None),
            Product.status == "active"
        ).order_by(desc(Product.created_at)).limit(limit).all()
    
    def get_product_details_options(self) -> Dict[str, List[Any]]:
        """Get all colors, materials, and tags for filters."""
        colors = self.db.query(Color).order_by(Color.name).all()
        materials = self.db.query(Material).order_by(Material.name).all()
        tags = self.db.query(Tag).order_by(Tag.name).all()
        
        return {
            "colors": colors,
            "materials": materials,
            "tags": tags
        }

    def get_all_categories(self) -> List:
        """Get all product categories."""
        return self.db.query(Category).order_by(Category.name).all()

    def get_platform_statistics(self) -> dict:
        """Get platform statistics for products."""
        
        total_products = self.db.query(Product).count()
        sold_products = self.db.query(Product).filter(Product.status == "sold").count()
        active_products = total_products - sold_products
        revenue_from_sold_products = self.db.query(func.sum(Product.price_amount)).filter(Product.status == "sold").scalar() or 0

        return {
            "total_products": total_products,
            "sold_products": sold_products,
            "active_products": active_products,
            "conversion_rate": round((sold_products / total_products * 100) if total_products > 0 else 0, 2),
            "revenue_from_sold_products": revenue_from_sold_products
        }
    
    def record_view(self, product_id: int, viewer_user_id: int) -> bool:
        """Record a product view and increment views counter."""
        # Check if user already viewed this product
        existing_view = self.db.query(ItemView).filter(
            ItemView.product_id == product_id,
            ItemView.viewer_user_id == viewer_user_id
        ).first()
        
        if existing_view:
            return False  # Already viewed
        
        # Create new view record
        new_view = ItemView(
            product_id=product_id,
            viewer_user_id=viewer_user_id
        )
        
        try:
            self.db.add(new_view)
            # Note: views_count is auto-incremented by database trigger
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False
    
    def get_by_category(self, category: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products by category name."""
        return self.db.query(Product).join(Category, Product.category_id == Category.id).filter(
            and_(
                Category.name.ilike(f"%{category}%"),
                Product.status == "active",
                Product.deleted_at.is_(None)
            )
        ).options(*PRODUCT_LIST_LOAD_OPTIONS).order_by(
            desc(Product.created_at)
        ).offset(skip).limit(limit).all()
    
    def _apply_filters(self, query, filters: ProductFilter):
        """Apply filters to the query."""
        if filters.category:
            query = query.join(Category, Product.category_id == Category.id)
            query = query.filter(Category.name.ilike(f"%{filters.category}%"))
        
        if filters.min_price is not None:
            query = query.filter(Product.price_amount >= filters.min_price)
        
        if filters.max_price is not None:
            query = query.filter(Product.price_amount <= filters.max_price)
        
        if filters.location_id is not None:
            query = query.filter(Product.location_id == filters.location_id)
        
        if filters.condition:
            query = query.filter(Product.condition.ilike(f"%{filters.condition}%"))
        
        if filters.status is not None:
            query = query.filter(Product.status == filters.status)
        
        if filters.search_term:
            # Use MySQL FULLTEXT search with MATCH AGAINST
            # ft_product_search index on (title, description)
            # Supports boolean operators: +required -exclude "exact phrase"
            search_term = filters.search_term.replace("'", "''")  # Escape single quotes
            query = query.filter(
                text(f"MATCH(title, description) AGAINST('{search_term}' IN BOOLEAN MODE)")
            )
        
        return query
    
    def _apply_sorting(self, query, filters: Optional[ProductFilter]):
        """Apply sorting to the query."""
        sort_options = {
            "newest": desc(Product.created_at),
            "oldest": asc(Product.created_at),
            "price_low": asc(Product.price_amount),
            "price_high": desc(Product.price_amount),
            "title": asc(Product.title)
        }
        
        if filters and filters.search_term and filters.sort_by == "relevance":
            search_term = filters.search_term.replace("'", "''")  # Escape single quotes
            return query.order_by(
                text(f"MATCH(title, description) AGAINST('{search_term}' IN NATURAL LANGUAGE MODE) DESC")
            )
        
        if filters and filters.sort_by:
            return query.order_by(sort_options.get(filters.sort_by, desc(Product.created_at)))
        return query.order_by(desc(Product.created_at))
    
    def _handle_product_relationships(self, product: Product, data, is_update: bool = False):
        """Handle many-to-many relationships for colors, materials, and tags."""
        # Handle colors
        if hasattr(data, 'color_ids') or (is_update and 'color_ids' in data):
            color_ids = data.color_ids if hasattr(data, 'color_ids') else data.get('color_ids')
            if is_update:
                product.colors.clear()
            if color_ids:
                colors = self.db.query(Color).filter(Color.id.in_(color_ids)).all()
                product.colors.extend(colors)
        
        # Handle materials
        if hasattr(data, 'material_ids') or (is_update and 'material_ids' in data):
            material_ids = data.material_ids if hasattr(data, 'material_ids') else data.get('material_ids')
            if is_update:
                product.materials.clear()
            if material_ids:
                materials = self.db.query(Material).filter(Material.id.in_(material_ids)).all()
                product.materials.extend(materials)
        
        # Handle tags
        if hasattr(data, 'tag_ids') or (is_update and 'tag_ids' in data):
            tag_ids = data.tag_ids if hasattr(data, 'tag_ids') else data.get('tag_ids')
            if is_update:
                product.tags.clear()
            if tag_ids:
                tags = self.db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
                product.tags.extend(tags)
