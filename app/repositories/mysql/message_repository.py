"""MySQL implementation of the Message Repository."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, exists, and_

from app.models.messages import Conversation, ConversationParticipant, Message, MessageRead
from app.models.user import User


class MySQLMessageRepository:
    """MySQL implementation of message repository operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== Conversation Operations =====
    
    def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID with participants and messages loaded."""
        return (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.participants).joinedload(ConversationParticipant.user),
                joinedload(Conversation.messages).joinedload(Message.sender)
            )
            .filter(Conversation.id == conversation_id)
            .first()
        )
    
    def get_conversations_by_user(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Conversation]:
        """Get all conversations for a user with pagination."""
        return (
            self.db.query(Conversation)
            .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
            .filter(ConversationParticipant.user_id == user_id)
            .options(
                joinedload(Conversation.participants).joinedload(ConversationParticipant.user),
                joinedload(Conversation.messages).joinedload(Message.sender)
            )
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_conversation(self, product_id: int) -> Conversation:
        """Create a new conversation for a product."""
        conversation = Conversation(
            product_id=product_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.db.add(conversation)
        self.db.flush()  # Get the conversation ID
        return conversation
    
    def update_conversation_timestamp(self, conversation_id: int) -> None:
        """Update the conversation's updated_at timestamp."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc)
            self.db.commit()
    
    # ===== Participant Operations =====
    
    def is_participant(self, conversation_id: int, user_id: int) -> bool:
        """Check if a user is a participant in a conversation."""
        return self.db.query(
            exists().where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id
                )
            )
        ).scalar()
    
    def add_participant(self, conversation_id: int, user_id: int) -> ConversationParticipant:
        """Add a participant to a conversation."""
        participant = ConversationParticipant(
            conversation_id=conversation_id,
            user_id=user_id,
            joined_at=datetime.now(timezone.utc)
        )
        self.db.add(participant)
        self.db.flush()
        return participant
    
    def get_participants(self, conversation_id: int) -> List[ConversationParticipant]:
        """Get all participants of a conversation."""
        return (
            self.db.query(ConversationParticipant)
            .options(joinedload(ConversationParticipant.user))
            .filter(ConversationParticipant.conversation_id == conversation_id)
            .all()
        )
    
    # ===== Message Operations =====
    
    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Get message by ID."""
        return (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(Message.id == message_id)
            .first()
        )
    
    def get_messages_by_conversation(
        self, 
        conversation_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages in a conversation with pagination."""
        return (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None)
            )
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_message(
        self, 
        conversation_id: int, 
        sender_id: int, 
        body: str
    ) -> Message:
        """Create a new message."""
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(message)
        self.db.flush()
        return message
    
    def update_message(self, message_id: int, new_body: str) -> Optional[Message]:
        """Update a message's body."""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if message and not message.deleted_at:
            message.body = new_body
            self.db.flush()
            return message
        return None
    
    def soft_delete_message(self, message_id: int) -> bool:
        """Soft delete a message."""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if message and not message.deleted_at:
            message.deleted_at = datetime.now(timezone.utc)
            self.db.flush()
            return True
        return False
    
    # ===== Message Read Tracking =====
    
    def get_unread_messages(
        self, 
        conversation_id: int, 
        user_id: int
    ) -> List[Message]:
        """Get unread messages for a user in a conversation."""
        return (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.deleted_at.is_(None)
            )
            .outerjoin(
                MessageRead,
                and_(
                    MessageRead.message_id == Message.id,
                    MessageRead.user_id == user_id
                )
            )
            .filter(MessageRead.user_id.is_(None))
            .all()
        )
    
    def get_unread_count(self, conversation_id: int, user_id: int) -> int:
        """Count unread messages for a user in a conversation."""
        return (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.deleted_at.is_(None)
            )
            .outerjoin(
                MessageRead,
                and_(
                    MessageRead.message_id == Message.id,
                    MessageRead.user_id == user_id
                )
            )
            .filter(MessageRead.user_id.is_(None))
            .count()
        )
    
    def mark_message_as_read(self, message_id: int, user_id: int) -> MessageRead:
        """Mark a specific message as read for a user."""
        message_read = MessageRead(
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.now(timezone.utc)
        )
        self.db.add(message_read)
        self.db.flush()
        return message_read
    
    def mark_messages_as_read(self, message_ids: List[int], user_id: int) -> None:
        """Mark multiple messages as read for a user."""
        for message_id in message_ids:
            # Check if already marked as read
            exists_read = self.db.query(MessageRead).filter(
                MessageRead.message_id == message_id,
                MessageRead.user_id == user_id
            ).first()
            
            if not exists_read:
                message_read = MessageRead(
                    message_id=message_id,
                    user_id=user_id,
                    read_at=datetime.now(timezone.utc)
                )
                self.db.add(message_read)
        self.db.flush()
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()
