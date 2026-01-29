"""Admin model for Campus AI"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Admin(SQLModel, table=True):
    """Admin model for Campus AI"""
    __tablename__ = "admins"
    
    admin_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", index=True, nullable=False)
    permissions: str = Field(default="all", max_length=500)  # JSON string
    last_activity: Optional[datetime] = Field(default=None, nullable=True)
    notes: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
