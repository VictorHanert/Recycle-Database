"""Products router for product-related operations."""
from math import ceil
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form

from app.db.mysql import get_db
from app.dependencies import (
    get_current_active_user, 
    get_current_user_optional, 
    get_product_service,
    get_repository_factory_dep
)
from app.models.user import User
from app.schemas.product_schema import (
    ProductCreate,
    ProductFilter,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    CategoryInfo,
    ColorInfo,
    MaterialInfo,
    TagInfo,
    LocationInfo,
)
from app.services.product_service import ProductService
from app.schemas.product_schema import ProductDetailsResponse

router = APIRouter()

@router.get("/", response_model=ProductListResponse)
async def get_all_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(15, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    condition: Optional[str] = Query(None, description="Filter by condition"),
    sort: Optional[str] = Query("newest", description="Sort by: newest, oldest, price_low, price_high, title"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    show_sold: bool = Query(False, description="Include sold products"),
    product_service: ProductService = Depends(get_product_service)
):
    """Get all products with filtering and pagination"""
    skip = (page - 1) * size

    # Create filter object
    filter_params = ProductFilter(
        category=category,
        min_price=min_price,
        max_price=max_price,
        location_id=location_id,
        condition=condition,
        sort_by=sort,
        search_term=search,
        status=None if show_sold else "active"
    )

    products, total = product_service.get_products(skip=skip, limit=size, filter_params=filter_params)
    total_pages = ceil(total / size) if total > 0 else 1

    return ProductListResponse(
        products=[ProductResponse.model_validate(product) for product in products],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/my-products", response_model=ProductListResponse)
async def get_my_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Get products posted by the current user"""
    skip = (page - 1) * size
    products, total = product_service.get_products_by_seller(current_user.id, skip=skip, limit=size)
    total_pages = ceil(total / size) if total > 0 else 1

    return ProductListResponse(
        products=[ProductResponse.model_validate(product) for product in products],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/locations", response_model=List[LocationInfo])
async def get_all_locations(repo_factory = Depends(get_repository_factory_dep)):
    """Get all product locations"""
    location_repository = repo_factory.get_location_repository()
    locations = location_repository.get_all(skip=0, limit=1000)  # Get all locations
    return [LocationInfo.model_validate(loc) for loc in locations]

@router.get("/currencies")
async def get_supported_currencies():
    """Get list of supported currencies"""
    currencies = [
        {"code": "DKK", "name": "Danish Krone", "symbol": "kr"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "USD", "name": "US Dollar", "symbol": "$"},
        {"code": "GBP", "name": "British Pound", "symbol": "£"},
        {"code": "SEK", "name": "Swedish Krona", "symbol": "kr"},
        {"code": "NOK", "name": "Norwegian Krone", "symbol": "kr"}
    ]
    return currencies

@router.get("/categories", response_model=List[CategoryInfo])
async def get_all_categories(product_service: ProductService = Depends(get_product_service)):
    """Get all product categories"""
    categories = product_service.get_all_categories()
    return [CategoryInfo.model_validate(cat) for cat in categories]

@router.get("/productdetails", response_model=ProductDetailsResponse)
async def get_all_product_details(
    product_service: ProductService = Depends(get_product_service),
    repo_factory = Depends(get_repository_factory_dep)
):
    """Get all product details including colors, materials, tags, and locations"""
    details = product_service.get_all_details()
    location_repository = repo_factory.get_location_repository()
    locations = location_repository.get_all(skip=0, limit=1000)

    return ProductDetailsResponse(
        colors=[ColorInfo.model_validate(color) for color in details['colors']],
        materials=[MaterialInfo.model_validate(mat) for mat in details['materials']],
        tags=[TagInfo.model_validate(tag) for tag in details['tags']],
        locations=[LocationInfo.model_validate(loc) for loc in locations]
    )

@router.get("/category/{category}", response_model=ProductListResponse)
async def get_products_by_category(
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    product_service: ProductService = Depends(get_product_service)
):
    """Get products by category"""
    skip = (page - 1) * size
    products, total = product_service.get_products_by_category(category, skip=skip, limit=size)
    total_pages = ceil(total / size) if total > 0 else 1

    return ProductListResponse(
        products=[ProductResponse.model_validate(product) for product in products],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int, 
    current_user: Optional[User] = Depends(get_current_user_optional),
    product_service: ProductService = Depends(get_product_service)
):
    """Get a specific product by ID"""
    current_user_id = current_user.id if current_user else None
    product_dict = product_service.get_product_by_id(product_id, current_user_id)
    if not product_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return ProductResponse.model_validate(product_dict)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Create a new product listing with optional images."""
    try:
        product_dict = json.loads(product_data)
        product = ProductCreate.model_validate(product_dict)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in product_data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid product data: {str(e)}"
        )

    # Create product with images (if any)
    db_product = await product_service.create_product(
        product=product,
        seller_id=current_user.id,
        image_files=images if images else None
    )

    return ProductResponse.model_validate(db_product)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Update a product listing with optional new images."""
    try:
        product_dict = json.loads(product_data)
        product_update = ProductUpdate.model_validate(product_dict)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in product_data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid product data: {str(e)}"
        )

    # Update product with optional new images
    db_product = await product_service.update_product(
        product_id=product_id,
        product_update=product_update,
        user_id=current_user.id,
        image_files=images if images else None
    )

    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you don't have permission to update it"
        )

    return ProductResponse.model_validate(db_product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    """Delete a product listing"""
    success = await product_service.delete_product(product_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you don't have permission to delete it"
        )
    return {"message": "Product deleted successfully"}
