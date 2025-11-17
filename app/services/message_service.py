from datetime import datetime, timezone
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, exists, and_
from app.models.messages import Conversation, ConversationParticipant, Message, MessageRead
from app.models.product import Product

class MessageService:
    # Helpers
    @staticmethod
    def _is_participant(db: Session, conversation_id: int, user_id: int) -> bool:
        return db.query(
            exists().where(and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            ))
        ).scalar()

    # Queries
    @staticmethod
    def list_conversations(db: Session, user_id: int, limit: int = 20, offset: int = 0) -> List[Conversation]:
        q = (db.query(Conversation)
               .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
               .filter(ConversationParticipant.user_id == user_id)
               .options(joinedload(Conversation.participants),
                        joinedload(Conversation.messages))
               .order_by(desc(Conversation.id)))
        return q.offset(offset).limit(limit).all()

    @staticmethod
    def get_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
        if not MessageService._is_participant(db, conversation_id, user_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        conv = (db.query(Conversation)
                  .options(joinedload(Conversation.participants),
                           joinedload(Conversation.messages))
                  .filter(Conversation.id == conversation_id)
                  .first())
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv

    # Mutations
    @staticmethod
    def start_conversation(
        db: Session,
        creator_id: int,
        product_id: int,
        participant_ids: Optional[List[int]],
        first_message: str
    ) -> Tuple[Conversation, Message]:
        # Create conversation
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        conv = Conversation(product_id=product_id)
        db.add(conv)
        db.flush()  # get conv.id

        # Participants: creator + provided list, ensure uniqueness
        participants = set([creator_id])
        if participant_ids:
            participants.update(participant_ids)
        else:
            # Common case: chat with the seller
            if product.seller_id != creator_id:
                participants.add(product.seller_id)

        for uid in participants:
            db.add(ConversationParticipant(conversation_id=conv.id, user_id=uid))

        # First message
        msg = Message(conversation_id=conv.id, sender_id=creator_id, body=first_message)
        db.add(msg)
        db.commit()
        db.refresh(conv)
        db.refresh(msg)
        return conv, msg

    @staticmethod
    def send_message(db: Session, conversation_id: int, sender_id: int, body: str) -> Message:
        if not MessageService._is_participant(db, conversation_id, sender_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        msg = Message(conversation_id=conversation_id, sender_id=sender_id, body=body)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def edit_message(db: Session, message_id: int, editor_id: int, new_body: str) -> Message:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg or msg.deleted_at:
            raise HTTPException(status_code=404, detail="Message not found")
        if msg.sender_id != editor_id:
            raise HTTPException(status_code=403, detail="Only the sender can edit")
        msg.body = new_body
        msg.created_at = msg.created_at  # unchanged
        # optional: track edited_at if you add it later
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def delete_message(db: Session, message_id: int, requester_id: int) -> None:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg or msg.deleted_at:
            return
        if msg.sender_id != requester_id:
            raise HTTPException(status_code=403, detail="Only the sender can delete")
        msg.deleted_at = datetime.now(timezone.utc)
        # optional: also null out body if you want "Message deleted"
        db.commit()

    @staticmethod
    def get_unread_count(db: Session, conversation_id: int, user_id: int) -> int:
        """Count unread messages for a user in a conversation."""
        unread = (db.query(Message)
                    .filter(Message.conversation_id == conversation_id,
                            Message.sender_id != user_id,
                            Message.deleted_at.is_(None))
                    .outerjoin(MessageRead, and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user_id
                    ))
                    .filter(MessageRead.user_id.is_(None))
                    .count())
        return unread

    @staticmethod
    def mark_conversation_as_read(db: Session, conversation_id: int, user_id: int) -> None:
        """Mark all messages in a conversation as read for a user."""
        if not MessageService._is_participant(db, conversation_id, user_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        
        unread_messages = (db.query(Message)
                            .filter(Message.conversation_id == conversation_id,
                                    Message.sender_id != user_id,
                                    Message.deleted_at.is_(None))
                            .outerjoin(MessageRead, and_(
                                MessageRead.message_id == Message.id,
                                MessageRead.user_id == user_id
                            ))
                            .filter(MessageRead.user_id.is_(None))
                            .all())
        
        for msg in unread_messages:
            db.add(MessageRead(message_id=msg.id, user_id=user_id))
        
        db.commit()
