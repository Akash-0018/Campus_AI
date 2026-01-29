"""Admin routes for Campus AI"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database.connection import get_db_session
from database.user_repository import get_user_repository
from database.resume_repository import get_resume_repository
from models.user import User, UserRole
import hashlib

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

class DashboardStats(BaseModel):
    """Dashboard statistics model"""
    total_users: int
    total_resumes: int
    active_users: int

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(session: Session = Depends(get_db_session)):
    """Get admin dashboard statistics"""
    try:
        user_repo = get_user_repository(session)
        resume_repo = get_resume_repository(session)
        
        # Get stats
        all_users = user_repo.read_all(skip=0, limit=10000)
        total_users = len(all_users)
        active_users = len([u for u in all_users if u.is_active])
        
        resumes = resume_repo.get_active()
        total_resumes = len(resumes)
        
        return DashboardStats(
            total_users=total_users,
            total_resumes=total_resumes,
            active_users=active_users
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/list")
async def list_all_users(
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_db_session)
):
    """Admin: List all users"""
    try:
        user_repo = get_user_repository(session)
        users = user_repo.read_all(skip=skip, limit=limit)
        return users
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    session: Session = Depends(get_db_session)
):
    """Admin: Activate/Deactivate user"""
    try:
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_active = is_active
        updated = user_repo.update(user_id, user)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

