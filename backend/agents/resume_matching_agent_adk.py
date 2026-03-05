"""
Resume Matching Agent - Finds matching resumes for requirements

Powered by ADK framework, uses ChromaDB for semantic search.
"""
import logging
from typing import Optional, Dict, Any, List

from agents.base_agent import BaseAgent
from tools.adk_tools import ResumeMatchingTool

logger = logging.getLogger(__name__)


class ResumeMatchingAgent(BaseAgent):
    """
    Resume Matching Agent
    
    Finds resumes that match job requirements using semantic search.
    
    Features:
    - Semantic resume search
    - Score-based ranking
    - Result filtering
    - Multi-turn refinement
    """
    
    def __init__(self, db_session: Optional[Any] = None):
        """
        Initialize resume matching agent
        
        Args:
            db_session: Optional database session
        """
        super().__init__(
            name="resume_matching_agent",
            description="Finds matching resumes for job requirements",
            system_instruction=(
                "You are a resume matching expert. Help find the best resumes "
                "matching the given job requirements. Ask clarifying questions "
                "about the job to improve match quality."
            )
        )
        
        self.db_session = db_session
        self.conversation_state = {}
        self.resume_matching_tool = ResumeMatchingTool()
        
        logger.info("[ResumeMatchingAgent] Initialized")
    
    async def _process_input(
        self,
        prompt: str,
        session: Any,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process input through agent
        
        Args:
            prompt: User input
            session: ADK session
            tools: Available tools
            metadata: Metadata (includes user_id, db_session)
            
        Returns:
            Agent response dict
        """
        try:
            user_id = metadata.get("user_id") if metadata else None
            
            # Get or create state for this user
            if user_id not in self.conversation_state:
                self.conversation_state[user_id] = {
                    "requirements": {},
                    "matched_resumes": [],
                    "refinement_count": 0
                }
            
            state = self.conversation_state[user_id]
            
            # Parse user input for requirements
            requirements = self._parse_requirements(prompt)
            
            # If requirements provided, search for matches
            if requirements or state["requirements"]:
                # Merge with existing requirements
                state["requirements"].update(requirements)
                
                # Search for matches (would call tool in real implementation)
                matches = await self._search_matching_resumes(
                    state["requirements"],
                    metadata
                )
                
                state["matched_resumes"] = matches
                state["refinement_count"] += 1
                
                response = self._format_match_response(matches, state)
            else:
                # Ask for more details
                response = (
                    "I'd be happy to help find matching resumes! "
                    "Could you describe the job requirements? "
                    "Please mention:\n"
                    "- Position/Role\n"
                    "- Required skills\n"
                    "- Experience level\n"
                    "- Preferred qualifications"
                )
            
            return {
                "response": response,
                "metadata": {
                    "agent": "resume_matching",
                    "requirements": state["requirements"],
                    "matches": state["matched_resumes"],
                    "match_count": len(state["matched_resumes"]),
                    "refinement_count": state["refinement_count"]
                }
            }
            
        except Exception as e:
            logger.error(f"[ResumeMatchingAgent] Error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error while searching for resumes. Please try again.",
                "metadata": {"error": str(e)}
            }
    
    def _parse_requirements(self, prompt: str) -> Dict[str, str]:
        """
        Parse requirements from user input
        
        Args:
            prompt: User input
            
        Returns:
            Extracted requirements dict
        """
        requirements = {}
        prompt_lower = prompt.lower()
        
        # Simple pattern matching
        if "senior" in prompt_lower or "sr" in prompt_lower:
            requirements["level"] = "senior"
        elif "junior" in prompt_lower or "jr" in prompt_lower:
            requirements["level"] = "junior"
        elif "mid" in prompt_lower or "mid-level" in prompt_lower:
            requirements["level"] = "mid-level"
        
        # Extract skills
        common_skills = ["python", "java", "javascript", "react", "aws", "postgresql",
                        "fastapi", "nodejs", "docker", "kubernetes"]
        for skill in common_skills:
            if skill in prompt_lower:
                if "skills" not in requirements:
                    requirements["skills"] = []
                requirements["skills"].append(skill)
        
        # Extract other requirements
        if "5+" in prompt_lower or "5 year" in prompt_lower:
            requirements["min_experience"] = "5+"
        elif "3+" in prompt_lower or "3 year" in prompt_lower:
            requirements["min_experience"] = "3+"
        elif "1+" in prompt_lower or "1 year" in prompt_lower:
            requirements["min_experience"] = "1+"
        
        return requirements
    
    async def _search_matching_resumes(
        self,
        requirements: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for matching resumes
        
        Args:
            requirements: Job requirements
            metadata: Metadata for search
            
        Returns:
            List of matching resumes
        """
        tool_result = await self.resume_matching_tool.execute(requirements, limit=2)
        if not tool_result.get("success"):
            logger.warning("[ResumeMatchingAgent] ResumeMatchingTool returned no results")
            return []

        matches = tool_result.get("matches", [])
        normalized: List[Dict[str, Any]] = []
        for idx, match in enumerate(matches, 1):
            normalized.append(
                {
                    "id": match.get("user_id", idx),
                    "candidate_name": match.get("name", f"Candidate {idx}"),
                    "summary": match.get("match_reason", "Candidate matched by semantic search"),
                    "skills": match.get("skills", []),
                    "experience_years": match.get("experience_years", 0),
                    "match_score": match.get("match_score", 0.0),
                }
            )

        return normalized
    
    def _format_match_response(
        self,
        matches: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> str:
        """
        Format match results for display
        
        Args:
            matches: List of matched resumes
            state: Conversation state
            
        Returns:
            Formatted response string
        """
        if not matches:
            return (
                "I couldn't find any resumes matching your requirements. "
                "Would you like to refine the search criteria?"
            )
        
        response = f"Found {len(matches)} matching resumes:\n\n"
        
        for i, match in enumerate(matches, 1):
            response += (
                f"{i}. **{match['candidate_name']}** "
                f"(Match: {match['match_score']*100:.0f}%)\n"
                f"   {match['summary']}\n"
                f"   Skills: {', '.join(match['skills'])}\n"
                f"   Experience: {match['experience_years']}+ years\n\n"
            )
        
        response += (
            "Would you like to:\n"
            "1. View detailed profiles\n"
            "2. Refine the search criteria\n"
            "3. Proceed with any of these candidates"
        )
        
        return response


# Global instance
_agent: Optional[ResumeMatchingAgent] = None


def get_resume_matching_agent(db_session: Optional[Any] = None) -> ResumeMatchingAgent:
    """Get or create resume matching agent"""
    global _agent
    if _agent is None:
        _agent = ResumeMatchingAgent(db_session=db_session)
    return _agent
