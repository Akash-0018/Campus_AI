"""User repository for Campus AI"""
from typing import Optional, List
from sqlmodel import Session, select
from models.user import User, UserRole
from database.base_repository import BaseRepository
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User]):
    """User repository for database operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            statement = select(User).where(User.email == email)
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            raise
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            statement = select(User).where(User.username == username)
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            raise
    
    def get_by_role(self, role: UserRole) -> List[User]:
        """Get all users by role"""
        try:
            statement = select(User).where(User.role == role.value)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting users by role: {e}")
            raise
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """Update user's last login timestamp"""
        try:
            user = self.session.get(User, user_id)
            if user:
                user.last_login = datetime.utcnow()
                self.session.add(user)
                self.session.commit()
                self.session.refresh(user)
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating last login for user {user_id}: {e}")
            raise
    
    def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        try:
            user = self.session.get(User, user_id)
            if user:
                user.is_verified = True
                self.session.add(user)
                self.session.commit()
                self.session.refresh(user)
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error verifying user {user_id}: {e}")
            raise

# Singleton instance
user_repository = None

def get_user_repository(session: Session) -> UserRepository:
    """Get user repository instance"""
    return UserRepository(session)
