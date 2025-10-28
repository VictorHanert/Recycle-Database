"""Repository factory for creating repository instances."""
from sqlalchemy.orm import Session

from app.repositories.base import (
    UserRepositoryInterface, 
    ProductRepositoryInterface, 
    LocationRepositoryInterface
)
from app.repositories.mysql.user_repository import MySQLUserRepository
from app.repositories.mysql.product_repository import MySQLProductRepository
from app.repositories.mysql.location_repository import MySQLLocationRepository


class RepositoryFactory:
    """Factory class for creating repository instances."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_repository(self) -> UserRepositoryInterface:
        """Get user repository instance."""
        return MySQLUserRepository(self.db)
    
    def get_product_repository(self) -> ProductRepositoryInterface:
        """Get product repository instance."""
        return MySQLProductRepository(self.db)
    
    def get_location_repository(self) -> LocationRepositoryInterface:
        """Get location repository instance."""
        return MySQLLocationRepository(self.db)


# Convenience function for dependency injection
def get_repository_factory(db: Session) -> RepositoryFactory:
    """Get repository factory instance for dependency injection."""
    return RepositoryFactory(db)
