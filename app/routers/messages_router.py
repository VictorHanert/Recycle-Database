from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.mysql import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.message_schema import (ConversationStart, MessageCreate, MessageUpdate,ConversationOut, ConversationWithMessagesOut, MessageOut, ParticipantOut)
from app.services.message_service import MessageService

router = APIRouter(tags=["messages"])

@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    convs = MessageService.list_conversations(db, user.id, limit, offset)
    out = []
    for c in convs:
        last = c.messages[-1] if c.messages else None
        unread_count = MessageService.get_unread_count(db, c.id, user.id)
        out.append(ConversationOut(
            id=c.id,
            product_id=c.product_id,
            participants=[
                ParticipantOut(
                    user_id=p.user_id,
                    username=p.user.username if p.user else None
                ) for p in c.participants
            ],
            last_message_preview=(last.body[:120] if last and last.body else None),
            last_message_at=(last.created_at if last else None),
            unread_count=unread_count,
        ))
    return out

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessagesOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = MessageService.get_conversation(db, conversation_id, user.id)
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv, msg = MessageService.start_conversation(
        db=db,
        creator_id=user.id,
        product_id=payload.product_id,
        participant_ids=payload.participant_ids,
        first_message=payload.first_message
    )
    return MessageOut.model_validate(msg)

@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg = MessageService.send_message(db, conversation_id, user.id, payload.body)
    return MessageOut.model_validate(msg)

@router.patch("/{message_id}", response_model=MessageOut)
def edit_message(
    message_id: int,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg = MessageService.edit_message(db, message_id, user.id, payload.body)
    return MessageOut.model_validate(msg)

@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    MessageService.delete_message(db, message_id, user.id)
    return

@router.post("/conversations/{conversation_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_conversation_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark all messages in a conversation as read."""
    MessageService.mark_conversation_as_read(db, conversation_id, user.id)
    return
