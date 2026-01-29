"""Resume routes for Campus AI"""

import logging
import json
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from utils.constants import RESUME_COLLECTION
from database.connection import get_db_session
from database.resume_repository import get_resume_repository
from database.user_repository import get_user_repository
from models.resume import Resume
from services.resume_parsing_service import get_resume_parsing_service
from services.embeddings_service import embeddings_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

# ------------------------------------------------------------------
# SAFE UPLOAD PATH (independent of working directory)
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "resumes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# RESPONSE MODEL
# ------------------------------------------------------------------
class ResumeResponse(BaseModel):
    resume_id: int
    user_id: int
    candidate_name: str
    candidate_email: str | None = None
    candidate_phone: str | None = None
    file_name: str
    skills: list = []
    experience: int | None = None
    education: str | None = None
    location: str | None = None
    views_count: int
    match_count: int
    created_at: datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------
# UPLOAD RESUME
# ------------------------------------------------------------------
@router.post("/upload")
async def upload_resume(
    user_id: int,
    candidate_name: str,
    file: UploadFile = File(...),
    candidate_email: str | None = None,
    candidate_phone: str | None = None,
    session: Session = Depends(get_db_session)
):
    """
    Upload resume → extract via LLM → store in DB → embed in ChromaDB
    """
    try:
        logger.info(f"[RESUME_UPLOAD_START] Starting resume upload for candidate: {candidate_name}")
        logger.info(f"[RESUME_UPLOAD_PARAMS] User ID: {user_id}, File: {file.filename}")
        
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)

        if not user:
            logger.error(f"[RESUME_UPLOAD_ERROR] User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        # --------------------------------------------------------------
        # Validate & save file
        # --------------------------------------------------------------
        logger.info(f"[FILE_VALIDATION_START] Validating file: {file.filename}")
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = {".pdf", ".docx", ".txt"}

        if file_ext not in allowed_extensions:
            logger.warning(f"[FILE_VALIDATION_ERROR] Unsupported file type: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PDF, DOCX, TXT"
            )

        timestamp = int(datetime.utcnow().timestamp())
        safe_name = candidate_name.replace(" ", "_")
        stored_file_name = f"{user_id}_{safe_name}_{timestamp}{file_ext}"
        file_path = UPLOAD_DIR / stored_file_name

        logger.info(f"[FILE_SAVE_START] Saving file to: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[FILE_SAVE_SUCCESS] File saved successfully at: {file_path}")

        # --------------------------------------------------------------
        # Parse resume (LLM-enhanced)
        # --------------------------------------------------------------
        logger.info(f"[LLM_PARSING_START] Starting LLM-based resume parsing...")
        parsing_service = get_resume_parsing_service()
        file_type = file_ext[1:]  # pdf / docx / txt

        parsed_data = parsing_service.parse_resume(str(file_path), file_type)
        resume_text = parsed_data["clean_text"]

        logger.info(f"[LLM_EXTRACTION_COMPLETE] LLM extracted and cleaned resume: {len(resume_text)} characters")
        logger.debug(f"[LLM_EXTRACTED_CONTENT] Cleaned resume content: {resume_text}")

        # 🔴 HARD VALIDATION (prevents empty embeddings forever)
        if not resume_text or len(resume_text.strip()) < 300:
            logger.error(f"[VALIDATION_ERROR] Resume text too short: {len(resume_text)} characters")
            raise HTTPException(
                status_code=400,
                detail="Resume could not be extracted properly. Please upload a readable resume."
            )

        # --------------------------------------------------------------
        # Store in DB (FULL CLEAN TEXT STORED)
        # --------------------------------------------------------------
        logger.info(f"[DB_STORAGE_START] Storing resume in local database...")
        resume = Resume(
            user_id=user_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            file_path=str(file_path),
            file_name=file.filename,
            file_size=file.size or 0,
            file_type=file_type,
            skills=json.dumps(parsed_data["skills"]),
            experience=parsed_data["experience_years"],
            education=parsed_data["education"],
            location=parsed_data["location"],
            summary=parsed_data["summary"],
            resume_text=resume_text,  # 🔥 CRITICAL
        )

        resume_repo = get_resume_repository(session)
        resume = resume_repo.create(resume)

        logger.info(f"[DB_STORAGE_SUCCESS] Resume stored in local DB - Resume ID: {resume.resume_id}")
        logger.info(f"[DB_STORAGE_METADATA] Skills: {parsed_data['skills']}, Experience: {parsed_data['experience_years']} years, Education: {parsed_data['education']}, Location: {parsed_data['location']}")

        # --------------------------------------------------------------
        # Embed into ChromaDB (DETERMINISTIC ID)
        # --------------------------------------------------------------
        chroma_id = f"resume_{resume.resume_id}"
        logger.info(f"[CHROMA_EMBEDDING_START] Starting ChromaDB embedding for Resume ID: {resume.resume_id}")

        try:
            logger.info(f"[CHROMA_EMBEDDING_TEXT] Text length for embedding: {len(resume_text)} characters")
            embeddings_service.add_document(
                collection_name=RESUME_COLLECTION,
                document_id=chroma_id,
                text=resume_text,
                metadata={
                    "resume_id": resume.resume_id,
                    "user_id": resume.user_id,
                    "candidate_name": candidate_name,
                    "skills": parsed_data["skills"],
                    "experience": parsed_data["experience_years"],
                    "location": parsed_data["location"],
                },
            )

            resume.chroma_collection_id = chroma_id
            resume_repo.update(resume.resume_id, resume)
            logger.info(f"[CHROMA_EMBEDDING_SUCCESS] Document embedded in ChromaDB - Collection ID: {chroma_id}")

        except Exception as e:
            logger.error(f"[CHROMA_EMBEDDING_ERROR] Embedding failed for Resume ID {resume.resume_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Resume uploaded but embedding failed. Please retry."
            )

        logger.info(f"[RESUME_UPLOAD_COMPLETE] Resume successfully uploaded & indexed - Candidate: {candidate_name}, Resume ID: {resume.resume_id}")

        return {
            "message": "Resume uploaded and indexed successfully",
            "resume_id": resume.resume_id,
            "skills": parsed_data["skills"],
            "experience": parsed_data["experience_years"],
            "education": parsed_data["education"],
            "location": parsed_data["location"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RESUME_UPLOAD_FATAL_ERROR] Unexpected error during resume upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error uploading resume")

# ------------------------------------------------------------------
# GET RESUMES BY USER
# ------------------------------------------------------------------
@router.get("/user/{user_id}")
async def get_user_resumes(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_db_session),
):
    try:
        resume_repo = get_resume_repository(session)
        resumes = resume_repo.get_by_user(user_id)
        return resumes[skip : skip + limit]
    except Exception:
        logger.error("Error fetching user resumes", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# ------------------------------------------------------------------
# GET SINGLE RESUME
# ------------------------------------------------------------------
@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    session: Session = Depends(get_db_session),
):
    try:
        resume_repo = get_resume_repository(session)
        resume = resume_repo.read(resume_id)

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        resume_repo.increment_views(resume_id)

        skills = []
        if resume.skills:
            try:
                skills = json.loads(resume.skills)
            except Exception:
                skills = resume.skills.split(",")

        return {
            **resume.dict(),
            "skills": skills,
        }

    except HTTPException:
        raise
    except Exception:
        logger.error("Error fetching resume", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
