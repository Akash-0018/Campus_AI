"""
User Profile Management Service for Campus AI
Handles user profile edits, resume management, and search
"""
import logging
import json
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from models.user import User
from models.resume import Resume
from services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user profiles and resumes"""
    
    def __init__(self, session: Session):
        """Initialize with database session"""
        self.session = session
        self.embeddings_service = EmbeddingsService()
        logger.info("UserProfileService initialized")
    
    def get_user_profile(self, user_id: int) -> dict:
        """Get user profile with all details"""
        try:
            user = self.session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            # Get user's resumes
            resumes = self.session.exec(
                select(Resume).where(Resume.user_id == user_id)
            ).all()
            
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "bio": user.bio,
                "phone_number": user.phone_number,
                "profile_image_url": user.profile_image_url,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "resumes_count": len(resumes),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            raise
    
    def update_user_profile(self, user_id: int, update_data: dict) -> dict:
        """Update user profile fields (bio, phone, image, etc)"""
        try:
            user = self.session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            # Update editable fields
            editable_fields = ['full_name', 'bio', 'phone_number', 'profile_image_url']
            for field in editable_fields:
                if field in update_data and update_data[field] is not None:
                    setattr(user, field, update_data[field])
            
            user.updated_at = datetime.utcnow()
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            
            logger.info(f"Updated profile for user {user_id}")
            return self.get_user_profile(user_id)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating user profile: {e}")
            raise
    
    def add_user_resume(
        self,
        user_id: int,
        file_name: str,
        file_path: str,
        file_size: int,
        file_type: str,
        parsed_data: dict = None
    ) -> dict:
        """Add a resume for the user
        
        New Flow:
        - Users can only have ONE active resume at a time
        - If user already has a current resume, this request will be rejected
        - User must delete the old resume before uploading a new one
        """
        try:
            user = self.session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            # Check if user already has an active/current resume
            existing_resume = self.session.exec(
                select(Resume).where(
                    (Resume.user_id == user_id) & (Resume.is_current == True)
                )
            ).first()
            
            if existing_resume:
                logger.warning(f"User {user_id} already has an active resume. Must delete before uploading new one.")
                return {
                    'error': True,
                    'message': 'User already has an active resume',
                    'detail': 'Please delete your existing resume before uploading a new one',
                    'existing_resume_id': existing_resume.resume_id
                }
            
            resume = Resume(
                user_id=user_id,
                candidate_name=user.full_name,
                candidate_email=user.email,
                candidate_phone=user.phone_number,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                skills=json.dumps(parsed_data.get('skills', [])) if parsed_data else '[]',
                experience=parsed_data.get('experience_years') if parsed_data else None,
                education=json.dumps(parsed_data.get('education')) if parsed_data else '[]',
                summary=parsed_data.get('summary', '') if parsed_data else '',
                location=parsed_data.get('location', '') if parsed_data else '',
                resume_text=parsed_data.get('clean_text') if parsed_data else None,  # 🔥 ADD THIS
                is_active=True,
                is_current=True
            )

            
            self.session.add(resume)
            self.session.commit()
            self.session.refresh(resume)
            
            # Index in ChromaDB
            self._index_resume_in_chromadb(resume, user)
            
            logger.info(f"Added resume {resume.resume_id} for user {user_id} as current resume")
            return self._format_resume(resume, user)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding user resume: {e}")
            raise
    
    def _index_resume_in_chromadb(self, resume: Resume, user: User) -> None:
        """Index resume in ChromaDB for semantic search with improved structure"""
        try:
            logger.info(f"[DB_STORAGE_STEP_1] Storing resume data in local database - Resume ID: {resume.resume_id}, User ID: {user.user_id}")
            logger.info(f"[DB_TABLE_INFO] Database table: 'resume' - Fields stored: resume_id, user_id, candidate_name, file_name, skills, experience, education, location, summary")
            
            # Parse resume data
            skills = json.loads(resume.skills) if isinstance(resume.skills, str) else []
            education = json.loads(resume.education) if isinstance(resume.education, str) else []
            
            logger.info(f"[DB_STORED_DATA] Resume data successfully stored in local DB")
            logger.info(f"[DB_STORED_FIELDS] resume_id={resume.resume_id}, user_id={user.user_id}, file_name={resume.file_name}, skills={skills}, experience={resume.experience}, education={education}, location={resume.location}")
            
            # Create comprehensive, well-structured profile text for better embeddings
            # This structure helps the embedding model understand the context better
# 🔥 USE FULL PARSED RESUME TEXT FOR EMBEDDINGS
            profile_text = resume.resume_text or resume.summary

            if not profile_text or len(profile_text.strip()) < 300:
                logger.error(
                    f"[EMBEDDING_VALIDATION_ERROR] Resume text too short for embedding "
                    f"(resume_id={resume.resume_id})"
                )
                return

            
            logger.info(f"[DB_TO_EMBEDDING_FLOW] Preparing resume content for embedding conversion...")
            logger.info(f"[CONTENT_FOR_EMBEDDING]\n{profile_text}")
            
            doc_id = f"user_resume_{resume.resume_id}"
            metadata = {
                "resume_id": str(resume.resume_id),
                "user_id": str(user.user_id),
                "name": user.full_name,
                "email": user.email,
                "skills": resume.skills or "[]",
                "location": resume.location or "",
                "experience": resume.experience or ""
            }
            
            logger.info(f"[CHROMADB_STORAGE_START] Preparing to store in ChromaDB...")
            self.embeddings_service.add_document(
                collection_name="user_resumes",
                document_id=doc_id,
                text=profile_text.strip(),
                metadata=metadata
            )
            
            # Update resume with ChromaDB reference
            resume.chroma_collection_id = doc_id
            self.session.add(resume)
            self.session.commit()
            
            logger.info(f"[CHROMADB_STORAGE_SUCCESS] Resume indexed in ChromaDB collection 'user_resumes' with document ID: {doc_id}")
            logger.info(f"[CHROMADB_COLLECTION_INFO] Collection: 'user_resumes' | Document ID: {doc_id} | Resume ID: {resume.resume_id}")
        except Exception as e:
            logger.error(f"Error indexing resume in ChromaDB: {e}")
            # Don't fail the whole operation if ChromaDB fails
    
    def get_user_resumes(self, user_id: int) -> List[dict]:
        """Get all resumes for a user"""
        try:
            user = self.session.get(User, user_id)
            if not user:
                return []
            
            resumes = self.session.exec(
                select(Resume).where(Resume.user_id == user_id)
            ).all()
            
            return [self._format_resume(r, user) for r in resumes]
        except Exception as e:
            logger.error(f"Error getting user resumes: {e}")
            raise
    
    def delete_resume(self, resume_id: int, user_id: int) -> bool:
        """Delete a resume (only own resumes)
        
        New Flow:
        - User must delete current resume before uploading a new one
        - Deletes the resume from DB and ChromaDB
        """
        try:
            resume = self.session.get(Resume, resume_id)
            if not resume or resume.user_id != user_id:
                logger.warning(f"Resume {resume_id} not found or not owned by user {user_id}")
                return False
            
            # Delete from ChromaDB
            if resume.chroma_collection_id:
                try:
                    self.embeddings_service.delete_document(
                        collection_name="user_resumes",
                        document_id=resume.chroma_collection_id
                    )
                except Exception as e:
                    logger.warning(f"Could not delete from ChromaDB: {e}")
            
            self.session.delete(resume)
            self.session.commit()
            
            logger.info(f"Deleted resume {resume_id} from user {user_id}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting resume: {e}")
            raise
    
    def get_current_resume(self, user_id: int) -> Optional[dict]:
        """Get the current active resume for a user"""
        try:
            user = self.session.get(User, user_id)
            if not user:
                return None
            
            resume = self.session.exec(
                select(Resume).where(
                    (Resume.user_id == user_id) & (Resume.is_current == True)
                )
            ).first()
            
            if not resume:
                return None
            
            return self._format_resume(resume, user)
        except Exception as e:
            logger.error(f"Error getting current resume: {e}")
            raise
    
    def _format_resume(self, resume: Resume, user: User) -> dict:
        """Format resume for API response"""
        return {
            "resume_id": resume.resume_id,
            "user_id": user.user_id,
            "candidate_name": resume.candidate_name,
            "candidate_email": resume.candidate_email,
            "candidate_phone": resume.candidate_phone,
            "file_name": resume.file_name,
            "file_type": resume.file_type,
            "file_size": resume.file_size,
            "skills": json.loads(resume.skills) if isinstance(resume.skills, str) else [],
            "experience": resume.experience,
            "education": json.loads(resume.education) if isinstance(resume.education, str) else [],
            "location": resume.location,
            "summary": resume.summary,
            "is_active": resume.is_active,
            "is_current": resume.is_current,
            "views_count": resume.views_count,
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None
        }

def get_user_profile_service(session: Session) -> UserProfileService:
    """Factory function for UserProfileService"""
    return UserProfileService(session)
