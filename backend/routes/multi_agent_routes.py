"""
Multi-Agent Routes - API endpoints for multi-agent functionality

Provides:
- Agent routing
- Multi-turn conversations
- Agent discovery
- Status tracking
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session

from agents.agent_router import AgentRouter, AgentType, initialize_router
from agents.requirements_agent_adk import get_requirements_agent
from agents.resume_matching_agent_adk import get_resume_matching_agent
from agents.user_profile_agent_adk import get_user_profile_agent
from agents.recruitment_coordinator_agent_adk import get_recruitment_coordinator_agent
from database.connection import get_db_session

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/multi-agent", tags=["multi-agent"])

# Global router instance
_multi_agent_router: Optional[AgentRouter] = None


def get_multi_agent_router() -> AgentRouter:
    """Get initialized multi-agent router"""
    global _multi_agent_router
    if _multi_agent_router is None:
        _multi_agent_router = initialize_router()
        _initialize_agents(_multi_agent_router)
    return _multi_agent_router


def _initialize_agents(router: AgentRouter) -> None:
    """Initialize and register all agents with router"""
    try:
        logger.info("[MULTI-AGENT-ORCHESTRATION] Starting agent registration process")
        
        # Register all agents
        router.register_agent_handler(
            AgentType.REQUIREMENTS_COLLECTION,
            get_requirements_agent()
        )
        logger.debug("[MULTI-AGENT-ORCHESTRATION] ✓ RequirementsAgent registered")
        
        router.register_agent_handler(
            AgentType.RESUME_MATCHING,
            get_resume_matching_agent()
        )
        logger.debug("[MULTI-AGENT-ORCHESTRATION] ✓ ResumeMatchingAgent registered")
        
        router.register_agent_handler(
            AgentType.USER_PROFILE,
            get_user_profile_agent()
        )
        logger.debug("[MULTI-AGENT-ORCHESTRATION] ✓ UserProfileAgent registered")
        
        router.register_agent_handler(
            AgentType.RECRUITMENT_COORDINATOR,
            get_recruitment_coordinator_agent()
        )
        logger.debug("[MULTI-AGENT-ORCHESTRATION] ✓ RecruitmentCoordinatorAgent registered")
        
        logger.info(
            "[MULTI-AGENT-ORCHESTRATION] ✓ All agents initialized and registered | "
            "agent_count=4 | orchestration_status=ready"
        )
        
    except Exception as e:
        logger.error(
            f"[MULTI-AGENT-ORCHESTRATION] ✗ Error initializing agents: {str(e)} | "
            f"orchestration_status=failed",
            exc_info=True
        )


# ===== Request/Response Models =====

class MultiAgentMessageRequest(BaseModel):
    """Request for multi-agent message endpoint"""
    message: str
    user_id: int
    session_id: Optional[str] = None
    force_agent: Optional[str] = None


class AgentResponse(BaseModel):
    """Response from agent"""
    agent: str
    response: str
    session_id: Optional[str] = None
    success: bool = True
    metadata: Optional[dict] = None


class MultiAgentStatusResponse(BaseModel):
    """Status response"""
    user_id: int
    session_id: Optional[str] = None
    current_agent: Optional[str] = None
    message: str


class AgentInfoResponse(BaseModel):
    """Agent information"""
    type: str
    name: str
    description: str


# ===== Endpoints =====

@router.post("/message", response_model=AgentResponse)
async def multi_agent_message(
    request: MultiAgentMessageRequest,
    db_session: Session = Depends(get_db_session)
) -> dict:
    """
    Send message to multi-agent router
    
    Intelligent routing based on user intent detection.
    Automatically selects appropriate agent or forces specific agent.
    
    Args:
        request: Message request with user_id, message, optional session_id
        
    Returns:
        AgentResponse with agent response and metadata
    """
    try:
        # Get router
        ma_router = get_multi_agent_router()
        
        # Validate input
        if not request.message or len(request.message) > 500:
            raise HTTPException(
                status_code=400,
                detail="Message must be 1-500 characters"
            )
        
        # Parse force_agent if provided
        force_agent = None
        if request.force_agent:
            try:
                force_agent = AgentType(request.force_agent)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid agent type: {request.force_agent}"
                )
        
        logger.info(
            f"[AGENT-COORDINATION] Message received | "
            f"user_id={request.user_id} | "
            f"session_id={request.session_id or 'new'} | "
            f"message_preview={request.message[:50]}... | "
            f"force_agent={force_agent.value if force_agent else 'auto_detect'}"
        )
        logger.debug(f"[AGENT-COORDINATION] Full message: {request.message}")
        
        # Route message
        logger.info(f"[AGENT-COORDINATION] Delegating to router for agent selection")
        result = await ma_router.route_message(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            force_agent=force_agent,
            metadata={"user_id": request.user_id, "db_session": db_session}
        )
        
        logger.info(
            f"[AGENT-COORDINATION] ✓ Agent execution complete | "
            f"user_id={request.user_id} | "
            f"selected_agent={result.get('agent', 'unknown')} | "
            f"response_length={len(result.get('response', ''))} | "
            f"coordination_status=success"
        )
        
        return {
            "agent": result.get("agent", "unknown"),
            "response": result.get("response", ""),
            "session_id": result.get("session_id"),
            "success": result.get("success", True),
            "metadata": {
                **result.get("metadata", {}),
                "engine": "adk"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Error in multi-agent routing | "
            f"user_id={request.user_id} | "
            f"error={str(e)} | "
            f"coordination_status=failed",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error processing message")


@router.get("/agents", response_model=list[AgentInfoResponse])
async def list_agents() -> list:
    """
    List all available agents
    
    Returns:
        List of available agent information
    """
    try:
        ma_router = get_multi_agent_router()
        agents = ma_router.list_available_agents()
        
        logger.info(
            f"[AGENT-COORDINATION] ✓ Listed available agents | "
            f"agent_count={len(agents)} | "
            f"agents={[a['type'] for a in agents]}"
        )
        
        return agents
        
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Error listing agents | "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error listing agents")


@router.post("/route/{agent_type}")
async def route_to_agent(
    agent_type: str,
    request: MultiAgentMessageRequest,
    db_session: Session = Depends(get_db_session)
) -> dict:
    """
    Route message to specific agent
    
    Bypasses intent detection and sends directly to specified agent.
    
    Args:
        agent_type: Type of agent (requirements_collection, resume_matching, etc.)
        request: Message request
        
    Returns:
        Agent response
    """
    try:
        # Validate agent type
        try:
            target_agent = AgentType(agent_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent type: {agent_type}. "
                       f"Valid types: {', '.join([a.value for a in AgentType])}"
            )
        
        logger.info(
            f"[AGENT-COORDINATION] Direct agent routing | "
            f"user_id={request.user_id} | "
            f"target_agent={agent_type} | "
            f"message_preview={request.message[:50]}..."
        )
        
        # Get router and route
        ma_router = get_multi_agent_router()
        result = await ma_router.route_message(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            force_agent=target_agent,
            metadata={"user_id": request.user_id, "db_session": db_session}
        )
        
        logger.info(
            f"[AGENT-COORDINATION] ✓ Direct routing complete | "
            f"user_id={request.user_id} | "
            f"target_agent={agent_type} | "
            f"response_length={len(result.get('response', ''))}"
        )
        
        return {
            "agent": result.get("agent", "unknown"),
            "response": result.get("response", ""),
            "session_id": result.get("session_id"),
            "success": result.get("success", True),
            "metadata": {
                **result.get("metadata", {}),
                "engine": "adk"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Error routing to {agent_type} | "
            f"user_id={request.user_id} | "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error processing request")


@router.post("/detect-intent")
async def detect_intent(request: MultiAgentMessageRequest) -> dict:
    """
    Detect user intent without executing
    
    Returns what agent would handle the message.
    
    Args:
        request: Message request
        
    Returns:
        Detected agent type and confidence
    """
    try:
        from agents.agent_router import IntentDetector
        
        detected = IntentDetector.detect_intent(request.message)
        
        logger.info(f"[Multi-Agent Routes] Detected intent: {detected.value}")
        
        return {
            "detected_agent": detected.value,
            "message": f"This message would be routed to {detected.value}",
            "confidence": "high"
        }
        
    except Exception as e:
        logger.error(f"[Multi-Agent Routes] Error detecting intent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error detecting intent")


@router.get("/workflow/status/{user_id}")
async def get_workflow_status(user_id: int) -> dict:
    """
    Get workflow status for user
    
    Returns current recruitment workflow status.
    
    Args:
        user_id: User ID
        
    Returns:
        Workflow status information
    """
    try:
        # Get coordinator to check workflow status
        coordinator = get_recruitment_coordinator_agent()
        
        if user_id not in coordinator.workflows:
            logger.info(
                f"[AGENT-COORDINATION] Workflow status requested | "
                f"user_id={user_id} | "
                f"workflow_status=not_found"
            )
            return {
                "user_id": user_id,
                "status": "no_workflow",
                "message": "No active workflow for this user"
            }
        
        workflow = coordinator.workflows[user_id]
        
        logger.info(
            f"[AGENT-COORDINATION] ✓ Workflow status retrieved | "
            f"user_id={user_id} | "
            f"workflow_stage={workflow['stage']} | "
            f"candidate_count={len(workflow['candidates'])}"
        )
        
        return {
            "user_id": user_id,
            "current_stage": workflow["stage"],
            "has_requirements": workflow["requirements"] is not None,
            "candidate_count": len(workflow["candidates"]),
            "selected_candidate": workflow.get("selected_candidate"),
            "interview_status": workflow.get("interview_status", {})
        }
        
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Error getting workflow status | "
            f"user_id={user_id} | "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error getting status")


@router.post("/workflow/reset/{user_id}")
async def reset_workflow(user_id: int) -> dict:
    """
    Reset workflow for user
    
    Clears all workflow state and starts fresh.
    
    Args:
        user_id: User ID
        
    Returns:
        Confirmation message
    """
    try:
        coordinator = get_recruitment_coordinator_agent()
        
        if user_id in coordinator.workflows:
            del coordinator.workflows[user_id]
            logger.info(
                f"[AGENT-COORDINATION] ✓ Workflow reset | "
                f"user_id={user_id} | "
                f"action=workflow_cleared"
            )
        else:
            logger.info(
                f"[AGENT-COORDINATION] Workflow reset requested | "
                f"user_id={user_id} | "
                f"workflow_status=not_found"
            )
        
        return {
            "success": True,
            "message": f"Workflow reset for user {user_id}",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Error resetting workflow | "
            f"user_id={user_id} | "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error resetting workflow")


@router.get("/health")
async def health_check() -> dict:
    """
    Health check for multi-agent system
    
    Returns:
        Health status and agent availability
    """
    try:
        ma_router = get_multi_agent_router()
        agents = ma_router.list_available_agents()
        
        logger.info(
            f"[AGENT-COORDINATION] ✓ Health check successful | "
            f"agents_available={len(agents)} | "
            f"status=healthy"
        )
        
        return {
            "status": "healthy",
            "agents_available": len(agents),
            "agents": [a["type"] for a in agents],
            "router_initialized": True
        }
        
    except Exception as e:
        logger.error(
            f"[AGENT-COORDINATION] ✗ Health check failed | "
            f"error={str(e)} | "
            f"status=unhealthy",
            exc_info=True
        )
        return {
            "status": "unhealthy",
            "agents_available": 0,
            "error": str(e)
        }
