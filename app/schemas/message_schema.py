from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class ConversationStart(BaseModel):
    product_id: int
    # If omitted, we’ll infer participants later (e.g., creator + product.seller)
    participant_ids: Optional[List[int]] = None
    first_message: str

class MessageCreate(BaseModel):
    conversation_id: int
    body: str

class MessageUpdate(BaseModel):
    body: str

class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    username: Optional[str] = None

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    sender_id: int
    body: Optional[str]
    created_at: datetime
    deleted_at: Optional[datetime] = None

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    participants: List[ParticipantOut]
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0

class ConversationWithMessagesOut(ConversationOut):
    messages: List[MessageOut]
