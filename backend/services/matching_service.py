"""
Matching service for Campus AI
Two-stage RAG matching:
1. SQL-based filtering (cheap, deterministic)
2. Vector-based ranking (semantic, accurate)
"""

import logging
import json
from typing import List
from sqlmodel import Session

from services.chatbot_search_service import ChatbotSearchService
from services.embeddings_service import embeddings_service
from database.resume_repository import get_resume_repository
from database.user_repository import get_user_repository

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching candidates using two-stage RAG"""

    def __init__(self, session: Session = None):
        self.session = session
        logger.info("MatchingService initialized")

    # --------------------------------------------------
    # MAIN ENTRY
    # --------------------------------------------------
    def find_candidates_rag(self, company_requirements: dict, top_k: int = 2) -> List[dict]:
        """
        Two-stage RAG search:
        1. SQL-based filtering
        2. Vector-based ranking
        """

        if not self.session:
            logger.error("Session required for RAG matching")
            return []

        try:
            # --------------------------------------------------
            # STEP 1: Build semantic query
            # --------------------------------------------------
            query_text = self._build_search_query(company_requirements)
            logger.info(f"[RAG] Query text: {query_text}")

            # --------------------------------------------------
            # STEP 2: SQL FILTERING
            # --------------------------------------------------
            chatbot_service = ChatbotSearchService(self.session)

            keywords = chatbot_service._extract_search_keywords(query_text)
            filtered_resumes = chatbot_service._filter_resumes_by_sql(
                query=query_text,
                keywords=keywords
            )

            logger.info(f"[RAG] SQL filter returned {len(filtered_resumes)} resumes")

            if not filtered_resumes:
                logger.warning("[RAG] No resumes after SQL filtering")
                return []

            # --------------------------------------------------
            # STEP 3: Collect allowed Chroma IDs
            # --------------------------------------------------
            allowed_chroma_ids = {
                r.chroma_collection_id
                for r in filtered_resumes
                if r.chroma_collection_id
            }

            if not allowed_chroma_ids:
                logger.warning("[RAG] SQL resumes have no Chroma IDs")
                return []

            # --------------------------------------------------
            # STEP 4: VECTOR SEARCH (NO ID FILTERING HERE)
            # --------------------------------------------------
            vector_results = embeddings_service.search(
                collection_name="user_resumes",
                query_text=query_text,
                top_k=15,              # higher recall
                min_similarity=0.4
            )

            logger.info(f"[RAG] Vector search returned {len(vector_results)} results")

            if not vector_results:
                return []

            # --------------------------------------------------
            # STEP 5: POST-FILTER VECTOR RESULTS USING SQL SET
            # --------------------------------------------------
            filtered_vector_results = [
                r for r in vector_results
                if r.get("id") in allowed_chroma_ids
            ]

            logger.info(
                f"[RAG] Vector results after SQL post-filter: "
                f"{len(filtered_vector_results)}"
            )

            if not filtered_vector_results:
                logger.warning("[RAG] No vector results matched SQL-filtered resumes")
                return []

            # Keep only top_k after filtering
            final_results = filtered_vector_results[:top_k]

            # --------------------------------------------------
            # STEP 6: HYDRATE RESULTS
            # --------------------------------------------------
            resume_repo = get_resume_repository(self.session)
            user_repo = get_user_repository(self.session)

            results = []

            for rank, result in enumerate(final_results, 1):
                resume = resume_repo.get_by_chroma_id(result["id"])
                if not resume:
                    continue

                user = user_repo.read(resume.user_id)
                if not user:
                    continue

                try:
                    skills = json.loads(resume.skills) if resume.skills else []
                except Exception:
                    skills = [s.strip() for s in resume.skills.split(",")]

                results.append({
                    "rank": rank,
                    "resume_id": resume.resume_id,
                    "user_id": resume.user_id,
                    "name": resume.candidate_name or user.full_name,
                    "email": resume.candidate_email or user.email,
                    "phone": resume.candidate_phone or user.phone_number,
                    "skills": skills,
                    "experience": resume.experience,
                    "location": resume.location,
                    "match_score": result.get("similarity", 0.0),
                    "match_reason": (
                        f"Semantic similarity score: "
                        f"{result.get('similarity', 0.0):.2%}"
                    ),
                    "profile_image_url": user.profile_image_url,
                    "is_verified": user.is_verified
                })

            logger.info(f"[RAG] Final matches returned: {len(results)}")
            return results

        except Exception as e:
            logger.error(f"[RAG] Error during matching: {e}", exc_info=True)
            return []

    # --------------------------------------------------
    # QUERY BUILDER
    # --------------------------------------------------
    def _build_search_query(self, requirements: dict) -> str:
        """Build semantic query from requirements"""

        parts = []

        if requirements.get("role"):
            parts.append(requirements["role"])

        if requirements.get("skills"):
            parts.append(f"skills in {requirements['skills']}")

        if requirements.get("experience_years"):
            parts.append(f"{requirements['experience_years']} experience")

        if requirements.get("industry"):
            parts.append(requirements["industry"])

        if requirements.get("location"):
            parts.append(f"based in {requirements['location']}")

        return ", ".join(parts) if parts else "software engineer"


# --------------------------------------------------
# Singleton
# --------------------------------------------------
matching_service = MatchingService()

def get_matching_service() -> MatchingService:
    return matching_service
