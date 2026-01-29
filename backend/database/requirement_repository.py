"""Requirement repository for Campus AI"""
from typing import Optional, List
from sqlmodel import Session, select
from models.requirement import Requirement
from database.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class RequirementRepository(BaseRepository[Requirement]):
    """Requirement repository for database operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, Requirement)
    
    def get_by_user(self, user_id: int) -> List[Requirement]:
        """Get all requirements by user"""
        try:
            statement = select(Requirement).where(
                Requirement.user_id == user_id
            ).order_by(Requirement.created_at.desc())
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting requirements by user: {e}")
            raise
    
    def get_active_by_user(self, user_id: int) -> Optional[Requirement]:
        """Get active requirement for user (not complete)"""
        try:
            statement = select(Requirement).where(
                (Requirement.user_id == user_id) & 
                (Requirement.is_complete == False)
            ).order_by(Requirement.created_at.desc())
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting active requirement for user: {e}")
            raise
    
    def get_latest_by_user(self, user_id: int) -> Optional[Requirement]:
        """Get latest requirement for user (regardless of completion status)"""
        try:
            statement = select(Requirement).where(
                Requirement.user_id == user_id
            ).order_by(Requirement.created_at.desc())
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting latest requirement for user: {e}")
            raise
    
    def get_by_chroma_id(self, chroma_id: str) -> Optional[Requirement]:
        """Get requirement by ChromaDB query ID"""
        try:
            statement = select(Requirement).where(Requirement.chroma_query_id == chroma_id)
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting requirement by chroma ID: {e}")
            raise

def get_requirement_repository(session: Session) -> RequirementRepository:
    """Get requirement repository instance"""
    return RequirementRepository(session)
