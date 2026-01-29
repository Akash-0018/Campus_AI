"""
Chatbot & User Search Service for Campus AI
Handles semantic search for user profiles/resumes
Returns top-2 matching profiles for matches
"""
import logging
import json
import re
from typing import List, Dict, Any, Set, Tuple
from sqlmodel import Session, select
from models.resume import Resume
from models.user import User
from services.embeddings_service import embeddings_service
from utils.constants import RESUME_COLLECTION
logger = logging.getLogger(__name__)

class ChatbotSearchService:
    """Service for chatbot-based user profile search"""
    
    def __init__(self, session: Session):
        self.session = session
        self.embeddings_service = embeddings_service
        logger.info("ChatbotSearchService initialized")

    
    def _extract_search_keywords(self, query: str) -> Dict[str, Any]:
        """Extract structured keywords from query for SQL filtering"""
        query_lower = query.lower()
        
        keywords = {
            'skills': [],
            'experience_level': None,
            'years_min': None,
            'years_max': None,
            'technologies': []
        }
        
        # Experience level keywords
        if any(word in query_lower for word in ['senior', 'lead', 'principal', 'architect']):
            keywords['experience_level'] = 'senior'
        elif any(word in query_lower for word in ['junior', 'entry', 'early-career', 'intern']):
            keywords['experience_level'] = 'junior'
        elif any(word in query_lower for word in ['mid', 'intermediate', 'mid-level']):
            keywords['experience_level'] = 'mid'
        
        # Extract years of experience
        years_match = re.search(r'(\d+)\s*\+?\s*years?', query_lower)
        if years_match:
            years = int(years_match.group(1))
            keywords['years_min'] = years
        
        # Common skills and technologies
        skills_dict = {
            'python': ['Python', 'python'],
            'javascript': ['JavaScript', 'javascript'],
            'java': ['Java', 'Java'],
            'react': ['React', 'react'],
            'fastapi': ['FastAPI', 'fastapi'],
            'django': ['Django', 'django'],
            'spring': ['Spring Boot', 'spring'],
            'kubernetes': ['Kubernetes', 'kubernetes'],
            'aws': ['AWS', 'aws'],
            'docker': ['Docker', 'docker'],
            'tensorflow': ['TensorFlow', 'tensorflow'],
            'machine learning': ['Machine Learning', 'ML'],
            'data science': ['Data Analysis', 'Pandas'],
            'frontend': ['React', 'Next.js', 'JavaScript', 'TypeScript'],
            'backend': ['FastAPI', 'Django', 'Spring Boot', 'Java'],
            'full stack': ['Python', 'JavaScript', 'React', 'FastAPI'],
            'microservices': ['Microservices', 'Spring Boot'],
        }
        
        for skill_key, skill_values in skills_dict.items():
            if skill_key in query_lower:
                keywords['skills'].extend(skill_values)
                keywords['technologies'].extend(skill_values)
        
        # Clean duplicates
        keywords['skills'] = list(set(keywords['skills']))
        keywords['technologies'] = list(set(keywords['technologies']))
        
        logger.info(f"Extracted keywords: {keywords}")
        return keywords
    
    def _filter_resumes_by_sql(self, query: str, keywords: Dict[str, Any]) -> List[Resume]:
        """
        Stage 1: Filter resumes from SQLite database based on extracted keywords
        Returns: List of candidate resumes that match the query criteria
        """
        try:
            # Start with all active user resumes
            statement = select(Resume).join(User).where(User.is_active == True)
            
            candidates = []
            all_resumes = self.session.exec(statement).all()
            
            for resume in all_resumes:
                score = 0
                
                # Score by skills match
                if resume.skills:
                    try:
                        resume_skills = json.loads(resume.skills) if isinstance(resume.skills, str) else resume.skills
                        resume_skills_lower = [s.lower() for s in resume_skills]
                        
                        for keyword_skill in keywords['skills']:
                            if any(keyword_skill.lower() in rs for rs in resume_skills_lower):
                                score += 10
                    except:
                        pass
                
                # Score by experience level match
                if resume.experience and keywords['experience_level']:
                    exp_lower = resume.experience.lower()
                    
                    if keywords['experience_level'] == 'senior' and any(w in exp_lower for w in ['6', '7', '8', '9', 'senior', 'lead']):
                        score += 5
                    elif keywords['experience_level'] == 'junior' and any(w in exp_lower for w in ['1', '2', '3', 'junior', 'entry']):
                        score += 5
                    elif keywords['experience_level'] == 'mid' and any(w in exp_lower for w in ['4', '5', 'mid']):
                        score += 5
                
                # Score by years minimum requirement
                if resume.experience and keywords['years_min']:
                    try:
                        years_match = re.search(r'(\d+)', resume.experience)
                        if years_match:
                            years = int(years_match.group(1))
                            if years >= keywords['years_min']:
                                score += 3
                    except:
                        pass
                
                # Score by location if mentioned
                if resume.location and any(word in query.lower() for word in [resume.location.lower()]):
                    score += 2
                
                # Include if score > 0 or if we have no specific keywords (fallback to all resumes)
                if score > 0:
                    candidates.append((resume, score))
                elif not keywords['skills'] and not keywords['experience_level']:
                    # If no keywords extracted, include all
                    candidates.append((resume, 1))
            
            # Sort by score descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Return top candidates (first 10 for vector search)
            filtered_resumes = [resume for resume, score in candidates[:10]]
            
            logger.info(f"SQL filtering: Found {len(filtered_resumes)} candidates from {len(all_resumes)} total resumes")
            return filtered_resumes
            
        except Exception as e:
            logger.error(f"Error filtering resumes by SQL: {e}")
            return []
    
    def _search_filtered_resumes_in_chromadb(
        self,
        query: str,
        top_k: int = 2,
        min_similarity: float = 0.65
    ) -> List[Dict[str, Any]]:
        """
        Pure vector search on resume embeddings
        """
        try:
            from utils.constants import RESUME_COLLECTION

            collection = self.embeddings_service.get_or_create_collection(RESUME_COLLECTION)

            if collection.count() == 0:
                logger.warning("ChromaDB collection is empty")
                return []

            query_embedding = self.embeddings_service.embed_text(query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10,
                include=["documents", "metadatas", "distances"]
            )

            matches = []

            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    similarity = max(0.0, 1 - distance)

                    if similarity >= min_similarity:
                        matches.append({
                            "id": doc_id,
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "similarity": round(similarity, 4)
                        })

                matches.sort(key=lambda x: x["similarity"], reverse=True)
                return matches[:top_k]
        except Exception as e:
            logger.error(f"Error searching filtered resumes in ChromaDB: {e}", exc_info=True)
            return []
        logger.info(f"CHROMA METADATA DEBUG: {results['metadatas'][0][i]}")

    
    def search_user_profiles(
        self,
        query: str,
        top_k: int = 2,
        current_user_id: int = None,
        min_similarity: float = 0.25
    ) -> Dict[str, Any]:
        """
        PURE VECTOR SEARCH (SQL FILTER DISABLED)

        This searches directly against ChromaDB resume embeddings
        and returns TOP-2 matching profiles.
        """
        try:
            logger.info(f"[VECTOR SEARCH] Searching profiles for query: {query}")

            # Always enforce TOP-2
            top_k = 2

            # --- VECTOR SEARCH ---
            vector_results = self._search_filtered_resumes_in_chromadb(
                query=query,
                top_k=top_k,
                min_similarity=min_similarity
            )

            logger.info(f"[VECTOR SEARCH] Returned {len(vector_results)} results")

            matches = []
            seen_user_ids = set()

            for result in vector_results:
                try:
                    metadata = result.get("metadata", {})
                    user_id = int(metadata.get("user_id", 0))

                    if not user_id:
                        continue

                    # Skip current user
                    if current_user_id and user_id == current_user_id:
                        continue

                    if user_id in seen_user_ids:
                        continue

                    seen_user_ids.add(user_id)

                    user = self.session.get(User, user_id)
                    if not user or not user.is_active:
                        continue

                    similarity = result.get("similarity", 0)

                    match_data = {
                        "rank": len(matches) + 1,
                        "user_id": user_id,
                        "name": user.full_name,
                        "email": user.email if user.is_verified else "***hidden***",
                        "phone": user.phone_number if user.is_verified else "***hidden***",
                        "bio": user.bio,
                        "location": metadata.get("location", ""),
                        "skills": json.loads(metadata.get("skills", "[]")),
                        "experience": metadata.get("experience", ""),
                        "summary": result.get("document", "")[:500],
                        "match_score": round(similarity * 100, 2),
                        "similarity_score": round(similarity, 4),
                        "profile_complete": bool(user.bio and user.phone_number),
                    }

                    matches.append(match_data)

                    logger.info(
                        f"[MATCH] #{len(matches)} {user.full_name} "
                        f"(user_id={user_id}, similarity={similarity:.4f})"
                    )

                    if len(matches) >= top_k:
                        break

                except Exception as e:
                    logger.warning(f"Error processing vector result: {e}")
                    continue

            return {
                "status": "success",
                "query": query,
                "match_count": len(matches),
                "matches": matches,
                "response_type": "TOP_2_MATCHES" if matches else "NO_MATCHES",
                "algorithm": "Pure Vector Search (SQL Disabled)",
                "parameters": {
                    "top_k": top_k,
                    "min_similarity_threshold": min_similarity
                }
            }

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "query": query,
                "match_count": 0,
                "matches": [],
                "response_type": "ERROR",
                "algorithm": "Pure Vector Search",
                "error": str(e)
            }

    def _generate_match_reason(self, query: str, metadata: dict) -> str:
        """Generate a natural language reason for the match with better context"""
        try:
            skills = json.loads(metadata.get('skills', '[]'))
            experience = metadata.get('experience', '')
            location = metadata.get('location', '')
            
            reasons = []
            query_lower = query.lower()
            
            # Check for skill matches - improved matching logic
            if skills:
                matched_skills = []
                for skill in skills:
                    if skill.lower() in query_lower:
                        matched_skills.append(skill)
                
                # If no exact matches, find partial matches
                if not matched_skills and len(skills) > 0:
                    reasons.append(f"Expertise in {', '.join(skills[:3])}".strip())
                elif matched_skills:
                    reasons.append(f"Skilled in {', '.join(matched_skills[:3])}".strip())
            
            # Experience matching
            if experience:
                if 'experience' in query_lower or 'years' in query_lower:
                    reasons.insert(0, f"{experience} of relevant experience")
                else:
                    reasons.append(f"{experience} experience")
            
            # Location match  
            if location and ('location' in query_lower or 'based' in query_lower or 'city' in query_lower):
                reasons.append(f"Based in {location}")
            
            # Role/level matching
            query_keywords = ['early-career', 'junior', 'senior', 'lead', 'staff', 'intern', 'backend', 'frontend', 'full stack', 'data']
            for keyword in query_keywords:
                if keyword in query_lower:
                    reasons.append(f"Matches {keyword} profile")
                    break
            
            if reasons:
                return "; ".join(reasons[:3])  # Limit to 3 reasons
            else:
                return "Strong semantic match with requirements"
                
        except Exception as e:
            logger.warning(f"Error generating match reason: {e}")
            return "Profile match found"
    
    def get_all_active_users(self, exclude_user_id: int = None) -> List[Dict[str, Any]]:
        """Get all active users (searchable directory)"""
        try:
            query = select(User).where(User.is_active == True)
            if exclude_user_id:
                query = query.where(User.user_id != exclude_user_id)
            
            users = self.session.exec(query).all()
            
            result = []
            for user in users:
                # Get user's resume
                resume = self.session.exec(
                    select(Resume).where(Resume.user_id == user.user_id).limit(1)
                ).first()
                
                user_data = {
                    "user_id": user.user_id,
                    "name": user.full_name,
                    "email": user.email if user.is_verified else "***hidden***",
                    "phone": user.phone_number if user.is_verified else "***hidden***",
                    "bio": user.bio,
                    "role": user.role,
                    "is_verified": user.is_verified,
                    "has_resume": bool(resume)
                }
                
                if resume:
                    user_data.update({
                        "location": resume.location,
                        "skills": json.loads(resume.skills) if isinstance(resume.skills, str) else [],
                        "experience": resume.experience
                    })
                
                result.append(user_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def increment_profile_views(self, resume_id: int) -> None:
        """Increment view count for a profile"""
        try:
            resume = self.session.get(Resume, resume_id)
            if resume:
                resume.views_count += 1
                self.session.add(resume)
                self.session.commit()
                logger.info(f"Incremented views for resume {resume_id}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error incrementing views: {e}")

def get_chatbot_search_service(session: Session) -> ChatbotSearchService:
    """Factory function for ChatbotSearchService"""
    return ChatbotSearchService(session)
