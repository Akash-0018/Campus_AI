"""
User routes for Campus AI
Handles profile management, resume uploads, and chatbot search
"""
import logging
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from database.connection import get_db_session
from database.user_repository import get_user_repository
from models.user import User
from models.resume import Resume
from services.user_profile_service import UserProfileService
from services.chatbot_search_service import ChatbotSearchService
from services.resume_parsing_service import get_resume_parsing_service
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserProfileUpdate(BaseModel):
    """User profile update model"""
    full_name: str = None
    phone_number: str = None
    bio: str = None
    profile_image_url: str = None

class UserResponse(BaseModel):
    """User response model"""
    user_id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    profile_image_url: str | None = None
    bio: str | None = None
    phone_number: str | None = None
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    user_id: Optional[int] = None
    min_similarity: float = 0.25  # Minimum similarity threshold (0.0-1.0, lower for better range)

class ResumeResponse(BaseModel):
    """Resume response model"""
    resume_id: int
    user_id: int
    file_name: str
    file_size: int
    file_type: str
    skills: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    is_active: bool
    is_current: bool
    views_count: int = 0

# ============================================================================
# USER PROFILE ROUTES
# ============================================================================

@router.get("/admin/list", response_model=list[UserResponse])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
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

@router.get("/directory")
async def get_user_directory(
    exclude_user_id: Optional[int] = Query(None),
    session: Session = Depends(get_db_session)
):
    """Get all active users (searchable directory)"""
    try:
        service = ChatbotSearchService(session)
        users = service.get_all_active_users(exclude_user_id=exclude_user_id)
        
        return {
            "status": "success",
            "user_count": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Error getting directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: Session = Depends(get_db_session)):
    """Get user by ID"""
    try:
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserProfileUpdate,
    session: Session = Depends(get_db_session)
):
    """Update user profile"""
    try:
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        if request.full_name:
            user.full_name = request.full_name
        if request.phone_number:
            user.phone_number = request.phone_number
        if request.bio:
            user.bio = request.bio
        if request.profile_image_url:
            user.profile_image_url = request.profile_image_url
        user.updated_at = datetime.utcnow()
        
        updated_user = user_repo.update(user_id, user)
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# RESUME MANAGEMENT ROUTES
# ============================================================================

@router.post("/resume/upload/{user_id}")
async def upload_resume(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session)
):
    """Upload and index user resume
    
    New Flow:
    - User can only have ONE active resume at a time
    - If user already has a resume, upload request will be rejected
    - User must delete existing resume before uploading a new one
    - On successful upload, resume is indexed in ChromaDB for semantic search
    """
    try:
        # Validate user exists
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Check if user already has an active resume
        existing_resume = session.exec(
            select(Resume).where(
                (Resume.user_id == user_id) & (Resume.is_current == True)
            )
        ).first()
        
        if existing_resume:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active resume. Please delete the existing resume before uploading a new one.",
                headers={"X-Existing-Resume-ID": str(existing_resume.resume_id)}
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Save file
        uploads_dir = Path("uploads/resumes")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = uploads_dir / f"{user_id}_{file.filename}"
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info("[RESUME_PARSING_START] Parsing uploaded resume")

        parsing_service = get_resume_parsing_service()

        file_ext = file.filename.split(".")[-1].lower()

        parsed = parsing_service.parse_resume(
            file_path=str(file_path),
            file_type=file_ext
        )

        logger.info(
            f"[RESUME_PARSING_SUCCESS] Cleaned resume length: "
            f"{len(parsed.get('clean_text', ''))}"
        )

        
        # Add resume (with new flow - now as current resume)
        logger.info(f"[RESUME_UPLOAD_SERVICE_CALL] Calling UserProfileService.add_user_resume() for user {user_id}")
        service = UserProfileService(session)
        resume_result = service.add_user_resume(
            user_id=user_id,
            file_name=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            file_type=file_ext,
            parsed_data=parsed
        )
        
        # Check if result is an error response
        if isinstance(resume_result, dict) and resume_result.get('error'):
            logger.error(f"[RESUME_UPLOAD_ERROR] Failed to add resume: {resume_result.get('detail')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resume_result.get('detail', resume_result.get('message'))
            )
        
        if not resume_result:
            logger.error(f"[RESUME_UPLOAD_ERROR] Resume service returned null result")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add resume"
            )
        
        logger.info(f"[RESUME_UPLOAD_COMPLETE_SUCCESS] Resume uploaded and indexed successfully for user {user_id}")
        return {
            "status": "success",
            "message": "Resume uploaded, indexed in vector database, and set as current resume",
            "resume": resume_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/resume/current/{user_id}")
async def get_current_resume(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Get the current active resume for a user"""
    try:
        # Validate user exists
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        service = UserProfileService(session)
        current_resume = service.get_current_resume(user_id)
        
        if not current_resume:
            return {
                "status": "no_resume",
                "message": "User has no active resume",
                "user_id": user_id
            }
        
        return {
            "status": "success",
            "user_id": user_id,
            "resume": current_resume
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/resumes/{user_id}")
async def get_user_resumes(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Get all resumes for a user"""
    try:
        # Validate user exists
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        service = UserProfileService(session)
        resumes = service.get_user_resumes(user_id)
        
        # Resumes are already formatted by service and include is_current field
        resume_list = resumes
        
        return {
            "user_id": user_id,
            "resume_count": len(resume_list),
            "resumes": resume_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/resume/{resume_id}/{user_id}")
async def delete_resume(
    resume_id: int,
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Delete a resume (user can only delete own)
    
    New Flow:
    - User must delete their current resume before uploading a new one
    - Deletes from database and vector store (ChromaDB)
    """
    try:
        service = UserProfileService(session)
        success = service.delete_resume(resume_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or not owned by user"
            )
        
        return {
            "status": "success",
            "message": "Resume deleted successfully. You can now upload a new resume.",
            "resume_id": resume_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# CHATBOT / SEARCH ROUTES
# ============================================================================

@router.post("/search/profiles")
async def search_user_profiles(
    search_request: SearchRequest,
    session: Session = Depends(get_db_session)
):
    """
    Search for user profiles via vector embedding similarity
    
    Returns the TOP-2 best matching profiles from the database
    using semantic similarity search based on resume embeddings.
    
    The algorithm:
    1. Embeds the query into vector space
    2. Compares with all user resume embeddings in ChromaDB
    3. Returns the 2 profiles with highest similarity scores
    """
    try:
        query = search_request.query
        current_user_id = search_request.user_id
        min_similarity = search_request.min_similarity if hasattr(search_request, 'min_similarity') else 0.25
        
        if not query or query.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query is required"
            )
        
        # Validate similarity threshold
        min_similarity = max(0.0, min(min_similarity, 1.0))  # Between 0 and 1
        
        service = ChatbotSearchService(session)
        # Always return top-2 (strict enforcement)
        results = service.search_user_profiles(
            query=query,
            top_k=2,  # ALWAYS TOP-2 - Strictly enforced
            current_user_id=current_user_id,
            min_similarity=min_similarity
        )
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/profile/{resume_id}/view")
async def record_profile_view(
    resume_id: int,
    session: Session = Depends(get_db_session)
):
    """Record that a profile was viewed"""
    try:
        service = ChatbotSearchService(session)
        service.increment_profile_views(resume_id)
        
        return {
            "status": "success",
            "message": "Profile view recorded"
        }
    except Exception as e:
        logger.error(f"Error recording view: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# ADMIN ONLY ROUTES
# ============================================================================

@router.post("/admin/resume/bulk-upload")
async def bulk_upload_resumes(
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_db_session)
):
    """
    Admin endpoint: Bulk upload resumes
    Associates resumes with existing users or creates new ones
    """
    try:
        uploaded = []
        errors = []
        
        for file in files:
            try:
                # Save file
                uploads_dir = Path("uploads/resumes")
                uploads_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = uploads_dir / file.filename
                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                
                uploaded.append({
                    "filename": file.filename,
                    "size": len(content),
                    "path": str(file_path)
                })
            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return {
            "status": "success" if not errors else "partial",
            "uploaded_count": len(uploaded),
            "error_count": len(errors),
            "uploaded": uploaded,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/admin/all-resumes")
async def get_all_resumes(session: Session = Depends(get_db_session)):
    """Admin endpoint: Get all resumes in system"""
    try:
        resumes = session.exec(select(Resume)).all()
        
        resume_list = []
        for resume in resumes:
            user = session.get(User, resume.user_id)
            resume_list.append({
                "resume_id": resume.resume_id,
                "user_id": resume.user_id,
                "user_name": user.full_name if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "file_name": resume.file_name,
                "file_size": resume.file_size,
                "skills": json.loads(resume.skills) if isinstance(resume.skills, str) else [],
                "created_at": resume.created_at.isoformat() if resume.created_at else None,
                "is_active": resume.is_active,
                "views_count": resume.views_count
            })
        
        return {
            "status": "success",
            "resume_count": len(resume_list),
            "resumes": resume_list
        }
    except Exception as e:
        logger.error(f"Error getting all resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# INFO ROUTES
# ============================================================================

@router.get("/health")
async def users_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "User Management API",
        "capabilities": [
            "Profile management",
            "Resume upload & indexing",
            "Semantic search (top-2 matches)",
            "Admin bulk operations"
        ]
    }