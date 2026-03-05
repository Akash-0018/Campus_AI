"""Requirements collection agent for Campus AI"""
import logging
from typing import Optional, Tuple, Dict, Any
from sqlmodel import Session
from models.requirement import Requirement
from models.user import User
from database.requirement_repository import get_requirement_repository
from database.user_repository import get_user_repository
from datetime import datetime

logger = logging.getLogger(__name__)

# Singleton instance for requirements agent
_requirements_agent = None

class RequirementsAgent:
    """Agent for collecting user job requirements through conversation"""
    
    # Conversation phases with prompts and quick response options
    CONVERSATION_PHASES = {
        0: {
            "prompt": "What type of position are you looking to fill?",
            "field": "role",
            "quick_responses": ["Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "Frontend Developer", "Backend Developer"]
        },
        1: {
            "prompt": "What industry or domain expertise is important?",
            "field": "industry",
            "quick_responses": ["FinTech", "Healthcare", "E-commerce", "SaaS", "Gaming", "EdTech", "Custom"]
        },
        2: {
            "prompt": "How many years of experience are required?",
            "field": "experience_years",
            "quick_responses": ["0-2 years", "2-5 years", "5-10 years", "10+ years", "No preference"]
        },
        3: {
            "prompt": "What are the primary technical skills needed? (comma-separated)",
            "field": "skills",
            "quick_responses": ["Python, Django, PostgreSQL", "JavaScript, React, Node.js", "Java, Spring Boot, Microservices", "Go, Kubernetes, Cloud", "Custom"]
        },
        4: {
            "prompt": "What is your preferred team size?",
            "field": "team_size",
            "quick_responses": ["Solo/Individual", "2-5 people", "5-10 people", "10+ people", "No preference"]
        }
    }
    
    def __init__(self):
        """Initialize requirements agent"""
        logger.info(
            "[MULTI-AGENT-INIT] ✓ RequirementsAgent initialized | "
            "agent_type=requirements_collection | "
            f"conversation_phases_count={len(self.CONVERSATION_PHASES)}"
        )
    
    def get_greeting(self, user: User) -> str:
        """Generate personalized greeting for user"""
        first_name = user.full_name.split()[0] if user.full_name else "there"
        return f"👋 Hello {first_name}! I'm here to help you find the perfect candidate. Let's start by understanding what you're looking for."
    
    def get_phase_info(self, phase: int) -> Optional[Dict[str, Any]]:
        """Get phase information with prompt and quick responses"""
        if phase < len(self.CONVERSATION_PHASES):
            return self.CONVERSATION_PHASES[phase]
        return None
    def extract_requirements_from_free_text(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()

        extracted = {}

        # Role detection
        roles = [
            "backend developer", "frontend developer", "full stack developer",
            "software engineer", "data scientist", "devops engineer"
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
        for skill in ["python", "java", "react", "fastapi", "django", "aws", "docker"]:
            if skill in text_lower:
                skills.append(skill.title())
        if skills:
            extracted["skills"] = ", ".join(skills)

        # Location detection
        for city in ["bangalore", "chennai", "hyderabad", "remote"]:
            if city in text_lower:
                extracted["location"] = city.title()

        return extracted

    def process_user_input(
    self,
    session: Session,
    user_id: int,
    user_input: str
) -> Tuple[Requirement, str, Dict[str, Any]]:
        """
        Process user input and update requirement.

        Supports:
        - Greeting handling
        - Full free-text requirement input
        - Step-by-step phase-based flow
        """

        try:
            # --------------------------------------------------
            # Fetch user
            # --------------------------------------------------
            user_repo = get_user_repository(session)
            user = user_repo.read(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            req_repo = get_requirement_repository(session)
            user_input = user_input.strip()

            # --------------------------------------------------
            # Get or create active requirement
            # --------------------------------------------------
            requirement = req_repo.get_active_by_user(user_id)

            if not requirement:
                requirement = Requirement(
                    user_id=user_id,
                    requirement_count=0,
                    is_complete=False
                )
                req_repo.create(requirement)
                session.refresh(requirement)

            # --------------------------------------------------
            # Handle greetings (Hi / Hello / Hey)
            # --------------------------------------------------
            if user_input.lower() in {"hi", "hello", "hey"}:
                phase = self.get_phase_info(requirement.requirement_count)
                response = self.get_greeting(user) + "\n\n" + phase["prompt"]
                return requirement, response, phase

            # --------------------------------------------------
            # 🔥 NEW: Free-text requirement extraction
            # --------------------------------------------------
            extracted = self.extract_requirements_from_free_text(user_input)

            if extracted:
                logger.info(f"[AGENT_EXTRACTION] Extracted from free text: {extracted}")

                if "role" in extracted:
                    requirement.role = extracted["role"]
                if "experience_years" in extracted:
                    requirement.experience_years = extracted["experience_years"]
                if "skills" in extracted:
                    requirement.skills = extracted["skills"]
                if "location" in extracted:
                    requirement.location = extracted["location"]

                # If core fields exist → mark complete
                core_fields = ["role", "skills", "experience_years"]
                if all(getattr(requirement, f, None) for f in core_fields):
                    requirement.is_complete = True
                    requirement.requirement_count = len(self.CONVERSATION_PHASES)
                    requirement.updated_at = datetime.utcnow()

                    req_repo.update(requirement.requirement_id, requirement)
                    session.refresh(requirement)

                    response = (
                        "✅ Got it! I understand your full requirement.\n\n"
                        "Let me find the best matching candidates for you..."
                    )
                    return requirement, response, {}

            # --------------------------------------------------
            # Phase-based flow (fallback)
            # --------------------------------------------------
            current_phase = self.get_phase_info(requirement.requirement_count)

            if not current_phase:
                requirement.is_complete = True
                requirement.updated_at = datetime.utcnow()
                req_repo.update(requirement.requirement_id, requirement)
                session.refresh(requirement)

                response = "Perfect! I've collected all the information. Let me find the best candidates for you..."
                return requirement, response, {}

            # --------------------------------------------------
            # Store answer for current phase
            # --------------------------------------------------
            field_name = current_phase["field"]

            if field_name == "role":
                requirement.role = user_input
            elif field_name == "industry":
                requirement.industry = user_input
            elif field_name == "experience_years":
                requirement.experience_years = user_input
            elif field_name == "skills":
                requirement.skills = user_input
            elif field_name == "team_size":
                requirement.team_size = user_input

            # Move to next phase
            requirement.requirement_count += 1
            requirement.updated_at = datetime.utcnow()

            req_repo.update(requirement.requirement_id, requirement)
            session.refresh(requirement)

            # --------------------------------------------------
            # Check completion
            # --------------------------------------------------
            if requirement.requirement_count >= len(self.CONVERSATION_PHASES):
                requirement.is_complete = True
                req_repo.update(requirement.requirement_id, requirement)
                session.refresh(requirement)

                response = (
                    "🎯 Excellent! I've gathered all your requirements.\n\n"
                    "I'm now finding the best candidates for you..."
                )
                return requirement, response, {}

            # --------------------------------------------------
            # Ask next question
            # --------------------------------------------------
            next_phase = self.get_phase_info(requirement.requirement_count)
            response = next_phase["prompt"]

            logger.info(f"User {user_id} moved to phase {requirement.requirement_count}")
            return requirement, response, next_phase

        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            raise

def get_requirements_agent() -> RequirementsAgent:
    """Get requirements agent instance (singleton pattern)"""
    global _requirements_agent
    if _requirements_agent is None:
        _requirements_agent = RequirementsAgent()
    return _requirements_agent
