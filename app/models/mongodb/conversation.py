"""MongoDB Conversation models - demonstrates nested/embedded documents."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId

from app.models.mongodb.user import PyObjectId


class ParticipantEmbedded(BaseModel):
    """Embedded conversation participant."""
    user_id: str
    username: str


class MessageEmbedded(BaseModel):
    """Embedded message within conversation."""
    sender_id: str
    sender_username: str
    body: str
    is_read: bool = False
    created_at: Optional[datetime] = None


class ConversationMongo(BaseModel):
    """MongoDB Conversation model with embedded messages - demonstrates multi-level nesting."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    legacy_mysql_id: Optional[int] = None
    
    # Participants array
    participants: List[ParticipantEmbedded] = []
    
    # Related product
    product_id: Optional[str] = None
    
    # Embedded messages array (multi-level nesting)
    messages: List[MessageEmbedded] = []
    message_count: int = 0
    
    # Timestamps
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: str = Field(alias="_id")
    participants: List[ParticipantEmbedded]
    product_id: Optional[str] = None
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    
    # Optionally include messages
    messages: Optional[List[MessageEmbedded]] = None
    
    class Config:
        populate_by_name = True
