"""Neo4j-backed Authentication Router (register/login with JWT)."""
from datetime import timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, EmailStr

from app.db.neo4j import neo4j_session
from app.repositories.neo4j.user_repository import Neo4jUserRepository
from app.auth import AuthService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class Neo4jUserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class LoginRequest(BaseModel):
    identifier: str
    password: str


class TokenNeo4j(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


@router.post("/register", response_model=TokenNeo4j, status_code=status.HTTP_201_CREATED)
async def register_user(user: Neo4jUserCreate):
    """Register a Neo4j user and issue a JWT."""
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        
        # Check if username exists
        existing = await repo.get_by_username(user.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Hash password and create user
        hashed_password = AuthService.get_password_hash(user.password)
        
        query = """
        CREATE (u:User {
            username: $username,
            email: $email,
            full_name: $full_name,
            hashed_password: $hashed_password,
            is_active: true,
            is_admin: false
        })
        RETURN u
        """
        result = await session.run(
            query,
            username=user.username,
            email=user.email,
            full_name=user.full_name or user.username,
            hashed_password=hashed_password
        )
        record = await result.single()
        created_user = record["u"]._properties if record else {}
        
        # Remove password from response
        created_user.pop("hashed_password", None)
        
        access_token_expires = timedelta(minutes=30000)
        access_token = AuthService.create_access_token(
            data={"sub": created_user["username"]},
            expires_delta=access_token_expires
        )
        
        return TokenNeo4j(
            access_token=access_token,
            expires_in=30000 * 60,
            user=created_user,
        )


@router.post("/login", response_model=TokenNeo4j)
@limiter.limit("5/minute")
async def login_user(request: Request, payload: LoginRequest):
    """Login by username or email against Neo4j and issue JWT."""
    async with neo4j_session() as session:
        repo = Neo4jUserRepository(session)
        
        # Fetch user by username or email
        query = """
        MATCH (u:User)
        WHERE u.username = $identifier OR u.email = $identifier
        RETURN u
        """
        result = await session.run(query, identifier=payload.identifier)
        record = await result.single()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password"
            )
        
        user = record["u"]._properties
        
        # Verify password
        if not AuthService.verify_password(payload.password, user.get("hashed_password", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(status_code=400, detail="Inactive user account")
        
        # Remove password from response
        user_response = {k: v for k, v in user.items() if k != "hashed_password"}
        
        access_token_expires = timedelta(minutes=30000)
        access_token = AuthService.create_access_token(
            data={"sub": user["username"]},
            expires_delta=access_token_expires
        )
        
        return TokenNeo4j(
            access_token=access_token,
            expires_in=30000 * 60,
            user=user_response,
        )
