"""Recruitment Coordinator Agent - Orchestrates multi-agent recruitment workflow."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.requirements_agent_adk import get_requirements_agent
from agents.resume_matching_agent_adk import get_resume_matching_agent
from agents.user_profile_agent_adk import get_user_profile_agent

logger = logging.getLogger(__name__)


class RecruitmentCoordinatorAgent(BaseAgent):
    """Coordinates requirements collection, matching, and user profile workflows."""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__(
            name="recruitment_coordinator_agent",
            description="Orchestrates end-to-end recruitment workflow",
            system_instruction=(
                "You are a recruitment coordinator. Orchestrate requirements, candidate matching, "
                "and profile operations across specialized agents."
            ),
        )

        self.db_session = db_session
        self.workflows: Dict[int, Dict[str, Any]] = {}
        logger.info("[RecruitmentCoordinatorAgent] Initialized")

    async def _process_input(
        self,
        prompt: str,
        session: Any,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            user_id = metadata.get("user_id") if metadata else None
            if not user_id:
                return {
                    "success": False,
                    "response": "Missing user context for workflow execution.",
                    "metadata": {"error": "missing_user_id"},
                }

            if user_id not in self.workflows:
                self.workflows[user_id] = {
                    "stage": "initial",
                    "requirements": None,
                    "candidates": [],
                    "selected_candidate": None,
                    "interview_status": {},
                    "updated_at": datetime.utcnow().isoformat(),
                }

            workflow = self.workflows[user_id]
            action = self._determine_action(prompt, workflow["stage"])
            result = await self._execute_action(action, prompt, int(user_id), metadata or {}, workflow)
            workflow["updated_at"] = datetime.utcnow().isoformat()

            return {
                "success": result.get("success", True),
                "response": result.get("response", ""),
                "metadata": {
                    "agent": "recruitment_coordinator",
                    "action": action,
                    "workflow_stage": workflow["stage"],
                    "user_id": user_id,
                    **result.get("metadata", {}),
                },
            }
        except Exception as e:
            logger.error("[RecruitmentCoordinatorAgent] Error: %s", str(e), exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error. Please try again.",
                "metadata": {"error": str(e)},
            }

    async def _execute_action(
        self,
        action: str,
        prompt: str,
        user_id: int,
        metadata: Dict[str, Any],
        workflow: Dict[str, Any],
    ) -> Dict[str, Any]:
        if action == "reset":
            workflow["stage"] = "initial"
            workflow["requirements"] = None
            workflow["candidates"] = []
            workflow["selected_candidate"] = None
            workflow["interview_status"] = {}
            return {"response": "Workflow reset. Tell me the role you want to hire for."}

        if action == "requirements":
            req_agent = get_requirements_agent()
            req_result = await req_agent.execute_prompt(
                prompt=prompt,
                user_id=str(user_id),
                metadata=metadata,
            )
            workflow["requirements"] = req_result.get("metadata", {})
            workflow["stage"] = "candidate_search" if req_result.get("is_complete") else "requirements"
            return {
                "success": req_result.get("success", True),
                "response": req_result.get("response", ""),
                "metadata": {"delegated_agent": "requirements"},
            }

        if action == "matching":
            match_agent = get_resume_matching_agent()
            match_result = await match_agent.execute_prompt(
                prompt=prompt,
                user_id=str(user_id),
                metadata=metadata,
            )
            workflow["candidates"] = match_result.get("metadata", {}).get("matches", [])
            workflow["stage"] = "candidate_review"
            return {
                "success": match_result.get("success", True),
                "response": match_result.get("response", ""),
                "metadata": {"delegated_agent": "resume_matching"},
            }

        if action == "profile":
            profile_agent = get_user_profile_agent()
            profile_result = await profile_agent.execute_prompt(
                prompt=prompt,
                user_id=str(user_id),
                metadata=metadata,
            )
            workflow["stage"] = workflow.get("stage", "profile")
            return {
                "success": profile_result.get("success", True),
                "response": profile_result.get("response", ""),
                "metadata": {"delegated_agent": "user_profile"},
            }

        if action == "status":
            return {"response": self._get_workflow_status(workflow)}

        workflow["stage"] = "requirements"
        return {
            "response": (
                "I can coordinate requirements, candidate matching, and profile updates. "
                "Tell me what you want to do next."
            )
        }

    def _determine_action(self, prompt: str, stage: str) -> str:
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["reset", "start over", "new position"]):
            return "reset"
        if any(word in prompt_lower for word in ["status", "progress", "where are we"]):
            return "status"
        if any(word in prompt_lower for word in ["profile", "settings", "preferences", "account"]):
            return "profile"
        if any(word in prompt_lower for word in ["match", "candidate", "resume", "search", "find"]):
            return "matching"
        if stage in {"initial", "requirements"}:
            return "requirements"
        return "matching"

    def _get_workflow_status(self, workflow: Dict[str, Any]) -> str:
        return (
            "Workflow Status\n"
            f"Stage: {workflow.get('stage', 'unknown')}\n"
            f"Requirements captured: {bool(workflow.get('requirements'))}\n"
            f"Candidates cached: {len(workflow.get('candidates', []))}\n"
            f"Selected candidate: {workflow.get('selected_candidate')}\n"
            f"Interview status: {workflow.get('interview_status', {})}\n"
        )


_agent: Optional[RecruitmentCoordinatorAgent] = None


def get_recruitment_coordinator_agent(db_session: Optional[Any] = None) -> RecruitmentCoordinatorAgent:
    """Get or create recruitment coordinator agent."""
    global _agent
    if _agent is None:
        _agent = RecruitmentCoordinatorAgent(db_session=db_session)
    return _agent
