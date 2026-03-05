"""
BaseAgent - ADK Framework Wrapper

Wraps Google's ADK Agent with session management, tool orchestration,
and guardrails enforcement.
"""
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid
from abc import ABC, abstractmethod

try:
    from google.adk.agents import Agent
    from google.adk.sessions import Session, InMemorySessionService
    from google.adk.runners import Runner
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("[BaseAgent] ADK not available - ensure google-adk is installed")

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all ADK agents with session management
    
    Provides:
    - Session management
    - Tool registration & execution
    - Guardrails enforcement
    - Error handling
    - Response formatting
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        system_instruction: str = "",
        session_service: Optional['InMemorySessionService'] = None,
        app_name: str = "campus_ai"
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name
            description: Agent description
            system_instruction: System prompt for the agent
            session_service: Optional custom session service
            app_name: Application name for session management
        """
        if not ADK_AVAILABLE:
            raise RuntimeError(
                "ADK not installed. Install with: pip install google-adk"
            )
        
        self.name = name
        self.description = description
        self.app_name = app_name
        self.system_instruction = system_instruction
        
        # Initialize session service
        self.session_service = session_service or InMemorySessionService()
        
        # Create ADK agent
        # Note: model parameter expects string name, not GenerativeModel object
        # system_instruction is passed but stored on BaseAgent for reference
        self.agent = Agent(
            name=name,
            description=description,
            model="gemini-2.0-flash"
        )
        
        logger.info(f"[BaseAgent] Initialized agent: {name}")
    
    async def execute_prompt(
        self,
        prompt: str,
        user_id: str,
        session_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt through the ADK agent
        
        Args:
            prompt: The user prompt/message
            user_id: User identifier for session isolation
            session_id: Optional existing session ID
            tools: Optional list of registered tools
            metadata: Optional metadata to include
        
        Returns:
            Response dict with:
            - response: Agent response text
            - session_id: Session ID for continuity
            - metadata: Response metadata
            - success: Boolean success flag
            - timestamp: Execution timestamp
        """
        try:
            # Get or create session
            if session_id:
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
            else:
                session = None
            
            if not session:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id
                )
                logger.info(f"[BaseAgent] Created new session: {session.id} for user: {user_id}")
            else:
                logger.info(f"[BaseAgent] Resumed session: {session.id} for user: {user_id}")
            
            # Add guardrails check
            if not self._validate_input(prompt):
                return {
                    "success": False,
                    "response": "Invalid input detected. Please check your message.",
                    "session_id": session.id,
                    "error": "input_validation_failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Call the abstract method for agent-specific processing
            if metadata is None:
                metadata = {}
            if "user_id" not in metadata:
                metadata["user_id"] = user_id
            
            agent_result = await self._process_input(
                prompt=prompt,
                session=session,
                tools=tools,
                metadata=metadata
            )
            
            success = agent_result.get("success", True)
            return {
                "success": success,
                "response": agent_result.get("response", ""),
                "session_id": session.id,
                "metadata": agent_result.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat(),
                **agent_result  # Merge additional fields
            }
        
        except Exception as e:
            logger.error(f"[BaseAgent] Error executing prompt: {e}", exc_info=True)
            return {
                "success": False,
                "response": "An error occurred processing your request. Please try again.",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @abstractmethod
    async def _process_input(
        self,
        prompt: str,
        session: 'Session',
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process input - implement in subclass
        
        Args:
            prompt: User prompt
            session: ADK session
            tools: Registered tools
            metadata: Optional metadata
        
        Returns:
            Dict with agent response and metadata
        """
        pass
    
    def _validate_input(self, prompt: str) -> bool:
        """
        Validate input against guardrails
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check length
            if len(prompt) < 1 or len(prompt) > 500:
                return False
            
            # Check for SQL injection patterns
            dangerous_patterns = [
                "DROP TABLE", "DELETE FROM", "INSERT INTO",
                "--", ";", "/*", "*/"
            ]
            
            prompt_upper = prompt.upper()
            for pattern in dangerous_patterns:
                if pattern in prompt_upper:
                    logger.warning(f"[BaseAgent] Detected dangerous pattern: {pattern}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"[BaseAgent] Input validation error: {e}")
            return False
    
    async def close_session(self, session_id: str, user_id: str) -> bool:
        """
        Close a session and cleanup resources
        
        Args:
            session_id: Session to close
            user_id: User ID for isolation
        
        Returns:
            True if successful
        """
        try:
            # ADK handles session cleanup
            logger.info(f"[BaseAgent] Closing session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"[BaseAgent] Error closing session: {e}")
            return False


class SimpleAgent(BaseAgent):
    """
    Simple agent implementation for testing/fallback
    
    Just returns echo responses
    """
    
    async def _process_input(
        self,
        prompt: str,
        session: 'Session',
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple agent just echoes the message"""
        return {
            "response": f"Received: {prompt}",
            "metadata": {"agent_type": "simple", "session_id": session.id}
        }
