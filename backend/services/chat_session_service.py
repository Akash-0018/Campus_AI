"""Chat Session Service for managing conversation state and phases"""
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatSession:
    """Manages a single chat session with conversation history and requirement tracking"""
    
    def __init__(self, session_id: str, user_id: int):
        self.session_id = session_id
        self.user_id = user_id
        self.messages: List[Dict[str, Any]] = []
        self.requirements = {
            "role": None,
            "industry": None,
            "experience": None,
            "skills": [],
            "budget": None,
            "location": None,
            "availability": None,
        }
        self.current_phase = 1
        self.phases = [
            "Ask about role/position type",
            "Ask about required experience",
            "Ask about required skills",
            "Ask about other preferences (budget, location, availability)",
            "Summarize and prepare search"
        ]
        self.phase_complete = False
        self.created_at = datetime.now()
    
    def add_message(self, message_type: str, content: str, agent_response: Optional[str] = None):
        """Add a message to conversation history"""
        msg = {
            "type": message_type,  # "user" or "agent"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agent_response": agent_response
        }
        self.messages.append(msg)
    
    def get_conversation_text(self) -> str:
        """Get formatted conversation text for LLM analysis"""
        text = ""
        for msg in self.messages:
            prefix = "User" if msg["type"] == "user" else "Agent"
            text += f"{prefix}: {msg['content']}\n"
        return text
    
    def is_complete(self) -> bool:
        """Check if all requirements are gathered"""
        required_fields = ["role", "experience", "skills"]
        return all(self.requirements.get(field) for field in required_fields)
    
    def get_completion_percentage(self) -> int:
        """Get percentage of requirements completed"""
        required_fields = ["role", "experience", "skills"]
        completed = sum(1 for field in required_fields if self.requirements.get(field))
        return int((completed / len(required_fields)) * 100)


class ChatSessionService:
    """Service for managing chat sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, session_id: str, user_id: int) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(session_id, user_id)
        self.sessions[session_id] = session
        logger.info(f"Created chat session {session_id} for user {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get existing chat session"""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str, user_id: int) -> ChatSession:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id, user_id)
        return session
    
    def update_requirements(self, session_id: str, requirements: Dict[str, Any]):
        """Update session requirements"""
        session = self.get_session(session_id)
        if session:
            session.requirements.update(requirements)
    
    def get_quick_responses(self, current_phase: int, requirements: Dict[str, Any]) -> List[str]:
        """Generate quick response suggestions based on current phase"""
        
        responses = {
            1: [
                "Senior Backend Engineer",
                "Full-Stack Developer",
                "DevOps/Infrastructure Engineer",
                "Data Scientist",
                "Frontend Engineer"
            ],
            2: [
                "3-5 years experience",
                "5-8 years experience",
                "8+ years experience",
                "10+ years experience",
                "Entry level (0-2 years)"
            ],
            3: [
                "Python, JavaScript, TypeScript",
                "React, Node.js, PostgreSQL",
                "AWS, Docker, Kubernetes",
                "Machine Learning & AI",
                "Cloud Architecture & Security"
            ],
            4: [
                "Remote",
                "Hybrid",
                "On-site",
                "Willing to relocate",
                "Flexible"
            ]
        }
        
        return responses.get(current_phase, [])


# Singleton instance
chat_session_service = ChatSessionService()
