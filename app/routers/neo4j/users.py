"""Neo4j Users API Router."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.neo4j import neo4j_session
from app.repositories.neo4j.user_repository import Neo4jUserRepository

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_user(username: str, email: str | None = None, full_name: str | None = None):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        user = await repo.create(username=username, email=email, full_name=full_name)
        return user


@router.get("", response_model=List[Dict[str, Any]])
async def list_users(skip: int = 0, limit: int = 50):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        return await repo.list_users(skip=skip, limit=limit)


@router.get("/{username}", response_model=Dict[str, Any])
async def get_user(username: str):
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        user = await repo.get_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
