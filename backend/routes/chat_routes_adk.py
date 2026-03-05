"""
ADK-powered chat routes - Parallel to existing routes

These routes use the new ADK-based RequirementsAgent for testing
while the old routes remain unchanged for backward compatibility.

Both can run in parallel during the migration phase.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional

from database.connection import get_db_session
from agents.requirements_agent_adk import get_requirements_agent
from services.matching_service import MatchingService
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-adk", tags=["chat-adk"])


class MessageRequest(BaseModel):
    """Chat message request"""
    message: str
    user_id: int
    session_id: Optional[str] = None


class Match(BaseModel):
    """Matched candidate"""
    user_id: int
    rank: int
    name: str
    email: Optional[str] = None
    skills: list = []
    match_score: float
    match_reason: str


class MessageResponse(BaseModel):
    """Chat response from ADK agent"""
    agent_response: str
    requirement_count: int
    is_complete: bool
    session_id: Optional[str] = None
    quick_responses: list[str] = []
    current_phase: Optional[str] = None
    matches: list[Match] = []
    adk_enabled: bool = True
    engine: str = "adk"


@router.post("/message", response_model=MessageResponse)
async def send_message_adk(
    request: MessageRequest,
    session: Session = Depends(get_db_session)
):
    """
    Send message to ADK-powered requirements agent
    
    This is the new ADK-based endpoint running in parallel with
    the old endpoint. Both can be used during migration phase.
    
    Flow:
    1. Get ADK requirements agent instance
    2. Execute prompt through ADK framework
    3. Handle response and get matches if complete
    4. Return response with session tracking
    """
    try:
        logger.info(f"[ADK Route] Processing message for user {request.user_id}")
        
        # Get ADK agent
        requirements_agent = get_requirements_agent()
        
        # Execute through ADK (async)
        result = await requirements_agent.execute_prompt(
            prompt=request.message,
            user_id=str(request.user_id),
            session_id=request.session_id,
            metadata={
                "user_id": request.user_id,
                "db_session": session
            }
        )
        
        if not result.get("success"):
            logger.warning(f"[ADK Route] Agent returned error: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail="Error processing message"
            )
        
        agent_response = result.get("response", "")
        
        # Get requirement data for response
        from database.requirement_repository import get_requirement_repository
        req_repo = get_requirement_repository(session)
        requirement = req_repo.get_active_by_user(request.user_id)
        
        requirement_count = requirement.requirement_count if requirement else 0
        is_complete = requirement.is_complete if requirement else False
        
        # Get matches if requirement is complete
        matches = []
        if is_complete and requirement:
            try:
                matching_service = MatchingService()
                matched = matching_service.get_matches(requirement)
                
                # Format matches
                matches = [
                    Match(
                        user_id=m.get("user_id"),
                        rank=m.get("rank", 0),
                        name=m.get("name", "Unknown"),
                        email=m.get("email"),
                        skills=m.get("skills", []),
                        match_score=m.get("match_score", 0),
                        match_reason=m.get("reason", "")
                    )
                    for m in matched
                ]
            except Exception as e:
                logger.error(f"[ADK Route] Error getting matches: {e}")
                matches = []
        
        # Get phase info for quick responses
        phase_info = result.get("phase_info", {})
        quick_responses = phase_info.get("quick_responses", [])
        current_phase = phase_info.get("prompt", "")
        
        logger.info(
            f"[ADK Route] Response sent: requirement_count={requirement_count}, "
            f"is_complete={is_complete}, matches={len(matches)}"
        )
        
        return MessageResponse(
            agent_response=agent_response,
            requirement_count=requirement_count,
            is_complete=is_complete,
            session_id=result.get("session_id", request.session_id),
            quick_responses=quick_responses,
            current_phase=current_phase,
            matches=matches,
            adk_enabled=True,
            engine="adk"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADK Route] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message"
        )


@router.get("/status/{user_id}")
async def get_status_adk(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Get requirement collection status for user"""
    try:
        from database.requirement_repository import get_requirement_repository
        req_repo = get_requirement_repository(session)
        requirement = req_repo.get_active_by_user(user_id)
        
        if not requirement:
            return {
                "user_id": user_id,
                "requirement_count": 0,
                "is_complete": False,
                "status": "no_requirement"
            }
        
        return {
            "user_id": user_id,
            "requirement_count": requirement.requirement_count,
            "is_complete": requirement.is_complete,
            "status": "complete" if requirement.is_complete else "in_progress",
            "requirement_id": requirement.requirement_id
        }
    except Exception as e:
        logger.error(f"[ADK Route] Error getting status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving status"
        )


@router.post("/reset/{user_id}")
async def reset_conversation_adk(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Reset conversation for a user (for testing)"""
    try:
        from database.requirement_repository import get_requirement_repository
        req_repo = get_requirement_repository(session)
        
        # Get active requirement
        requirement = req_repo.get_active_by_user(user_id)
        if requirement:
            requirement.requirement_count = 0
            requirement.is_complete = False
            requirement.role = None
            requirement.skills = None
            req_repo.update(requirement.requirement_id, requirement)
        
        logger.info(f"[ADK Route] Reset conversation for user {user_id}")
        
        return {
            "status": "success",
            "message": "Conversation reset",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"[ADK Route] Error resetting conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error resetting conversation"
        )
