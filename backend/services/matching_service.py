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
        logger.info(
            "[MULTI-AGENT-ORCHESTRATION] ✓ MatchingService initialized | "
            "component=matching_service | agent_type=resume_matcher"
        )

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
            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] Building resume matcher query | "
                f"query_preview={query_text[:80]} | "
                f"query_length={len(query_text)}"
            )

            # --------------------------------------------------
            # STEP 2: SQL FILTERING
            # --------------------------------------------------
            chatbot_service = ChatbotSearchService(self.session)
            logger.debug(f"[MULTI-AGENT-ORCHESTRATION] Delegating to SQL filter service")

            keywords = chatbot_service._extract_search_keywords(query_text)
            filtered_resumes = chatbot_service._filter_resumes_by_sql(
                query=query_text,
                keywords=keywords
            )

            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] Resume filtering complete | "
                f"filtered_count={len(filtered_resumes)} | "
                f"filter_stage=sql_pre_filter"
            )

            if not filtered_resumes:
                logger.warning(
                    f"[MULTI-AGENT-ORCHESTRATION] No resumes matched in SQL filter | "
                    f"query={query_text[:60]} | stage=sql_pre_filter"
                )
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
                logger.warning(
                    f"[MULTI-AGENT-ORCHESTRATION] Resume collection incomplete | "
                    f"filtered_resumes={len(filtered_resumes)} but none indexed | "
                    f"stage=collection_prep"
                )
                return []

            # --------------------------------------------------
            # STEP 4: RESUME MATCHING AGENT - SEMANTIC SEARCH
            # --------------------------------------------------
            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] Starting semantic matching agent | "
                f"collection=user_resumes | top_k=15 | min_similarity=0.4"
            )
            vector_results = embeddings_service.search(
                collection_name="user_resumes",
                query_text=query_text,
                top_k=15,              # higher recall
                min_similarity=0.4
            )

            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] ✓ Semantic matching complete | "
                f"matched_candidates={len(vector_results)} | "
                f"agent=semantic_matcher"
            )

            if not vector_results:
                return []

            # --------------------------------------------------
            # STEP 5: MULTI-AGENT COORDINATION - RESULT VALIDATION
            # --------------------------------------------------
            logger.debug(f"[MULTI-AGENT-ORCHESTRATION] Validating matched candidates against filtered set | allowed_ids={len(allowed_chroma_ids)}")
            filtered_vector_results = [
                r for r in vector_results
                if r.get("id") in allowed_chroma_ids
            ]

            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] Result validation complete | "
                f"valid_matches={len(filtered_vector_results)} of {len(vector_results)} candidates | "
                f"stage=result_validation"
            )

            if not filtered_vector_results:
                logger.warning(
                    f"[MULTI-AGENT-ORCHESTRATION] No valid matches found | "
                    f"semantic_matches={len(vector_results)} but none passed validation"
                )
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

            logger.info(
                f"[MULTI-AGENT-ORCHESTRATION] ✓ Resume matching orchestration complete | "
                f"final_matches={len(results)} | "
                f"top_k={top_k} | "
                f"orchestration_status=success"
            )
            return results

        except Exception as e:
            logger.error(
                f"[MULTI-AGENT-ORCHESTRATION] ✗ Resume matching orchestration failed | "
                f"error={str(e)} | "
                f"orchestration_status=failed",
                exc_info=True
            )
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
