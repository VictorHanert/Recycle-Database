"""Abstract base repository classes for the repository pattern."""
from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.product import Product
from app.models.location import Location
from app.schemas.user_schema import UserCreate, UserUpdate
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductFilter

# Type variables for generic repository
T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """Abstract base repository providing common CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        pass
    
    @abstractmethod
    def create(self, entity_data: dict) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def update(self, entity_id: int, entity_data: dict) -> Optional[T]:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        pass


class UserRepositoryInterface(ABC):
    """Abstract interface for user repository operations."""
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with location relationship loaded."""
        pass
    
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username with location relationship loaded."""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass
    
    @abstractmethod
    def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        pass
    
    @abstractmethod
    def check_username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        pass
    
    @abstractmethod
    def check_email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[User]:
        """Get all users with pagination and optional filtering."""
        pass

    @abstractmethod
    def search_users(self, search_term: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, or full name."""
        pass

    @abstractmethod
    def count_total_users(self) -> int:
        """Get total count of users."""
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete user by ID."""
        pass


class ProductRepositoryInterface(ABC):
    """Abstract interface for product repository operations."""
    
    @abstractmethod
    def get_by_id(self, product_id: int, load_details: bool = False) -> Optional[Product]:
        """Get product by ID with optional detailed relationships."""
        pass
    
    @abstractmethod
    def get_all_filtered(
        self, 
        filters: Optional[ProductFilter] = None,
        skip: int = 0, 
        limit: int = 100,
        load_details: bool = False
    ) -> List[Product]:
        """Get filtered products with pagination."""
        pass
    
    @abstractmethod
    def get_by_seller(self, seller_id: int, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products by seller ID."""
        pass
    
    @abstractmethod
    def create(self, product_data: ProductCreate, seller_id: int) -> Product:
        """Create a new product."""
        pass
    
    @abstractmethod
    def update(self, product_id: int, product_data: ProductUpdate, new_image_urls: Optional[List[str]] = None) -> tuple[Optional[Product], List[str]]:
        """Update product information."""
        pass
    
    @abstractmethod
    def soft_delete(self, product_id: int) -> bool:
        """Soft delete a product."""
        pass

    @abstractmethod
    def delete(self, product_id: int) -> Optional[List[str]]:
        """Hard delete a product and all related data."""
        pass

    @abstractmethod
    def get_platform_statistics(self) -> dict:
        """Get platform statistics for products."""
        pass
    
    @abstractmethod
    def count_filtered(self, filters: Optional[ProductFilter] = None) -> int:
        """Count filtered products."""
        pass
    
    @abstractmethod
    def count_by_seller(self, seller_id: int) -> int:
        """Count products by seller."""
        pass
    
    @abstractmethod
    def search_by_title(self, query: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """Search products by title."""
        pass
    
    @abstractmethod
    def get_recent_products(self, limit: int = 10) -> List[Product]:
        """Get most recently created products."""
        pass
    
    @abstractmethod
    def get_product_details_options(self) -> dict:
        """Get all colors, materials, and tags for dropdowns/filters."""
        pass

    @abstractmethod
    def get_all_categories(self) -> List:
        """Get all product categories."""
        pass
    
    @abstractmethod
    def record_view(self, product_id: int, viewer_user_id: int) -> bool:
        """Record a product view."""
        pass
    
    @abstractmethod
    def get_by_category(self, category: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products by category name."""
        pass


class LocationRepositoryInterface(ABC):
    """Abstract interface for location repository operations."""
    
    @abstractmethod
    def get_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Location]:
        """Get all locations with pagination."""
        pass
    
    @abstractmethod
    def get_by_city_and_postcode(self, city: str, postcode: str) -> Optional[Location]:
        """Get location by city and postcode."""
        pass
    
    @abstractmethod
    def create(self, city: str, postcode: str) -> Location:
        """Create a new location."""
        pass
    
    @abstractmethod
    def get_or_create(self, city: str, postcode: str) -> Location:
        """Get existing location or create new one."""
        pass
    
    @abstractmethod
    def search_by_city(self, city: str, limit: int = 10) -> List[Location]:
        """Search locations by city name."""
        pass

    @abstractmethod
    def search_locations(self, query: str, limit: int = 10) -> List[Location]:
        """Search locations by city or postcode."""
        pass

    @abstractmethod
    def update(self, location_id: int, city: Optional[str] = None, postcode: Optional[str] = None) -> Optional[Location]:
        """Update location information."""
        pass

    @abstractmethod
    def delete(self, location_id: int) -> bool:
        """Delete a location."""
        pass
    
    @abstractmethod
    def count_total_locations(self) -> int:
        """Count total number of locations."""
        pass
