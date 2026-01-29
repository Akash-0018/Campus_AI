"""Match Result model for Campus AI"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class MatchResult(SQLModel, table=True):
    """Match result between user requirements and resumes"""
    __tablename__ = "match_results"
    
    match_id: Optional[int] = Field(default=None, primary_key=True)
    requirement_id: int = Field(foreign_key="requirements.requirement_id", index=True, nullable=False)
    resume_id: int = Field(foreign_key="resumes.resume_id", index=True, nullable=False)
    
    # Match score and rank
    match_score: float = Field(nullable=False)  # 0-1
    rank: int = Field(nullable=False)  # 1, 2, etc.
    
    # Match details
    matched_skills: Optional[str] = Field(default=None, nullable=True)  # JSON
    skill_match_percentage: float = Field(default=0.0)
    experience_match: Optional[str] = Field(default=None, nullable=True)
    location_match: bool = Field(default=False)
    
    # Interaction tracking
    was_viewed: bool = Field(default=False)
    view_date: Optional[datetime] = Field(default=None, nullable=True)
    was_contacted: bool = Field(default=False)
    contact_date: Optional[datetime] = Field(default=None, nullable=True)
    feedback: Optional[str] = Field(default=None, nullable=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
