"""MongoDB Product Repository."""
from typing import Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.mongodb.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    SellerEmbedded,
    CategoryEmbedded
)


class MongoDBProductRepository:
    """MongoDB implementation of product repository."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.products
        self.users_collection = db.users
        self.categories_collection = db.categories
    
    async def create(self, product_data: ProductCreate, seller_id: str) -> ProductResponse:
        """Create a new product with embedded seller and category data."""
        if not ObjectId.is_valid(seller_id):
            raise ValueError("Invalid seller ID")
        
        # Get seller info for embedding
        seller = await self.users_collection.find_one({"_id": ObjectId(seller_id)})
        if not seller:
            raise ValueError("Seller not found")
        
        seller_embedded = SellerEmbedded(
            id=str(seller["_id"]),
            username=seller["username"],
            full_name=seller.get("full_name")
        )
        
        # Get category info for embedding
        category_embedded = None
        if product_data.category_id:
            category = await self.categories_collection.find_one({"_id": ObjectId(product_data.category_id)})
            if category:
                category_embedded = CategoryEmbedded(
                    id=str(category["_id"]),
                    name=category["name"],
                    parent_name=category.get("parent_name")
                )
        
        product_dict = {
            "title": product_data.title,
            "description": product_data.description,
            "price_amount": product_data.price_amount,
            "price_currency": product_data.price_currency,
            "product_condition": product_data.product_condition,
            "status": "active",
            "seller": seller_embedded.model_dump(),
            "category": category_embedded.model_dump() if category_embedded else None,
            "images": [],
            "details": {
                "colors": product_data.colors,
                "materials": product_data.materials,
                "tags": product_data.tags
            },
            "stats": {
                "view_count": 0,
                "favorite_count": 0
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await self.collection.insert_one(product_dict)
        product_dict["_id"] = str(result.inserted_id)
        
        # Increment seller's product count
        await self.users_collection.update_one(
            {"_id": ObjectId(seller_id)},
            {"$inc": {"product_count": 1}}
        )
        
        return ProductResponse(**product_dict)
    
    async def get_by_id(self, product_id: str) -> Optional[ProductResponse]:
        """Get product by ID."""
        if not ObjectId.is_valid(product_id):
            return None
        
        product = await self.collection.find_one({"_id": ObjectId(product_id)})
        if product:
            product["_id"] = str(product["_id"])
            return ProductResponse(**product)
        return None
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        seller_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> List[ProductResponse]:
        """Get all products with filters and pagination."""
        query = {}
        
        if status:
            query["status"] = status
        
        if seller_id:
            query["seller.id"] = seller_id
        
        if category_id:
            query["category.id"] = category_id
        
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        
        products = []
        async for product in cursor:
            product["_id"] = str(product["_id"])
            products.append(ProductResponse(**product))
        return products
    
    async def search(self, search_text: str, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Full-text search products."""
        cursor = self.collection.find(
            {"$text": {"$search": search_text}}
        ).skip(skip).limit(limit)
        
        products = []
        async for product in cursor:
            product["_id"] = str(product["_id"])
            products.append(ProductResponse(**product))
        return products
    
    async def update(self, product_id: str, update_data: ProductUpdate) -> Optional[ProductResponse]:
        """Update product."""
        if not ObjectId.is_valid(product_id):
            return None
        
        # Build update dict, excluding None values
        update_dict = {}
        if update_data.title is not None:
            update_dict["title"] = update_data.title
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.price_amount is not None:
            update_dict["price_amount"] = update_data.price_amount
        if update_data.status is not None:
            update_dict["status"] = update_data.status
        if update_data.product_condition is not None:
            update_dict["product_condition"] = update_data.product_condition
        
        if not update_dict:
            return await self.get_by_id(product_id)
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(product_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return ProductResponse(**result)
        return None
    
    async def delete(self, product_id: str) -> bool:
        """Delete product."""
        if not ObjectId.is_valid(product_id):
            return False
        
        # Get product to decrement seller's count
        product = await self.collection.find_one({"_id": ObjectId(product_id)})
        
        result = await self.collection.delete_one({"_id": ObjectId(product_id)})
        
        # Decrement seller's product count
        if result.deleted_count > 0 and product:
            seller_id = product["seller"]["id"]
            await self.users_collection.update_one(
                {"_id": ObjectId(seller_id)},
                {"$inc": {"product_count": -1}}
            )
        
        return result.deleted_count > 0
    
    async def increment_view_count(self, product_id: str):
        """Increment product view count."""
        if ObjectId.is_valid(product_id):
            await self.collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"stats.view_count": 1}}
            )
    
    async def increment_favorite_count(self, product_id: str):
        """Increment product favorite count."""
        if ObjectId.is_valid(product_id):
            await self.collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"stats.favorite_count": 1}}
            )
    
    async def decrement_favorite_count(self, product_id: str):
        """Decrement product favorite count."""
        if ObjectId.is_valid(product_id):
            await self.collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"stats.favorite_count": -1}}
            )
    
    async def get_by_seller(self, seller_id: str, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Get all products by seller."""
        return await self.get_all(skip=skip, limit=limit, seller_id=seller_id)
    
    async def get_popular(self, limit: int = 10) -> List[ProductResponse]:
        """Get popular products by view count."""
        cursor = self.collection.find({"status": "active"}).sort("stats.view_count", -1).limit(limit)
        
        products = []
        async for product in cursor:
            product["_id"] = str(product["_id"])
            products.append(ProductResponse(**product))
        return products
