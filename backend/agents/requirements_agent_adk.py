"""
RequirementsAgent - ADK Implementation

Agent for collecting job requirements through multi-phase conversation.
Now powered by Google's ADK framework with session management and guardrails.
"""
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from sqlmodel import Session

from agents.base_agent import BaseAgent
from models.requirement import Requirement
from models.user import User
from database.requirement_repository import get_requirement_repository
from database.user_repository import get_user_repository
from tools.registration import get_tool_registry
from tools.adk_tools import ResumeMatchingTool, EmbeddingsTool

logger = logging.getLogger(__name__)


class RequirementsAgent(BaseAgent):
    """
    Requirements collection agent powered by ADK
    
    Handles multi-phase conversation to collect job requirements
    from recruiters with option for free-text input.
    """
    
    # Conversation phases
    CONVERSATION_PHASES = {
        0: {
            "prompt": "What type of position are you looking to fill?",
            "field": "role",
            "quick_responses": [
                "Software Engineer", "Data Scientist", "Product Manager",
                "DevOps Engineer", "Frontend Developer", "Backend Developer"
            ]
        },
        1: {
            "prompt": "What industry or domain expertise is important?",
            "field": "industry",
            "quick_responses": [
                "FinTech", "Healthcare", "E-commerce", "SaaS", "Gaming", "EdTech"
            ]
        },
        2: {
            "prompt": "How many years of experience are required?",
            "field": "experience_years",
            "quick_responses": [
                "0-2 years", "2-5 years", "5-10 years", "10+ years", "No preference"
            ]
        },
        3: {
            "prompt": "What are the primary technical skills needed? (comma-separated)",
            "field": "skills",
            "quick_responses": [
                "Python, Django, PostgreSQL",
                "JavaScript, React, Node.js",
                "Java, Spring Boot, Microservices"
            ]
        },
        4: {
            "prompt": "What is your preferred team size or organizational structure?",
            "field": "team_size",
            "quick_responses": [
                "Solo/Individual", "2-5 people", "5-10 people", "10+ people"
            ]
        }
    }
    
    def __init__(self, session_service=None):
        """Initialize RequirementsAgent with ADK"""
        super().__init__(
            name="requirements_collector",
            description="Collects job requirements from recruiters",
            system_instruction=(
                "You are a helpful recruitment assistant. Your job is to collect "
                "job requirements from recruiters through a structured conversation. "
                "Be friendly, clear, and concise. Help the recruiter specify what "
                "they're looking for in a candidate."
            ),
            session_service=session_service,
            app_name="campus_ai"
        )
        
        # Initialize tools
        self.resume_matching_tool = ResumeMatchingTool()
        self.embeddings_tool = EmbeddingsTool()
        
        logger.info("[RequirementsAgent] Initialized with ADK framework")
    
    def get_greeting(self, user: User) -> str:
        """Generate personalized greeting for user"""
        first_name = user.full_name.split()[0] if user.full_name else "there"
        return (
            f"👋 Hello {first_name}! I'm here to help you find the perfect candidate. "
            f"Let's start by understanding what you're looking for."
        )
    
    def get_phase_info(self, phase: int) -> Optional[Dict[str, Any]]:
        """Get phase information with prompt and quick responses"""
        if phase < len(self.CONVERSATION_PHASES):
            return self.CONVERSATION_PHASES[phase]
        return None
    
    def extract_requirements_from_free_text(self, text: str) -> Dict[str, Any]:
        """Extract requirements from free-text user input"""
        text_lower = text.lower()
        extracted = {}
        
        # Role detection
        roles = [
            "backend developer", "frontend developer", "full stack developer",
            "software engineer", "data scientist", "devops engineer",
            "product manager", "qa engineer", "solutions architect"
        ]
        for role in roles:
            if role in text_lower:
                extracted["role"] = role.title()
                break
        
        # Experience detection
        import re
        exp_match = re.search(r'(\d+)\s*\+?\s*years?', text_lower)
        if exp_match:
            extracted["experience_years"] = exp_match.group(0)
        
        # Skills detection
        skills = []
        for skill in [
            "python", "java", "javascript", "react", "vue", "angular",
            "fastapi", "django", "spring", "nodejs", "aws", "gcp",
            "docker", "kubernetes", "postgres", "mongodb", "git"
        ]:
            if skill in text_lower:
                skills.append(skill.title())
        if skills:
            extracted["skills"] = ", ".join(skills)
        
        # Industry detection
        industries = [
            "fintech", "healthcare", "ecommerce", "e-commerce", "saas",
            "gaming", "edtech", "education", "retail", "insurance"
        ]
        for industry in industries:
            if industry in text_lower:
                extracted["industry"] = industry.title()
                break
        
        return extracted
    
    async def _process_input(
        self,
        prompt: str,
        session,
        tools=None,
        metadata=None
    ) -> Dict[str, Any]:
        """
        Process user input through ADK agent
        
        Args:
            prompt: User message
            session: ADK session
            tools: Available tools
            metadata: Additional metadata
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Extract user_id from metadata
            user_id = metadata.get("user_id") if metadata else None
            if not user_id:
                return {
                    "success": False,
                    "response": "Error: User not identified",
                    "metadata": {"error": "missing_user_id"}
                }
            
            # DB access is mandatory for requirements collection state.
            db_session = metadata.get("db_session") if metadata else None
            if db_session is None:
                return {
                    "success": False,
                    "response": "Error: Database session not available",
                    "metadata": {"error": "missing_db_session"}
                }
            
            # Get repositories
            user_repo = get_user_repository(db_session)
            req_repo = get_requirement_repository(db_session)
            
            # Fetch user
            user = user_repo.read(user_id)
            if not user:
                return {
                    "success": False,
                    "response": "Error: User not found",
                    "metadata": {"error": "user_not_found"}
                }
            
            # Get or create active requirement
            requirement = req_repo.get_active_by_user(user_id)
            if not requirement:
                requirement = Requirement(
                    user_id=user_id,
                    requirement_count=0,
                    is_complete=False
                )
                req_repo.create(requirement)
                db_session.refresh(requirement)  # type: ignore
            
            # Handle greeting
            if prompt.lower() in {"hi", "hello", "hey", "start"}:
                phase = self.get_phase_info(requirement.requirement_count)
                if phase:
                    response = self.get_greeting(user) + "\n\n" + phase["prompt"]
                else:
                    response = self.get_greeting(user)
                
                return {
                    "response": response,
                    "requirement_count": requirement.requirement_count,
                    "is_complete": requirement.is_complete,
                    "phase_info": phase,
                    "metadata": {"greeting": True}
                }
            
            # Try free-text extraction first
            extracted = self.extract_requirements_from_free_text(prompt)
            
            if extracted:
                logger.info(f"[RequirementsAgent] Extracted from free text: {extracted}")
                
                # Update requirement with extracted fields
                if "role" in extracted:
                    requirement.role = extracted["role"]
                if "experience_years" in extracted:
                    requirement.experience_years = extracted["experience_years"]
                if "skills" in extracted:
                    requirement.skills = extracted["skills"]
                if "industry" in extracted:
                    requirement.industry = extracted["industry"]
                
                # Check if complete (has core fields)
                core_fields = ["role", "skills", "experience_years"]
                if all(getattr(requirement, f, None) for f in core_fields):
                    requirement.is_complete = True
                    requirement.requirement_count = len(self.CONVERSATION_PHASES)
                    requirement.updated_at = datetime.utcnow()
                    
                    req_repo.update(requirement.requirement_id, requirement)
                    db_session.refresh(requirement)  # type: ignore
                    
                    response = (
                        "✅ Got it! I understand your full requirement.\n\n"
                        "Let me find the best matching candidates for you..."
                    )
                    
                    return {
                        "response": response,
                        "requirement_count": requirement.requirement_count,
                        "is_complete": requirement.is_complete,
                        "shortcut": True,
                        "metadata": {"free_text_complete": True}
                    }
            
            # Phase-based flow (standard progression)
            current_phase = self.get_phase_info(requirement.requirement_count)
            
            if not current_phase:
                # All phases complete
                requirement.is_complete = True
                requirement.updated_at = datetime.utcnow()
                req_repo.update(requirement.requirement_id, requirement)
                db_session.refresh(requirement)  # type: ignore
                
                response = (
                    "🎯 Perfect! I've collected all the information. "
                    "Let me find the best candidates for you..."
                )
                
                return {
                    "response": response,
                    "requirement_count": requirement.requirement_count,
                    "is_complete": True,
                    "metadata": {"all_phases_complete": True}
                }
            
            # Store answer for current phase
            field_name = current_phase["field"]
            
            if field_name == "role":
                requirement.role = prompt
            elif field_name == "industry":
                requirement.industry = prompt
            elif field_name == "experience_years":
                requirement.experience_years = prompt
            elif field_name == "skills":
                requirement.skills = prompt
            elif field_name == "team_size":
                requirement.team_size = prompt
            
            # Move to next phase
            requirement.requirement_count += 1
            requirement.updated_at = datetime.utcnow()
            
            req_repo.update(requirement.requirement_id, requirement)
            db_session.refresh(requirement)  # type: ignore
            
            # Check if now complete
            if requirement.requirement_count >= len(self.CONVERSATION_PHASES):
                requirement.is_complete = True
                req_repo.update(requirement.requirement_id, requirement)
                db_session.refresh(requirement)  # type: ignore
                
                response = (
                    "🎯 Excellent! I've gathered all your requirements.\n\n"
                    "I'm now finding the best candidates for you..."
                )
                
                return {
                    "response": response,
                    "requirement_count": requirement.requirement_count,
                    "is_complete": True,
                    "metadata": {"phase_complete": True}
                }
            
            # Ask next question
            next_phase = self.get_phase_info(requirement.requirement_count)
            response = next_phase["prompt"] if next_phase else "Thank you!"
            
            logger.info(f"[RequirementsAgent] User {user_id} advanced to phase {requirement.requirement_count}")
            
            return {
                "response": response,
                "requirement_count": requirement.requirement_count,
                "is_complete": requirement.is_complete,
                "phase_info": next_phase,
                "quick_responses": next_phase.get("quick_responses", []) if next_phase else [],
                "metadata": {"phase_progressed": True}
            }
        
        except Exception as e:
            logger.error(f"[RequirementsAgent] Error processing input: {e}", exc_info=True)
            return {
                "success": False,
                "response": "An error occurred. Please try again.",
                "metadata": {"error": str(e)}
            }
    
    async def process_user_input(
        self,
        user_id: int,
        user_input: str,
        session_id: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> Tuple[Requirement, str, Dict[str, Any]]:
        """
        Process user input (wrapper for backward compatibility)
        
        Args:
            user_id: User ID
            user_input: User message
            session_id: Optional ADK session ID
            db_session: Database session for DB operations
        
        Returns:
            Tuple of (requirement, response_text, phase_info)
        """
        # Execute through ADK with metadata
        result = await self.execute_prompt(
            prompt=user_input,
            user_id=str(user_id),
            session_id=session_id,
            metadata={"user_id": user_id, "db_session": db_session}
        )
        
        if not result.get("success"):
            return None, result.get("response", "Error processing"), {}
        
        # For backward compatibility, fetch and return the requirement
        if db_session:
            req_repo = get_requirement_repository(db_session)
            requirement = req_repo.get_active_by_user(user_id)
        else:
            requirement = None
        
        return (
            requirement,
            result.get("response", ""),
            result.get("phase_info", {})
        )


# Singleton instance
_requirements_agent = None


def get_requirements_agent(session_service=None) -> RequirementsAgent:
    """Get or create RequirementsAgent instance"""
    global _requirements_agent
    if _requirements_agent is None:
        _requirements_agent = RequirementsAgent(session_service=session_service)
    return _requirements_agent
