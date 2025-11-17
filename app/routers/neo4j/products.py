"""Neo4j Products API Router."""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.neo4j import neo4j_session
from app.repositories.neo4j.product_repository import Neo4jProductRepository
from app.dependencies import get_current_user
from app.models.user import User as MySQLUser

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_product(
    title: str,
    price_amount: float,
    description: Optional[str] = None,
    current_user: MySQLUser = Depends(get_current_user)
):
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        product = await repo.create(title=title, description=description, price_amount=price_amount, seller_username=str(current_user.username))
        return product


@router.get("", response_model=List[Dict[str, Any]])
async def list_products(skip: int = 0, limit: int = 50, status_filter: Optional[str] = None):
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        return await repo.list(skip=skip, limit=limit, status=status_filter)


@router.get("/popular", response_model=List[Dict[str, Any]])
async def popular_products(limit: int = 10):
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        return await repo.popular(limit=limit)


@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product(product_id: str, current_user: MySQLUser = Depends(get_current_user)):
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        # Record a view
        await repo.add_view(username=str(current_user.username), product_id=product_id)
        # Return updated product
        return await repo.get_by_id(product_id)


@router.post("/{product_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def favorite_product(product_id: str, current_user: MySQLUser = Depends(get_current_user)):
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        ok = await repo.add_favorite(username=str(current_user.username), product_id=product_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to favorite product")
        return None


@router.get("/{product_id}/recommendations", response_model=List[Dict[str, Any]])
async def recommend_products(product_id: str, limit: int = 10):
    """Get recommended products based on shared user interactions (favorites/views)."""
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        # Verify product exists first
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return await repo.recommendations(product_id=product_id, limit=limit)
