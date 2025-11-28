"""Neo4j Users API Router."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.neo4j import neo4j_session
from app.repositories.neo4j.user_repository import Neo4jUserRepository
from app.dependencies import get_admin_user

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_user(username: str, email: str | None = None, full_name: str | None = None):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        user = await repo.create(username=username, email=email, full_name=full_name)
        # Remove sensitive fields
        user.pop("hashed_password", None)
        return user


@router.get("", response_model=List[Dict[str, Any]])
async def list_users(skip: int = 0, limit: int = 50):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        users = await repo.list_users(skip=skip, limit=limit)
        # Remove sensitive fields from all users
        for user in users:
            user.pop("hashed_password", None)
        return users


@router.get("/{username}", response_model=Dict[str, Any])
async def get_user(username: str):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        user = await repo.get_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        # Remove sensitive fields
        user.pop("hashed_password", None)
        return user


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(username: str, admin = Depends(get_admin_user)):
    """Delete a Neo4j user (admin only)."""
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        # Ensure user exists first
        user = await repo.get_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        success = await repo.delete(username)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete user")
