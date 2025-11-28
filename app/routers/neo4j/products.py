"""Neo4j Products API Router."""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.neo4j import neo4j_session
from app.repositories.neo4j.product_repository import Neo4jProductRepository
from app.dependencies import get_current_user, get_current_user_optional, AuthenticatedUser

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_product(
    title: str,
    price_amount: float,
    description: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
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
async def get_product(product_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
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
async def favorite_product(product_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
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


@router.put("/{product_id}", response_model=Dict[str, Any])
async def update_product(
    product_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price_amount: Optional[float] = None,
    status: Optional[str] = None,
    condition: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update product in Neo4j.
    Business Logic: Only product owner can update.
    Neo4j Difference: Uses Cypher SET to update node properties.
    Authorization via CREATED relationship traversal.
    """
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        
        # Check if product exists
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Authorization check: verify CREATED relationship (ownership)
        seller_username = await repo.get_seller_username(product_id)
        if seller_username != str(current_user.username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only product owner can update this product"
            )
        
        # Update product
        updated = await repo.update(
            product_id=product_id,
            title=title,
            description=description,
            price_amount=price_amount,
            status=status,
            condition=condition
        )
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update product"
            )
        
        return updated


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Delete product in Neo4j.
    Business Logic: Only product owner can delete.
    Neo4j Difference: Uses DETACH DELETE to remove node and all relationships.
    Authorization via CREATED relationship traversal.
    """
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        
        # Check if product exists
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Authorization check: verify CREATED relationship (ownership)
        seller_username = await repo.get_seller_username(product_id)
        if seller_username != str(current_user.username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only product owner can delete this product"
            )
        
        # Delete product and all relationships
        success = await repo.delete(product_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product"
            )


@router.patch("/{product_id}/mark-sold", response_model=Dict[str, str])
async def mark_product_as_sold(
    product_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Mark product as sold in Neo4j.
    Business Logic: Only product owner can mark as sold.
    Neo4j Difference: Updates status property on Product node.
    Authorization via CREATED relationship traversal.
    """
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        
        # Check if product exists
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Authorization check: verify CREATED relationship (ownership)
        seller_username = await repo.get_seller_username(product_id)
        if seller_username != str(current_user.username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only product owner can mark as sold"
            )
        
        # Mark as sold
        success = await repo.mark_as_sold(product_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark product as sold"
            )
        
        return {"message": "Product marked as sold", "product_id": product_id}


@router.patch("/{product_id}/toggle-status", response_model=Dict[str, str])
async def toggle_product_status(
    product_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Toggle product status between active and paused in Neo4j.
    Business Logic: Only product owner can toggle status.
    Neo4j Difference: Updates status property with conditional logic.
    Authorization via CREATED relationship traversal.
    """
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        
        # Check if product exists
        product = await repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Authorization check: verify CREATED relationship (ownership)
        seller_username = await repo.get_seller_username(product_id)
        if seller_username != str(current_user.username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only product owner can toggle status"
            )
        
        # Toggle status
        new_status = await repo.toggle_status(product_id)
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to toggle product status"
            )
        
        return {"message": f"Product status changed to {new_status}", "new_status": new_status}


@router.post("/{product_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def track_product_view(
    product_id: str,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user)
):
    """
    Track product view in Neo4j.
    Neo4j Difference: Creates VIEWED relationship between User and Product.
    Increments view_count property on Product node.
    For anonymous users, only increments counter without relationship.
    """
    async with neo4j_session() as session:
        repo = Neo4jProductRepository(session)
        
        # Track view (creates VIEWED relationship if user is authenticated)
        viewer_username = str(current_user.username) if current_user else None
        await repo.track_view(product_id, viewer_username)
