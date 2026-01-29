"""Resume repository for Campus AI"""
from typing import Optional, List
from sqlmodel import Session, select
from models.resume import Resume
from database.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class ResumeRepository(BaseRepository[Resume]):
    """Resume repository for database operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, Resume)
    
    def get_by_user(self, user_id: int) -> List[Resume]:
        """Get all resumes by user"""
        try:
            statement = select(Resume).where(
                Resume.user_id == user_id
            ).order_by(Resume.created_at.desc())
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting resumes by user: {e}")
            raise
    
    def get_by_chroma_id(self, chroma_id: str) -> Optional[Resume]:
        """Get resume by ChromaDB collection ID"""
        try:
            statement = select(Resume).where(Resume.chroma_collection_id == chroma_id)
            return self.session.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting resume by chroma ID: {e}")
            raise
    
    def get_active(self) -> List[Resume]:
        """Get all active resumes"""
        try:
            statement = select(Resume).where(Resume.is_active == True)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting active resumes: {e}")
            raise
    
    def increment_views(self, resume_id: int) -> Optional[Resume]:
        """Increment resume views count"""
        try:
            resume = self.session.get(Resume, resume_id)
            if resume:
                resume.views_count += 1
                self.session.add(resume)
                self.session.commit()
                self.session.refresh(resume)
            return resume
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error incrementing views for resume {resume_id}: {e}")
            raise

def get_resume_repository(session: Session) -> ResumeRepository:
    """Get resume repository instance"""
    return ResumeRepository(session)
