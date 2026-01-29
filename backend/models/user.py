"""User model for Campus AI"""
from typing import Optional
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

class UserRole(str, Enum):
    """User role enumeration - 2 roles only
    
    ADMIN: Platform administration (manage users, bulk uploads, governance)
    USER: Regular users (upload resumes, edit profile, use chatbot, search)
    
    Note: RECRUITER role removed - all users are now treated equally
    """
    ADMIN = "admin"
    USER = "user"

class User(SQLModel, table=True):
    """User model for Campus AI"""
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, max_length=100, nullable=False, unique=True)
    email: str = Field(index=True, max_length=150, nullable=False, unique=True)
    password_hash: Optional[str] = Field(default=None, nullable=True)
    full_name: str = Field(max_length=200, nullable=False)
    role: str = Field(default=UserRole.USER.value, max_length=20)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    profile_image_url: Optional[str] = Field(default=None, nullable=True)
    bio: Optional[str] = Field(default=None, nullable=True)
    phone_number: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None, nullable=True)
