"""MongoDB Products API Router."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_mongodb
from app.repositories.mongodb.product_repository import MongoDBProductRepository
from app.repositories.mongodb.user_repository import MongoDBUserRepository
from app.models.mongodb.product import ProductCreate, ProductUpdate, ProductResponse
from app.dependencies import get_current_user
from app.models.user import User as MySQLUser


router = APIRouter()


def get_product_repository(db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> MongoDBProductRepository:
    """Dependency to get product repository."""
    return MongoDBProductRepository(db)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: MySQLUser = Depends(get_current_user),
    repo: MongoDBProductRepository = Depends(get_product_repository),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Create a new product in MongoDB."""
    # Find MongoDB user by username from MySQL user
    user_repo = MongoDBUserRepository(db)
    mongo_user = await user_repo.get_by_username(str(current_user.username))
    
    if not mongo_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found in MongoDB. Please create a MongoDB user first."
        )
    
    seller_id = str(mongo_user.id)
    
    try:
        return await repo.create(product_data, seller_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    seller_id: Optional[str] = None,
    category_id: Optional[str] = None,
    repo: MongoDBProductRepository = Depends(get_product_repository)
):
    """Get all products from MongoDB with filters."""
    return await repo.get_all(
        skip=skip,
        limit=limit,
        status=status,
        seller_id=seller_id,
        category_id=category_id
    )


@router.get("/search", response_model=List[ProductResponse])
async def search_products(
    q: str = Query(..., description="Search query"),
    skip: int = 0,
    limit: int = 100,
    repo: MongoDBProductRepository = Depends(get_product_repository)
):
    """Full-text search products in MongoDB."""
    return await repo.search(q, skip=skip, limit=limit)


@router.get("/filter", response_model=List[ProductResponse])
async def filter_products(
    text: Optional[str] = Query(None, description="Text search in title/description"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    status: Optional[str] = Query(None),
    seller_username: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Advanced filtered search combining text, price range, status, seller, and tag."""
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if min_price is not None or max_price is not None:
        price_cond: Dict[str, Any] = {}
        if min_price is not None:
            price_cond["$gte"] = min_price
        if max_price is not None:
            price_cond["$lte"] = max_price
        query["price_amount"] = price_cond
    if seller_username:
        query["seller.username"] = seller_username
    if tag:
        query["details.tags"] = tag

    # Text search uses $text; combine carefully
    if text:
        query["$text"] = {"$search": text}

    cursor = db.products.find(query).sort("created_at", -1).skip(skip).limit(limit)
    results = []
    async for doc in cursor:
        # Map to ProductResponse manually (subset) - rely on Pydantic population by name
        doc["_id"] = str(doc.get("_id"))
        results.append(ProductResponse.model_validate(doc))
    return results


@router.get("/top-categories", response_model=List[Dict[str, Any]])
async def top_categories(limit: int = 5, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Aggregation: Top categories by active product count."""
    pipeline = [
        {"$match": {"status": "active", "category.name": {"$ne": None}}},
        {"$group": {"_id": "$category.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    cursor = db.products.aggregate(pipeline)
    results = await cursor.to_list(length=limit)
    return [{"category": doc["_id"], "count": doc["count"]} for doc in results]


@router.get("/popular", response_model=List[ProductResponse])
async def get_popular_products(
    limit: int = 10,
    repo: MongoDBProductRepository = Depends(get_product_repository)
):
    """Get popular products by view count."""
    return await repo.get_popular(limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    repo: MongoDBProductRepository = Depends(get_product_repository)
):
    """Get product by ID from MongoDB."""
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Increment view count
    await repo.increment_view_count(product_id)
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    update_data: ProductUpdate,
    current_user: MySQLUser = Depends(get_current_user),
    repo: MongoDBProductRepository = Depends(get_product_repository),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Update product in MongoDB."""
    # Find MongoDB user by username from MySQL user
    user_repo = MongoDBUserRepository(db)
    mongo_user = await user_repo.get_by_username(str(current_user.username))
    
    if not mongo_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found in MongoDB"
        )
    
    # Check if product exists and user owns it
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check ownership (or admin)
    if product.seller.id != str(mongo_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this product"
        )
    
    updated_product = await repo.update(product_id, update_data)
    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: MySQLUser = Depends(get_current_user),
    repo: MongoDBProductRepository = Depends(get_product_repository),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Delete product from MongoDB."""
    # Find MongoDB user by username from MySQL user
    user_repo = MongoDBUserRepository(db)
    mongo_user = await user_repo.get_by_username(str(current_user.username))
    
    if not mongo_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found in MongoDB"
        )
    
    # Check if product exists and user owns it
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check ownership (or admin)
    if product.seller.id != str(mongo_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this product"
        )
    
    await repo.delete(product_id)
