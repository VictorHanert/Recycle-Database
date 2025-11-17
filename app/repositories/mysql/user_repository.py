"""MySQL implementation of the User Repository."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.repositories.base import UserRepositoryInterface
from app.models.user import User
from app.models.favorites import Favorite
from app.models.item_views import ItemView
from app.models.messages import Message, ConversationParticipant, Conversation
from app.models.sold import SoldItemArchive
from app.schemas.user_schema import UserCreate, UserUpdate


class MySQLUserRepository(UserRepositoryInterface):
    """MySQL implementation of user repository operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with location relationship loaded."""
        return self.db.query(User).options(
            joinedload(User.location)
        ).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username with location relationship loaded."""
        return self.db.query(User).options(
            joinedload(User.location)
        ).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user."""
        try:
            db_user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed due to database constraint"
            ) from e
    
    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Update only provided fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed due to database constraint"
            ) from e
    
    def check_username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        return self.db.query(User).filter(User.username == username).first() is not None
    
    def check_email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        return self.db.query(User).filter(User.email == email).first() is not None
    
    def get_all(self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[User]:
        """Get all users with pagination and optional filtering"""
        query = self.db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()

    def search_users(self, search_term: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, or full name"""
        if not search_term:
            return self.get_all(skip, limit)
        
        search_filter = f"%{search_term}%"
        query = self.db.query(User).filter(
            (User.username.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (User.full_name.ilike(search_filter))
        )
        
        return query.offset(skip).limit(limit).all()

    def count_total_users(self) -> int:
        """Get total count of users"""
        return self.db.query(User).count()
    
    def get_active_users_count(self) -> int:
        """Count active users."""
        return self.db.query(User).filter(User.is_active == True).count()
    
    def get_admin_users(self) -> List[User]:
        """Get all admin users."""
        return self.db.query(User).options(
            joinedload(User.location)
        ).filter(User.is_admin == True).all()
    
    def toggle_user_status(self, user_id: int) -> Optional[User]:
        """Toggle user active status."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.is_active = not user.is_active
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user status"
            ) from e

    def delete(self, user_id: int) -> bool:
        """Delete a user and all related data"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        try:
            # Get conversation IDs where user is a participant (for cleanup)
            user_conversation_ids = [
                cp.conversation_id for cp in 
                self.db.query(ConversationParticipant.conversation_id)
                .filter(ConversationParticipant.user_id == user_id).all()
            ]
            
            # Delete messages sent by user
            self.db.query(Message).filter(Message.sender_id == user_id).delete()
            
            # Remove user from conversations
            self.db.query(ConversationParticipant).filter(ConversationParticipant.user_id == user_id).delete()
            
            # Clean up empty conversations
            for conv_id in user_conversation_ids:
                remaining_count = self.db.query(ConversationParticipant).filter(
                    ConversationParticipant.conversation_id == conv_id
                ).count()
                if remaining_count == 0:
                    self.db.query(Conversation).filter(Conversation.id == conv_id).delete()
            
            # Delete user's favorites and item views (some may be cascade deleted)
            self.db.query(Favorite).filter(Favorite.user_id == user_id).delete()
            self.db.query(ItemView).filter(ItemView.viewer_user_id == user_id).delete()
            
            # Update sold items to remove buyer reference (preserve sales history)
            self.db.query(SoldItemArchive).filter(SoldItemArchive.buyer_id == user_id).update({
                SoldItemArchive.buyer_id: None
            })
            
            # Delete the user
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
