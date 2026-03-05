"""User Profile Agent - Manages user profiles and preferences."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from database.user_repository import get_user_repository
from tools.adk_tools import UserProfileTool

logger = logging.getLogger(__name__)


class UserProfileAgent(BaseAgent):
    """ADK agent for viewing and updating user profile data."""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__(
            name="user_profile_agent",
            description="Manages user profiles and preferences",
            system_instruction=(
                "You are a helpful assistant for managing user profiles. "
                "Help users view and update their profile information, "
                "preferences, and settings. Always prioritize privacy and data security."
            ),
        )

        self.db_session = db_session
        self.user_profile_tool = UserProfileTool(db_session=db_session)
        logger.info("[UserProfileAgent] Initialized")

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
                    "response": "Missing user context for profile operation.",
                    "metadata": {"error": "missing_user_id"},
                }

            # Keep DB session in sync with request-level metadata.
            request_db_session = metadata.get("db_session") if metadata else None
            if request_db_session is not None:
                self.db_session = request_db_session
                self.user_profile_tool.db_session = request_db_session

            action = self._detect_action(prompt)

            if action == "view":
                profile = await self._get_user_profile(int(user_id))
                response = self._format_profile_view(profile)
            elif action == "update":
                updates = self._parse_updates(prompt)
                result = await self._update_user_profile(int(user_id), updates)
                response = self._format_update_response(result)
            elif action == "preferences":
                prefs = await self._get_user_preferences(int(user_id))
                response = self._format_preferences_view(prefs)
            else:
                response = (
                    "I can help with your profile. You can: view profile, update profile, "
                    "or manage preferences. What would you like to do?"
                )

            return {
                "response": response,
                "metadata": {"agent": "user_profile", "action": action, "user_id": user_id},
            }
        except Exception as e:
            logger.error("[UserProfileAgent] Error: %s", str(e), exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error managing your profile. Please try again.",
                "metadata": {"error": str(e)},
            }

    def _detect_action(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["update", "change", "edit", "modify", "set"]):
            return "update"
        if any(word in prompt_lower for word in ["preference", "setting", "config"]):
            return "preferences"
        if any(word in prompt_lower for word in ["view", "show", "see", "my profile", "tell me"]):
            return "view"
        return "help"

    async def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        result = await self.user_profile_tool.execute(user_id=user_id)
        if not result.get("success"):
            return {}

        user = result.get("user", {})
        return {
            "id": user.get("user_id"),
            "name": user.get("full_name", "Unknown"),
            "email": user.get("email", ""),
            "role": user.get("role", "N/A"),
            "bio": user.get("bio", "No bio set"),
            "phone_number": user.get("phone_number", "N/A"),
            "created_at": user.get("created_at", "N/A"),
        }

    async def _update_user_profile(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not updates:
            return {"success": False, "error": "No valid fields found to update"}
        if self.db_session is None:
            return {"success": False, "error": "Database session not available"}

        user_repo = get_user_repository(self.db_session)
        user = user_repo.read(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        for field, value in updates.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        user_repo.update(user.user_id, user)

        return {
            "success": True,
            "updated_fields": list(updates.keys()),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        profile = await self._get_user_profile(user_id)
        if not profile:
            return {}

        return {
            "notifications": {"email": True, "in_app": True, "sms": False},
            "privacy": {"show_profile": True, "show_email": False, "allow_contact": True},
            "search_filters": {"preferred_skills": [], "preferred_level": "mid-senior"},
        }

    def _format_profile_view(self, profile: Dict[str, Any]) -> str:
        if not profile:
            return "Profile not found"

        email = profile.get("email", "")
        masked_email = email.replace("@", "@***") if email else "N/A"
        return (
            "Your Profile\n\n"
            f"Name: {profile.get('name', 'Unknown')}\n"
            f"Role: {profile.get('role', 'N/A')}\n"
            f"Email: {masked_email}\n"
            f"Bio: {profile.get('bio', 'No bio set')}\n"
            f"Member Since: {profile.get('created_at', 'N/A')}\n\n"
            "Reply with update instructions if you want to change details."
        )

    def _parse_updates(self, prompt: str) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        prompt_lower = prompt.lower()

        if "bio" in prompt_lower:
            bio_idx = prompt_lower.find("bio")
            updates["bio"] = prompt[bio_idx + 3 :].strip(" :.-")

        if "phone" in prompt_lower:
            updates["phone_number"] = "Updated via ADK agent"

        if "name" in prompt_lower:
            updates["full_name"] = "Updated User"

        return updates

    def _format_update_response(self, result: Dict[str, Any]) -> str:
        if result.get("success"):
            fields = result.get("updated_fields", [])
            return f"Updated {len(fields)} field(s): {', '.join(fields)}"
        return f"Update failed: {result.get('error', 'Unknown error')}"

    def _format_preferences_view(self, prefs: Dict[str, Any]) -> str:
        if not prefs:
            return "Preferences not available"
        return (
            "Preferences:\n"
            f"Notifications: {prefs.get('notifications')}\n"
            f"Privacy: {prefs.get('privacy')}\n"
            f"Search filters: {prefs.get('search_filters')}"
        )


_agent: Optional[UserProfileAgent] = None


def get_user_profile_agent(db_session: Optional[Any] = None) -> UserProfileAgent:
    """Get or create user profile agent."""
    global _agent
    if _agent is None:
        _agent = UserProfileAgent(db_session=db_session)
    return _agent
