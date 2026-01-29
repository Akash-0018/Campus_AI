"""Chat routes with requirements agent and RAG matching"""
import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database.connection import get_db_session
from agents.requirements_agent import get_requirements_agent
from services.matching_service import MatchingService
from models.user import User
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Get requirements agent
requirements_agent = get_requirements_agent()


class MessageRequest(BaseModel):
    """Chat message request"""
    message: str
    user_id: int
    session_id: str = None


class Match(BaseModel):
    """Matched candidate"""
    user_id: int
    rank: int
    name: str
    email: str = None
    phone: Optional[str] = None
    skills: list = []
    match_score: float
    match_reason: str
    profile_image_url: Optional[str] = None
    is_verified: bool = False


class MessageResponse(BaseModel):
    """Chat response using requirements agent logic"""
    agent_response: str
    requirement_count: int
    is_complete: bool
    quick_responses: list[str] = []
    current_phase: str = None
    matches: list[Match] = []


@router.post("/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    session: Session = Depends(get_db_session)
):
    """
    Send message to requirements agent and get response
    
    Flow:
    1. Use RequirementsAgent to process user input
    2. Extract requirements (step-by-step OR free-text shortcut)
    3. If is_complete === true, find matching candidates using RAG
    4. Return agent response with matches and quick responses
    """
    
    try:
        # Validate user exists
        user = session.exec(select(User).where(User.user_id == request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Step 1: Process user input through requirements agent
        requirement, agent_response, phase_info = requirements_agent.process_user_input(
            session=session,
            user_id=request.user_id,
            user_input=request.message
        )
        
        logger.info(
            f"Requirement phase {requirement.requirement_count}, "
            f"Complete: {requirement.is_complete}, "
            f"Role: {requirement.role}, "
            f"Skills: {requirement.skills}"
        )
        
        # Step 2: Get quick responses from phase info
        quick_responses = phase_info.get("quick_responses", []) if phase_info else []
        
        # Step 3: If requirements complete, find matching candidates
        matches = []
        current_phase = None
        
        if requirement.is_complete:
            current_phase = "Searching for candidates..."
            try:
                # Build requirements dict for matching service
                requirements_dict = {
                    "role": requirement.role,
                    "industry": requirement.industry,
                    "experience_years": requirement.experience_years,
                    "skills": requirement.skills,
                    "team_size": requirement.team_size,
                    "location": requirement.location,
                }
                
                # Use matching service to find candidates
                matching_service = MatchingService(session)
                candidates = matching_service.find_candidates_rag(requirements_dict, top_k=2)
                
                # Format matches for response
                matches = [
                    Match(
                        user_id=candidate.get("user_id"),
                        rank=candidate.get("rank", idx + 1),
                        name=candidate.get("name", "Unknown"),
                        email=candidate.get("email"),
                        phone=candidate.get("phone"),
                        skills=candidate.get("skills", []),
                        match_score=candidate.get("match_score", 0.0),
                        match_reason=candidate.get("match_reason", "Good match"),
                        profile_image_url=candidate.get("profile_image_url"),
                        is_verified=candidate.get("is_verified", False)
                    )
                    for idx, candidate in enumerate(candidates, 1)
                ]
                
                logger.info(f"Found {len(matches)} matching candidates")
                current_phase = f"Found {len(matches)} candidate(s)"
                
            except Exception as e:
                logger.warning(f"Could not find matches: {e}")
                current_phase = "Ready to search"
        else:
            phase_num = requirement.requirement_count
            phase_names = {
                0: "Gathering role information",
                1: "Gathering industry preferences",
                2: "Gathering experience requirements",
                3: "Gathering skill requirements",
                4: "Gathering team size preferences"
            }
            current_phase = phase_names.get(phase_num, "Gathering requirements")
        
        return MessageResponse(
            agent_response=agent_response,
            requirement_count=requirement.requirement_count,
            is_complete=requirement.is_complete,
            quick_responses=quick_responses,
            current_phase=current_phase,
            matches=matches
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/phases")
async def get_conversation_phases():
    """Get the conversation flow phases"""
    
    phases = requirements_agent.CONVERSATION_PHASES
    return {
        "phases": [
            {
                "number": num,
                "prompt": phase["prompt"],
                "field": phase["field"],
                "quick_responses": phase["quick_responses"]
            }
            for num, phase in phases.items()
        ]
    }

