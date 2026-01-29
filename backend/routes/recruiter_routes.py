"""Recruiter routes for Campus AI"""
import logging
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, EmailStr
from sqlmodel import Session
from database.connection import get_db_session
from database.recruiter_repository import get_recruiter_repository
from database.user_repository import get_user_repository
from models.recruiter import Recruiter
from datetime import datetime
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recruiters", tags=["recruiters"])

class RecruiterProfileCreate(BaseModel):
    """Recruiter profile creation model"""
    company_name: str
    company_email: EmailStr
    job_title: str
    department: str = None
    company_website: str = None
    phone_number: str = None
    location: str
    company_description: str = None

class RecruiterProfileUpdate(BaseModel):
    """Recruiter profile update model"""
    company_name: str = None
    company_email: EmailStr = None
    job_title: str = None
    department: str = None
    company_website: str = None
    phone_number: str = None
    location: str = None
    company_description: str = None

class RecruiterResponse(BaseModel):
    """Recruiter response model"""
    recruiter_id: int
    user_id: int
    company_name: str
    company_email: str
    company_website: str | None = None
    job_title: str
    department: str | None = None
    phone_number: str | None = None
    location: str
    company_description: str | None = None
    total_resumes_reviewed: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/admin/list", response_model=list[RecruiterResponse])
async def list_all_recruiters(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session)
):
    """Admin: List all recruiters"""
    try:
        recruiter_repo = get_recruiter_repository(session)
        recruiters = recruiter_repo.read_all(skip=skip, limit=limit)
        return recruiters
    except Exception as e:
        logger.error(f"Error listing recruiters: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/profile", response_model=RecruiterResponse)
async def create_recruiter_profile(
    user_id: int,
    request: RecruiterProfileCreate,
    session: Session = Depends(get_db_session)
):
    """Create recruiter profile"""
    try:
        recruiter_repo = get_recruiter_repository(session)
        user_repo = get_user_repository(session)
        
        # Verify user exists
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if recruiter profile already exists
        existing = recruiter_repo.get_by_user_id(user_id)
        if existing:
            raise HTTPException(status_code=400, detail="Recruiter profile already exists")
        
        # Create recruiter profile
        recruiter = Recruiter(
            user_id=user_id,
            company_name=request.company_name,
            company_email=request.company_email,
            job_title=request.job_title,
            department=request.department,
            company_website=request.company_website,
            phone_number=request.phone_number,
            location=request.location,
            company_description=request.company_description,
            is_verified=False
        )
        
        recruiter = recruiter_repo.create(recruiter)
        logger.info(f"Recruiter profile created for user {user_id}")
        return recruiter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating recruiter profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{recruiter_id}", response_model=RecruiterResponse)
async def get_recruiter_profile(
    recruiter_id: int,
    session: Session = Depends(get_db_session)
):
    """Get recruiter profile"""
    try:
        recruiter_repo = get_recruiter_repository(session)
        recruiter = recruiter_repo.read(recruiter_id)
        if not recruiter:
            raise HTTPException(status_code=404, detail="Recruiter profile not found")
        return recruiter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recruiter profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{recruiter_id}", response_model=RecruiterResponse)
async def update_recruiter_profile(
    recruiter_id: int,
    request: RecruiterProfileUpdate,
    session: Session = Depends(get_db_session)
):
    """Update recruiter profile"""
    try:
        recruiter_repo = get_recruiter_repository(session)
        recruiter = recruiter_repo.read(recruiter_id)
        if not recruiter:
            raise HTTPException(status_code=404, detail="Recruiter profile not found")
        
        # Update fields
        if request.company_name:
            recruiter.company_name = request.company_name
        if request.company_email:
            recruiter.company_email = request.company_email
        if request.job_title:
            recruiter.job_title = request.job_title
        if request.department:
            recruiter.department = request.department
        if request.company_website:
            recruiter.company_website = request.company_website
        if request.phone_number:
            recruiter.phone_number = request.phone_number
        if request.location:
            recruiter.location = request.location
        if request.company_description:
            recruiter.company_description = request.company_description
        
        recruiter.updated_at = datetime.utcnow()
        updated = recruiter_repo.update(recruiter_id, recruiter)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating recruiter profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
