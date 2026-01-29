"""Recruiter model for Campus AI"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Recruiter(SQLModel, table=True):
    """Recruiter profile model for Campus AI"""
    __tablename__ = "recruiters"
    
    recruiter_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", index=True, nullable=False)
    company_name: str = Field(max_length=200, nullable=False)
    company_email: str = Field(max_length=150, nullable=False)
    company_website: Optional[str] = Field(default=None, nullable=True)
    job_title: str = Field(max_length=150, nullable=False)
    department: Optional[str] = Field(default=None, nullable=True)
    phone_number: Optional[str] = Field(default=None, nullable=True)
    location: str = Field(max_length=200, nullable=False)
    company_description: Optional[str] = Field(default=None, nullable=True)
    total_resumes_reviewed: int = Field(default=0)
    is_verified: bool = Field(default=False)
    verification_date: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
