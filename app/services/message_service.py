from datetime import datetime, timezone
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.mysql.message_repository import MySQLMessageRepository
from app.models.messages import Conversation, Message
from app.models.product import Product


class MessageService:
    """Service for message and conversation operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.message_repo = MySQLMessageRepository(db)
    
    # ===== Query Operations =====
    
    def list_conversations(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Conversation]:
        """List all conversations for a user."""
        return self.message_repo.get_conversations_by_user(user_id, skip=offset, limit=limit)
    
    def get_conversation(self, conversation_id: int, user_id: int) -> Conversation:
        """Get a specific conversation if user is a participant."""
        if not self.message_repo.is_participant(conversation_id, user_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        
        conv = self.message_repo.get_conversation_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv
    
    # ===== Mutation Operations =====
    
    def start_conversation(
        self,
        creator_id: int,
        product_id: int,
        participant_ids: Optional[List[int]],
        first_message: str
    ) -> Tuple[Conversation, Message]:
        """Start a new conversation about a product."""
        # Verify product exists
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Create conversation
        conv = self.message_repo.create_conversation(product_id)
        
        # Add participants: creator + provided list, ensure uniqueness
        participants = set([creator_id])
        if participant_ids:
            participants.update(participant_ids)
        else:
            # Common case: chat with the seller
            if product.seller_id != creator_id:
                participants.add(product.seller_id)
        
        for uid in participants:
            self.message_repo.add_participant(conv.id, uid)
        
        # Create first message
        msg = self.message_repo.create_message(conv.id, creator_id, first_message)
        
        # Commit transaction
        self.message_repo.commit()
        
        # Refresh to get relationships
        self.db.refresh(conv)
        self.db.refresh(msg)
        
        return conv, msg
    
    def send_message(self, conversation_id: int, sender_id: int, body: str) -> Message:
        """Send a message in an existing conversation."""
        if not self.message_repo.is_participant(conversation_id, sender_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        
        msg = self.message_repo.create_message(conversation_id, sender_id, body)
        self.message_repo.update_conversation_timestamp(conversation_id)
        self.message_repo.commit()
        
        self.db.refresh(msg)
        return msg
    
    def edit_message(self, message_id: int, editor_id: int, new_body: str) -> Message:
        """Edit an existing message."""
        msg = self.message_repo.get_message_by_id(message_id)
        if not msg or msg.deleted_at:
            raise HTTPException(status_code=404, detail="Message not found")
        if msg.sender_id != editor_id:
            raise HTTPException(status_code=403, detail="Only the sender can edit")
        
        updated_msg = self.message_repo.update_message(message_id, new_body)
        self.message_repo.commit()
        
        self.db.refresh(updated_msg)
        return updated_msg
    
    def delete_message(self, message_id: int, requester_id: int) -> None:
        """Delete a message (soft delete)."""
        msg = self.message_repo.get_message_by_id(message_id)
        if not msg or msg.deleted_at:
            return
        if msg.sender_id != requester_id:
            raise HTTPException(status_code=403, detail="Only the sender can delete")
        
        self.message_repo.soft_delete_message(message_id)
        self.message_repo.commit()
    
    def get_unread_count(self, conversation_id: int, user_id: int) -> int:
        """Get count of unread messages in a conversation for a user."""
        return self.message_repo.get_unread_count(conversation_id, user_id)
    
    def mark_conversation_as_read(self, conversation_id: int, user_id: int) -> None:
        """Mark all unread messages in a conversation as read for a user."""
        if not self.message_repo.is_participant(conversation_id, user_id):
            raise HTTPException(status_code=403, detail="Not a participant")
        
        unread_messages = self.message_repo.get_unread_messages(conversation_id, user_id)
        message_ids = [msg.id for msg in unread_messages]
        
        if message_ids:
            self.message_repo.mark_messages_as_read(message_ids, user_id)
            self.message_repo.commit()

