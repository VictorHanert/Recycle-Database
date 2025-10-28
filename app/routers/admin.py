"""Admin router for administrative operations."""
from math import ceil
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.dependencies import get_admin_user, get_auth_service, get_product_service, get_profile_service
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.product_service import ProductService
from app.services.profile_service import ProfileService
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.schemas.product import ProductListResponse, ProductFilter, ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()

# -- Admin user management (CRUD)
@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(15, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term for username, email, or full name"),
    _admin_user: User = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get all users (admin only)"""
    skip = (page - 1) * size
    
    # Use AuthService search functionality
    if search:
        users = auth_service.search_users(search, skip, size)
        # For total count, we'll get all matching results (could optimize this later)
        all_matching = auth_service.search_users(search, 0, 1000)  # Large limit
        total = len(all_matching)
    else:
        # Use repository get_all method through auth service
        users = auth_service.user_repository.get_all(skip, size)
        total = auth_service.user_repository.count_total_users()
    
    # Calculate total pages
    total_pages = ceil(total / size) if total > 0 else 1
    
    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_admin(
    user_in: UserCreate,
    _admin_user: User = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new user (admin only). Uses AuthService to handle hashing and validation."""
    new_user = auth_service.register_user(user_in)
    return UserResponse.model_validate(new_user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_admin(
    user_id: int,
    _admin_user: User = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    _admin_user: User = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user (admin only)"""
    try:
        updated_user = auth_service.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(updated_user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update user: {str(e)}")


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    _admin_user: User = Depends(get_admin_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Hard delete a user account and all related data (admin only)."""
    profile_service.delete_user_account(user_id)
    return {"message": "User and all related data deleted permanently"}


# -- Admin product management (CRUD)
@router.get("/products", response_model=ProductListResponse)
async def get_all_products_admin(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term for product title or description"),
    include_sold: bool = Query(True, description="Include sold products"),
    _admin_user: User = Depends(get_admin_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Get all products including sold ones (admin only)"""
    skip = (page - 1) * size

    # Get all products for admin (including sold, paused, draft)
    filter_params = ProductFilter(status=None, min_price=None, max_price=None, search_term=search)  # Admin sees all products
    products, total = product_service.get_products(skip=skip, limit=size, filter_params=filter_params)
    total_pages = ceil(total / size) if total > 0 else 1

    return ProductListResponse(
        products=[ProductResponse.model_validate(product) for product in products],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product_admin(
    product_in: ProductCreate,
    _admin_user: User = Depends(get_admin_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Create a product as admin. Admin becomes the owner (seller_id set to admin user's id)."""
    product = product_service.create_product(product_in, _admin_user.id)
    return ProductResponse.model_validate(product)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product_admin(
    product_id: int,
    _admin_user: User = Depends(get_admin_user),
    product_service: ProductService = Depends(get_product_service)
):
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product_admin(
    product_id: int,
    product_update: ProductUpdate,
    admin_user: User = Depends(get_admin_user),
    product_service: ProductService = Depends(get_product_service)
):
    updated = product_service.update_product(product_id, product_update, admin_user.id, is_admin=True)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or update failed")
    return ProductResponse.model_validate(updated)


@router.delete("/products/{product_id}")
async def delete_product_admin(
    product_id: int,
    _admin_user: User = Depends(get_admin_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Delete a product (admin only) - uses repository delete (hard delete)"""
    success = product_service.force_delete_product(product_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return {"message": "Product deleted"}

# -- Other Admin routes
@router.get("/stats")
async def get_platform_stats(
    _admin_user: User = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service),
    product_service: ProductService = Depends(get_product_service)
):
    """Get platform statistics (admin only)"""
    stats = product_service.get_platform_statistics()
    stats["total_users"] = auth_service.user_repository.count_total_users()
    
    return stats

@router.get("/recent-activities")
async def get_recent_activities(
    _admin_user: User = Depends(get_admin_user)
):
    """Get recent activities (admin only)"""
    # TODO: Implement recent activities tracking in services
    recent_activities = []
    return {"recent_activities": recent_activities}
