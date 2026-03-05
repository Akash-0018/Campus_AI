"""
Agent Router - Routes user requests to appropriate agents

Provides intelligent routing based on user intent detection.
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
import re

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Available agent types"""
    REQUIREMENTS_COLLECTION = "requirements_collection"
    RESUME_MATCHING = "resume_matching"
    USER_PROFILE = "user_profile"
    RECRUITMENT_COORDINATOR = "recruitment_coordinator"


class IntentDetector:
    """Detects user intent from messages"""
    
    # Intent patterns mapped to agent types
    INTENT_PATTERNS = {
        AgentType.REQUIREMENTS_COLLECTION: [
            r"(?i)(i\s+need|looking\s+for\s+(?!candidate|resume|resume)|hire|recruit|find\s+someone|position|role|job\s+(?!search))",
            r"(?i)(developer|engineer|designer|manager|analyst)\s+(?!profile|resume|candidate)",
        ],
        AgentType.RESUME_MATCHING: [
            r"(?i)(match|find\s+(?:resumes?|candidates?)|search\s+(?:resumes?|candidates?)|browse\s+(?:resumes?|candidates?)|filter|candidate|resume)",
            r"(?i)(best\s+fit|similar\s+(?:profile|candidate)|like|compare)",
        ],
        AgentType.USER_PROFILE: [
            r"(?i)(profile|account|settings|update|change|edit|my\s+info|information|preferences?|skill|experience|background)",
            r"(?i)(personal|recruiter|user\s+(?:info|profile|account))",
        ],
    }
    
    @classmethod
    def detect_intent(cls, message: str) -> AgentType:
        """
        Detect user intent from message
        
        Args:
            message: User message
            
        Returns:
            AgentType indicating which agent should handle this
        """
        message_lower = message.lower()
        
        # Score each agent based on pattern matches
        scores: Dict[AgentType, int] = {agent: 0 for agent in AgentType}
        
        for agent_type, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    scores[agent_type] += 1
        
        # Return agent with highest score (default to requirements collection)
        best_agent = max(scores, key=scores.get)
        
        if scores[best_agent] == 0:
            best_agent = AgentType.REQUIREMENTS_COLLECTION
        
        logger.info(
            f"[Router] Intent detection: '{message[:50]}...' → {best_agent.value} "
            f"(scores: {scores})"
        )
        return best_agent


class AgentRouter:
    """
    Routes user requests to appropriate agents
    
    Provides:
    - Intent detection
    - Agent selection
    - Conversation routing
    - Multi-agent orchestration
    """
    
    def __init__(self):
        """Initialize router"""
        self.intent_detector = IntentDetector()
        self.agent_handlers: Dict[AgentType, Any] = {}
        
        logger.info("[Router] Initialized agent router")
    
    def register_agent_handler(self, agent_type: AgentType, handler: Any) -> None:
        """
        Register an agent handler
        
        Args:
            agent_type: Type of agent
            handler: Agent handler instance
        """
        self.agent_handlers[agent_type] = handler
        logger.info(f"[Router] Registered handler for {agent_type.value}")
    
    def get_agent_handler(self, agent_type: AgentType) -> Optional[Any]:
        """
        Get handler for agent type
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Agent handler or None if not registered
        """
        return self.agent_handlers.get(agent_type)
    
    async def route_message(
        self,
        message: str,
        user_id: int,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_agent: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """
        Route message to appropriate agent
        
        Args:
            message: User message
            user_id: User ID
            session_id: Optional session ID
            metadata: Optional metadata
            force_agent: Force specific agent (override detection)
            
        Returns:
            Response dict with:
            - response: Agent response
            - agent: Agent that handled the request
            - session_id: Session ID
            - success: Boolean success flag
        """
        try:
            # Determine target agent
            if force_agent:
                target_agent = force_agent
                logger.info(f"[Router] Using forced agent: {target_agent.value}")
            else:
                target_agent = self.intent_detector.detect_intent(message)
            
            # Get agent handler
            handler = self.get_agent_handler(target_agent)
            if not handler:
                logger.error(f"[Router] No handler registered for {target_agent.value}")
                return {
                    "success": False,
                    "response": f"Agent {target_agent.value} not available",
                    "agent": None,
                    "session_id": session_id,
                    "error": "agent_not_available"
                }
            
            # Route to agent
            logger.info(f"[Router] Routing to {target_agent.value}")
            result = await handler.execute_prompt(
                prompt=message,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
            
            return {
                "success": result.get("success", True),
                "response": result.get("response", ""),
                "agent": target_agent.value,
                "session_id": result.get("session_id", session_id),
                **{k: v for k, v in result.items() 
                   if k not in ["success", "response", "session_id"]}
            }
            
        except Exception as e:
            logger.error(f"[Router] Error routing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "response": "Error processing your request",
                "agent": None,
                "session_id": session_id,
                "error": str(e)
            }
    
    def list_available_agents(self) -> List[Dict[str, str]]:
        """
        List all available agents
        
        Returns:
            List of agent info dicts
        """
        agents = []
        for agent_type, handler in self.agent_handlers.items():
            agents.append({
                "type": agent_type.value,
                "name": getattr(handler, "name", agent_type.value),
                "description": getattr(handler, "description", "")
            })
        
        return agents


# Global router instance
_router: Optional[AgentRouter] = None


def get_router() -> AgentRouter:
    """Get or create global router instance"""
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router


def initialize_router() -> AgentRouter:
    """Initialize and return router"""
    global _router
    _router = AgentRouter()
    logger.info("[Router] Agent router initialized")
    return _router
