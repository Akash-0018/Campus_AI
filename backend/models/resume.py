"""Resume model for Campus AI"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Resume(SQLModel, table=True):
    """Resume model for Campus AI
    
    Users upload their own resumes for searching other users/profiles.
    Resumes are indexed in ChromaDB for semantic similarity matching.
    Can be uploaded individually by user or in bulk by admin.
    
    Flow:
    1. User uploads resume (self or admin bulk)
    2. Resume text is parsed (extracted: skills, experience, education, summary)
    3. Resume is embedded in ChromaDB for semantic search
    4. Other users can search and find this resume via chatbot
    5. Top-2 matches returned
    """
    __tablename__ = "resumes"
    
    resume_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", index=True, nullable=False)
    candidate_name: str = Field(max_length=200, nullable=False, index=True)
    candidate_email: Optional[str] = Field(default=None, nullable=True)
    candidate_phone: Optional[str] = Field(default=None, nullable=True)
    file_path: str = Field(max_length=500, nullable=False)
    file_name: str = Field(max_length=255, nullable=False)
    file_size: int = Field(nullable=False)  # in bytes
    file_type: str = Field(max_length=50, nullable=False)  # pdf, docx, txt
    
    # Parsed content
    skills: Optional[str] = Field(default=None, nullable=True)  # JSON list
    experience: Optional[str] = Field(default=None, nullable=True)  # Years
    education: Optional[str] = Field(default=None, nullable=True)  # JSON
    certifications: Optional[str] = Field(default=None, nullable=True)  # JSON
    location: Optional[str] = Field(default=None, nullable=True)
    summary: Optional[str] = Field(default=None, nullable=True)
    resume_text: Optional[str] = Field(default=None, nullable=True)  # Full cleaned text
    # Vector embeddings reference in ChromaDB
    chroma_collection_id: Optional[str] = Field(default=None, nullable=True, index=True)
    
    # Metadata
    is_active: bool = Field(default=True)  # Resume is stored/available
    is_current: bool = Field(default=True)  # Current active resume for user (only one per user)
    views_count: int = Field(default=0)
    match_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
