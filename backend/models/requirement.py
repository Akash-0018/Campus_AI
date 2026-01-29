"""Requirement model for Campus AI"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Requirement(SQLModel, table=True):
    """Requirement model collected from user chat"""
    __tablename__ = "requirements"
    
    requirement_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", index=True, nullable=False)
    
    # Conversation phase data
    role: Optional[str] = Field(default=None, nullable=True)  # Position type
    industry: Optional[str] = Field(default=None, nullable=True)  # Industry/domain
    team_size: Optional[str] = Field(default=None, nullable=True)  # Preferred team size
    
    # Collected requirements
    skills: Optional[str] = Field(default=None, nullable=True)  # Comma-separated or JSON list
    experience_years: Optional[str] = Field(default=None, nullable=True)  # Changed to string for flexibility
    education_level: Optional[str] = Field(default=None, nullable=True)
    location: Optional[str] = Field(default=None, nullable=True)
    keywords: Optional[str] = Field(default=None, nullable=True)  # JSON list
    salary_range: Optional[str] = Field(default=None, nullable=True)  # JSON: min, max
    additional_preferences: Optional[str] = Field(default=None, nullable=True)
    
    # Status tracking
    requirement_count: int = Field(default=0)  # Current conversation phase (0-4)
    is_complete: bool = Field(default=False)
    is_matched: bool = Field(default=False)
    
    # Vector embeddings
    embedding: Optional[str] = Field(default=None, nullable=True)  # JSON vector
    chroma_query_id: Optional[str] = Field(default=None, nullable=True, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
