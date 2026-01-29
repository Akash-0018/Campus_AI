"""Match result repository for Campus AI"""
from typing import Optional, List
from sqlmodel import Session, select
from models.match_result import MatchResult
from database.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class MatchResultRepository(BaseRepository[MatchResult]):
    """Match result repository for database operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, MatchResult)
    
    def get_by_requirement(self, requirement_id: int) -> List[MatchResult]:
        """Get all matches for a requirement"""
        try:
            statement = select(MatchResult).where(
                MatchResult.requirement_id == requirement_id
            ).order_by(MatchResult.rank)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting matches by requirement: {e}")
            raise
    
    def get_top_matches(self, requirement_id: int, limit: int = 2) -> List[MatchResult]:
        """Get top N matches for a requirement"""
        try:
            statement = select(MatchResult).where(
                MatchResult.requirement_id == requirement_id
            ).order_by(MatchResult.match_score.desc()).limit(limit)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error getting top matches: {e}")
            raise
    
    def mark_as_viewed(self, match_id: int) -> Optional[MatchResult]:
        """Mark match as viewed"""
        try:
            from datetime import datetime
            match = self.session.get(MatchResult, match_id)
            if match:
                match.was_viewed = True
                match.view_date = datetime.utcnow()
                self.session.add(match)
                self.session.commit()
                self.session.refresh(match)
            return match
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error marking match as viewed: {e}")
            raise

def get_match_result_repository(session: Session) -> MatchResultRepository:
    """Get match result repository instance"""
    return MatchResultRepository(session)
