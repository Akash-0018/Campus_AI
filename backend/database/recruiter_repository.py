"""Recruiter repository for Campus AI"""
from typing import Optional, List
from sqlmodel import Session, select
from models.recruiter import Recruiter
from database.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class RecruiterRepository(BaseRepository[Recruiter]):
    """Recruiter repository for database operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, Recruiter)
    
    def get_by_user_id(self, user_id: int) -> Optional[Recruiter]:
        """Get recruiter by user ID"""
        try:
            statement = select(Recruiter).where(Recruiter.user_id == user_id)
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting recruiter by user ID: {e}")
            raise
    
    def get_by_company(self, company_name: str) -> List[Recruiter]:
        """Get all recruiters from a company"""
        try:
            statement = select(Recruiter).where(Recruiter.company_name == company_name)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting recruiters by company: {e}")
            raise
    
    def get_verified(self) -> List[Recruiter]:
        """Get all verified recruiters"""
        try:
            statement = select(Recruiter).where(Recruiter.is_verified == True)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting verified recruiters: {e}")
            raise

def get_recruiter_repository(session: Session) -> RecruiterRepository:
    """Get recruiter repository instance"""
    return RecruiterRepository(session)
