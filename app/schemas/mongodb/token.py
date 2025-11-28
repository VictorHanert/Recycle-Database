from pydantic import BaseModel
from typing import Optional
from app.models.mongodb.user import UserResponse as MongoUserResponse


class TokenMongo(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: MongoUserResponse
