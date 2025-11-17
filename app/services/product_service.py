"""Service class for product operations using the repository pattern."""
from typing import List, Optional, Tuple

from fastapi import HTTPException, status, UploadFile

from app.models.product import Product
from app.schemas.product_schema import ProductCreate, ProductFilter, ProductUpdate, ProductResponse
from app.repositories.base import ProductRepositoryInterface, UserRepositoryInterface
from app.services.file_upload_service import FileUploadService


class ProductService:
    """Service class for product operations using the repository pattern."""
    
    def __init__(
        self, 
        product_repository: ProductRepositoryInterface, 
        user_repository: UserRepositoryInterface,
        file_upload_service: Optional[FileUploadService] = None
    ):
        self.product_repository = product_repository
        self.user_repository = user_repository
        self.file_upload_service = file_upload_service or FileUploadService()

    def get_all_details(self):
        """Fetch all colors, materials, and tags for product details dropdowns/filters."""
        return self.product_repository.get_product_details_options()

    def get_all_categories(self):
        """Get all product categories"""
        return self.product_repository.get_all_categories()

    async def create_product(self, product: ProductCreate, seller_id: int, image_files: Optional[List[UploadFile]] = None) -> Product:
        """Create a new product listing with optional images."""
        saved_image_urls = []
        
        try:
            if image_files:
                saved_image_urls = await self.file_upload_service.validate_and_save_images(image_files)
            
            if saved_image_urls:
                product.image_urls = saved_image_urls
            
            return self.product_repository.create(product, seller_id)
            
        except Exception as e:
            if saved_image_urls:
                await self.file_upload_service.delete_images(saved_image_urls)
            raise

    def get_product_by_id(self, product_id: int, current_user_id: Optional[int] = None) -> Optional[ProductResponse]:
        """Get product by ID with all details and counters."""
        product = self.product_repository.get_by_id(product_id, load_details=True)
        
        if not product:
            return None
        
        if current_user_id != product.seller_id and product.status not in ['active', 'sold']:
            return None
        
        if current_user_id and current_user_id != product.seller_id:
            self.product_repository.record_view(product_id, current_user_id)
            product = self.product_repository.get_by_id(product_id, load_details=True)
        
        product_response = ProductResponse.model_validate(product)
        return product_response

    def get_products(
        self,
        skip: int = 0,
        limit: int = 20,
        filter_params: Optional[ProductFilter] = None
    ) -> Tuple[List[Product], int]:
        """Get products with filtering and pagination"""
        products = self.product_repository.get_all_filtered(
            filters=filter_params,
            skip=skip,
            limit=limit,
            load_details=False
        )
        
        total = self.product_repository.count_filtered(filter_params)
        
        return products, total

    def get_products_by_seller(self, seller_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[Product], int]:
        """Get products by seller with pagination"""
        products = self.product_repository.get_by_seller(seller_id, skip, limit)
        total = self.product_repository.count_by_seller(seller_id)
        return products, total

    def get_products_by_category(self, category: str, skip: int = 0, limit: int = 20) -> Tuple[List[Product], int]:
        """Get products by category with pagination"""
        products = self.product_repository.get_by_category(category, skip, limit)
        # For category filtering, we need to count separately since repository doesn't have this method
        # We'll use get_by_category for both count and data for simplicity
        # In a real implementation, you might add a count_by_category method to the repository
        all_products = self.product_repository.get_by_category(category, skip=0, limit=10000)
        total = len(all_products)
        return products, total

    async def update_product(self, product_id: int, product_update: ProductUpdate, user_id: int, is_admin: bool = False, image_files: Optional[List[UploadFile]] = None) -> Product:
        """Update an existing product with optional new images."""
        product = self.product_repository.get_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        if not is_admin and product.seller_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this product"
            )
        
        saved_image_urls = []
        
        try:
            if image_files:
                saved_image_urls = await self.file_upload_service.validate_and_save_images(image_files)
            
            updated_product, deleted_image_urls = self.product_repository.update(
                product_id, 
                product_update,
                new_image_urls=saved_image_urls
            )
            
            if deleted_image_urls:
                await self.file_upload_service.delete_images(deleted_image_urls)
            
            return updated_product
            
        except Exception as e:
            if saved_image_urls:
                await self.file_upload_service.delete_images(saved_image_urls)
            raise

    async def delete_product(self, product_id: int, user_id: int) -> bool:
        """Delete a product (soft delete, only owner can delete)."""
        product = self.product_repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        if product.seller_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this product"
            )
        
        return self.product_repository.soft_delete(product_id)

    async def force_delete_product(self, product_id: int) -> bool:
        """
        Force delete a product (admin only, hard delete).
        Deletes product and all associated images.
        """
        deleted_image_urls = self.product_repository.delete(product_id)
        
        if deleted_image_urls is None:
            return False
        
        # Clean up image files
        if deleted_image_urls:
            await self.file_upload_service.delete_images(deleted_image_urls)
        
        return True

    def get_platform_statistics(self) -> dict:
        """Get platform statistics"""
        return self.product_repository.get_platform_statistics()

    def search_products(self, query: str, skip: int = 0, limit: int = 20) -> List[Product]:
        """Search products by title or description"""
        return self.product_repository.search_by_title(query, skip, limit)

    def get_recent_products(self, limit: int = 10) -> List[Product]:
        """Get most recently created products"""
        return self.product_repository.get_recent_products(limit)

    def mark_product_as_sold(self, product_id: int, user_id: int, is_admin: bool = False) -> Product:
        """Mark a product as sold"""
        product = self.product_repository.get_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Check if user owns the product (skip for admin)
        if not is_admin and product.seller_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this product"
            )

        # Use update method with status change
        update_data = ProductUpdate.model_validate({"status": "sold"})
        updated_product, _ = self.product_repository.update(product_id, update_data)
        return updated_product

    def get_product_statistics(self) -> dict:
        """Get general product statistics"""
        # This would need additional repository methods to be implemented properly
        # For now, returning a basic structure
        return {
            "total_products": 0,  # Would need count_all method in repository
            "active_products": 0,  # Would need count_by_status method
            "sold_products": 0,
            "recent_products": len(self.get_recent_products())
        }

    def toggle_product_status(self, product_id: int, user_id: int, is_admin: bool = False) -> Product:
        """Toggle product between active and paused status"""
        product = self.product_repository.get_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Check if user owns the product (skip for admin)
        if not is_admin and product.seller_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this product"
            )

        # Toggle between active and paused
        new_status = "paused" if product.status == "active" else "active"
        update_data = ProductUpdate.model_validate({"status": new_status})
        updated_product, _ = self.product_repository.update(product_id, update_data)
        return updated_product
