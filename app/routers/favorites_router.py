"""Favorites router for managing user's favorite products."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.favorites import Favorite
from app.models.product import Product
from app.schemas.product_schema import ProductResponse

router = APIRouter()


@router.post("/{product_id}", status_code=status.HTTP_201_CREATED)
def add_favorite(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a product to user's favorites."""
    
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if already favorited
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already in favorites"
        )
    
    # Add to favorites
    favorite = Favorite(user_id=current_user.id, product_id=product_id)
    db.add(favorite)
    db.commit()
    
    return {"message": "Product added to favorites", "product_id": product_id}


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def remove_favorite(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from user's favorites."""
    
    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not in favorites"
        )
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Product removed from favorites", "product_id": product_id}


@router.get("/{product_id}/status", status_code=status.HTTP_200_OK)
def check_favorite_status(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if a product is in user's favorites."""
    
    is_favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first() is not None
    
    return {"is_favorite": is_favorite, "product_id": product_id}


@router.get("/", response_model=List[ProductResponse])
def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products in user's favorites."""
    
    favorites = db.query(Product).join(
        Favorite, Favorite.product_id == Product.id
    ).filter(
        Favorite.user_id == current_user.id,
        Product.deleted_at.is_(None)
    ).all()
    
    return favorites
