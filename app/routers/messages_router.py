from typing import List
from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user, get_message_service
from app.models.user import User
from app.services.message_service import MessageService
from app.schemas.message_schema import (
    ConversationOut,
    ConversationWithMessagesOut,
    MessageOut,
    ParticipantOut,
    ConversationStart,
    MessageCreate,
    MessageUpdate
)

router = APIRouter()

@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """List all conversations for the current user."""
    convs = message_service.list_conversations(user.id, limit, offset)
    result = []
    for c in convs:
        unread_count = message_service.get_unread_count(c.id, user.id)
        result.append(ConversationOut(
            id=c.id,
            product_id=c.product_id,
            participants=[
                ParticipantOut(
                    user_id=p.user_id,
                    username=p.user.username if p.user else None
                ) for p in c.participants
            ],
            last_message_preview=(c.messages[-1].body[:120] if c.messages and c.messages[-1].body else None),
            last_message_at=(c.messages[-1].created_at if c.messages else None),
            unread_count=unread_count
        ))
    return result

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessagesOut)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get a specific conversation with all messages."""
    c = message_service.get_conversation(conversation_id, user.id)
    return ConversationWithMessagesOut(
        id=c.id,
        product_id=c.product_id,
        participants=[
            ParticipantOut(
                user_id=p.user_id,
                username=p.user.username if p.user else None
            ) for p in c.participants
        ],
        last_message_preview=(c.messages[-1].body[:120] if c.messages and c.messages[-1].body else None),
        last_message_at=(c.messages[-1].created_at if c.messages else None),
        messages=[MessageOut.model_validate(m) for m in c.messages]
    )

@router.post("/conversations", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationStart,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Start a new conversation about a product."""
    conv, msg = message_service.start_conversation(
        user.id,
        payload.product_id,
        payload.participant_ids,
        payload.first_message
    )
    return MessageOut.model_validate(msg)

@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Send a message in an existing conversation."""
    msg = message_service.send_message(conversation_id, user.id, payload.body)
    return MessageOut.model_validate(msg)

@router.patch("/messages/{message_id}", response_model=MessageOut)
def edit_message(
    message_id: int,
    payload: MessageUpdate,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Edit an existing message."""
    msg = message_service.edit_message(message_id, user.id, payload.body)
    return MessageOut.model_validate(msg)

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Delete a message (soft delete)."""
    message_service.delete_message(message_id, user.id)
    return

@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_conversation_read(
    conversation_id: int,
    user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Mark all messages in a conversation as read."""
    message_service.mark_conversation_as_read(conversation_id, user.id)
    return

