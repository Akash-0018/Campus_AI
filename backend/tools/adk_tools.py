"""
Resume Matching Tool - ADK Tool for semantic resume search

Uses ChromaDB to find matching resumes based on user requirements.
"""
import logging
from typing import Dict, Any, List, Optional
from services.matching_service import MatchingService
from services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class ResumeMatchingTool:
    """Tool for matching resumes from ChromaDB"""
    
    def __init__(self):
        self.matching_service = MatchingService()
        self.embeddings_service = EmbeddingsService()
        logger.info("[ResumeTool] Initialized")
    
    async def execute(
        self,
        requirements: Dict[str, Any],
        limit: int = 2,
        min_score: float = 0.65
    ) -> Dict[str, Any]:
        """
        Match resumes based on requirements
        
        Args:
            requirements: User job requirements dict
            limit: Max results to return (default: 2)
            min_score: Minimum similarity score (0-1)
        
        Returns:
            Dict with matches and metadata
        """
        try:
            # Enforce limit guardrail
            if limit > 2:
                logger.warning(f"[ResumeTool] Requested limit {limit} > max 2, capping to 2")
                limit = 2
            
            # Get matches from service
            matches = self.matching_service.get_top_matches(
                requirements=requirements,
                limit=limit
            )
            
            # Filter by score threshold guardrail
            filtered_matches = [
                m for m in matches 
                if m.get("match_score", 0) >= min_score
            ]
            
            logger.info(f"[ResumeTool] Found {len(filtered_matches)} matches for requirements")
            
            return {
                "success": True,
                "matches": filtered_matches,
                "count": len(filtered_matches),
                "metadata": {
                    "tool": "resume_matching",
                    "limit_applied": limit,
                    "min_score": min_score
                }
            }
        
        except Exception as e:
            logger.error(f"[ResumeTool] Error matching resumes: {e}", exc_info=True)
            return {
                "success": False,
                "matches": [],
                "count": 0,
                "error": str(e),
                "metadata": {"tool": "resume_matching"}
            }


class UserProfileTool:
    """Tool for fetching user information"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        logger.info("[UserProfileTool] Initialized")
    
    async def execute(
        self,
        user_id: int,
        include_private: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch user profile
        
        Args:
            user_id: User to fetch
            include_private: Include private fields (restricted)
        
        Returns:
            User profile dict
        """
        try:
            # Import here to avoid circular imports
            from database.user_repository import get_user_repository
            
            user_repo = get_user_repository(self.db_session)
            user = user_repo.read(user_id)
            
            if not user:
                return {
                    "success": False,
                    "user": None,
                    "error": "User not found"
                }
            
            # Prepare response (apply guardrail for data masking)
            user_data = {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "bio": user.bio,
                "phone_number": user.phone_number,
                "profile_image_url": user.profile_image_url,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            
            logger.info(f"[UserProfileTool] Fetched profile for user {user_id}")
            
            return {
                "success": True,
                "user": user_data,
                "metadata": {"tool": "user_profile"}
            }
        
        except Exception as e:
            logger.error(f"[UserProfileTool] Error fetching user: {e}", exc_info=True)
            return {
                "success": False,
                "user": None,
                "error": str(e),
                "metadata": {"tool": "user_profile"}
            }


class EmbeddingsTool:
    """Tool for generating embeddings"""
    
    def __init__(self):
        self.embeddings_service = EmbeddingsService()
        logger.info("[EmbeddingsTool] Initialized")
    
    async def execute(
        self,
        text: str,
        max_length: int = 5000
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text
        
        Args:
            text: Text to embed
            max_length: Max text length guardrail
        
        Returns:
            Embeddings vector and metadata
        """
        try:
            # Apply length guardrail
            if len(text) > max_length:
                logger.warning(
                    f"[EmbeddingsTool] Text length {len(text)} > {max_length}, truncating"
                )
                text = text[:max_length]
            
            # Generate embeddings
            embeddings = self.embeddings_service.get_embeddings(text)
            
            if not embeddings:
                return {
                    "success": False,
                    "embeddings": None,
                    "error": "Failed to generate embeddings"
                }
            
            logger.info(f"[EmbeddingsTool] Generated embeddings (dim={len(embeddings)})")
            
            return {
                "success": True,
                "embeddings": embeddings,
                "dimension": len(embeddings),
                "text_length": len(text),
                "metadata": {"tool": "embeddings"}
            }
        
        except Exception as e:
            logger.error(f"[EmbeddingsTool] Error generating embeddings: {e}", exc_info=True)
            return {
                "success": False,
                "embeddings": None,
                "error": str(e),
                "metadata": {"tool": "embeddings"}
            }
