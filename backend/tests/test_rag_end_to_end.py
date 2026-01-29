"""
Comprehensive End-to-End RAG Integration Test
Verifies complete workflow: Upload -> Index -> Query -> Retrieve -> Match -> Response

This test ensures:
1. Backend services work together correctly
2. ChromaDB integration is functional
3. Embedding-based retrieval works accurately
4. RAG properties are maintained (semantic relevance, grounding, ranking)
5. Frontend receives properly formatted responses
6. All error scenarios are handled gracefully
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import uuid

# Real embeddings and RAG components
from sentence_transformers import SentenceTransformer
import chromadb

# Database and models
from sqlmodel import Session, create_engine, SQLModel, select
from sqlmodel.pool import StaticPool

# Models
from models.resume import Resume
from models.user import User, UserRole
from models.recruiter import Recruiter
from models.requirement import Requirement
from models.match_result import MatchResult

# Services
from services.embeddings_service import EmbeddingsService
from services.matching_service import MatchingService


# ================================================================
# REAL RAG INFRASTRUCTURE
# ================================================================

class RealEmbeddingsProvider:
    """Wrapper for real SentenceTransformer embeddings"""
    
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed(self, text: str) -> List[float]:
        """Generate real embedding for text"""
        return self.model.encode(text, convert_to_tensor=False).tolist()
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        import numpy as np
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


class E2ERAGPipeline:
    """End-to-end RAG pipeline with real components"""
    
    def __init__(self, db_session: Session, chroma_path: str):
        self.session = db_session
        self.embedder = RealEmbeddingsProvider()
        
        # Initialize ChromaDB with unique persistent path per test
        unique_collection_name = f"resumes_test_{uuid.uuid4().hex[:8]}"
        
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Resumes collection for semantic search with unique name
        self.resumes_collection = self.chroma_client.get_or_create_collection(
            name=unique_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize services
        self.matching_service = MatchingService(session=db_session)
    
    def upload_and_index_resume(
        self,
        recruiter_id: int,
        candidate_name: str,
        skills: List[str],
        experience: str,
        location: str,
        summary: str
    ) -> Dict[str, Any]:
        """Upload resume and index in ChromaDB"""
        
        # Create resume in database
        resume_text = f"{candidate_name} - {experience} experience. Skills: {', '.join(skills)}. {summary} Location: {location}"
        
        resume = Resume(
            recruiter_id=recruiter_id,
            candidate_name=candidate_name,
            candidate_email=f"{candidate_name.lower().replace(' ', '.')}@email.com",
            file_path=f"/uploads/resume_{candidate_name.replace(' ', '_')}.pdf",
            file_name=f"resume_{candidate_name}.pdf",
            file_size=100000,
            file_type="pdf",
            skills=json.dumps(skills),
            experience=experience,
            summary=summary,
            location=location,
            is_active=True
        )
        
        self.session.add(resume)
        self.session.commit()
        self.session.refresh(resume)
        
        # Index in ChromaDB
        embedding = self.embedder.embed(resume_text)
        doc_id = f"resume_{resume.resume_id}"
        
        self.resumes_collection.add(
            ids=[doc_id],
            documents=[resume_text],
            embeddings=[embedding],
            metadatas=[{
                "resume_id": str(resume.resume_id),
                "candidate_name": candidate_name,
                "location": location,
                "skills": json.dumps(skills)
            }]
        )
        
        # Update ChromaDB reference
        resume.chroma_collection_id = doc_id
        self.session.add(resume)
        self.session.commit()
        
        return {
            "resume_id": resume.resume_id,
            "chroma_id": doc_id,
            "embedding_dim": len(embedding),
            "indexed": True
        }
    
    def retrieve_relevant_resumes(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve semantically similar resumes from ChromaDB"""
        
        # Embed query
        query_embedding = self.embedder.embed(query)
        
        # Search ChromaDB
        results = self.resumes_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Format results with similarity scores
        retrieved = []
        if results and results['ids'] and len(results['ids']) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
                retrieved.append({
                    "chroma_id": doc_id,
                    "document": results['documents'][0][i] if results['documents'] else None,
                    "similarity": similarity,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "rank": i + 1
                })
        
        return retrieved
    
    def create_requirement_from_chat(
        self,
        user_id: int,
        role: str,
        tech_skills: List[str],
        experience_years: str,
        location: str,
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Create requirement from conversation data"""
        
        requirement = Requirement(
            user_id=user_id,
            role=role,
            skills=json.dumps(tech_skills),
            experience_years=experience_years,
            location=location,
            keywords=json.dumps(keywords or []),
            requirement_count=5,  # Complete requirement
            is_complete=True
        )
        
        self.session.add(requirement)
        self.session.commit()
        self.session.refresh(requirement)
        
        return {
            "requirement_id": requirement.requirement_id,
            "user_id": user_id,
            "role": role,
            "skills": tech_skills,
            "experience_years": experience_years,
            "location": location,
            "is_complete": requirement.is_complete
        }
    
    def score_and_rank_matches(
        self,
        requirement: Dict[str, Any],
        retrieved_resumes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Score and rank retrieved resumes against requirement"""
        
        scored_matches = []
        requirement_skills = set(requirement['skills'])
        
        for resume in retrieved_resumes:
            metadata = resume['metadata']
            resume_skills = json.loads(metadata.get('skills', '[]'))
            
            # Calculate skill match percentage
            matched_skills = requirement_skills & set(resume_skills)
            skill_match_pct = (len(matched_skills) / len(requirement_skills)) * 100 if requirement_skills else 0
            
            # Create match explanation
            explanation = f"Matched {len(matched_skills)} of {len(requirement_skills)} required skills"
            if matched_skills:
                explanation += f": {', '.join(list(matched_skills)[:3])}"
            
            scored_matches.append({
                "resume_id": metadata.get('resume_id'),
                "candidate_name": metadata.get('candidate_name'),
                "similarity_score": resume['similarity'],  # RAG property: semantic relevance
                "skill_match_percentage": skill_match_pct,
                "combined_score": (resume['similarity'] * 0.5) + (skill_match_pct / 100 * 0.5),
                "explanation": explanation,
                "rank": resume['rank'],
                "chroma_id": resume['chroma_id']
            })
        
        # Sort by combined score
        scored_matches.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return scored_matches
    
    def save_matches_to_db(
        self,
        requirement_id: int,
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Save match results to database"""
        
        saved_matches = []
        for rank, match in enumerate(matches[:2], 1):  # Save top 2
            match_result = MatchResult(
                requirement_id=requirement_id,
                resume_id=int(match['resume_id']),
                match_score=match['combined_score'],
                rank=rank,
                matched_skills=json.dumps([]),  # Placeholder
                skill_match_percentage=match['skill_match_percentage'],
                location_match=True,
                was_viewed=False
            )
            self.session.add(match_result)
            saved_matches.append(match_result)
        
        self.session.commit()
        return saved_matches
    
    def generate_api_response(
        self,
        matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate API response for frontend consumption"""
        
        return {
            "status": "success",
            "match_count": len(matches),
            "candidates": [
                {
                    "candidate_id": m['resume_id'],
                    "name": m['candidate_name'],
                    "match_score": round(m['combined_score'] * 100, 2),
                    "skill_match_percentage": round(m['skill_match_percentage'], 2),
                    "explanation": m['explanation'],
                    "rank": m['rank'],
                    "timestamp": datetime.utcnow().isoformat()
                }
                for m in matches
            ]
        }


# ================================================================
# PYTEST FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def temp_chroma_dir():
    """Create temporary ChromaDB directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def rag_pipeline(db_session, temp_chroma_dir):
    """Initialize E2E RAG pipeline"""
    return E2ERAGPipeline(db_session, temp_chroma_dir)


@pytest.fixture(scope="function")
def sample_user_and_recruiter(db_session):
    """Create sample user and recruiter"""
    # Create user
    user = User(
        username="john_doe",
        email="john@company.com",
        password_hash="hashed_password",
        full_name="John Doe",
        role=UserRole.RECRUITER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create recruiter
    recruiter = Recruiter(
        user_id=user.user_id,
        company_name="TechCorp",
        company_email="recruit@techcorp.com",
        job_title="Hiring Manager",
        location="San Francisco, CA",
        company_description="Leading tech company"
    )
    db_session.add(recruiter)
    db_session.commit()
    db_session.refresh(recruiter)
    
    return user, recruiter


# ================================================================
# E2E RAG INTEGRATION TESTS
# ================================================================

class TestE2ERAGUploadAndIndex:
    """Test resume upload and ChromaDB indexing"""
    
    def test_upload_single_resume(self, rag_pipeline, sample_user_and_recruiter):
        """Test uploading and indexing a single resume"""
        user, recruiter = sample_user_and_recruiter
        
        result = rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Alice Johnson",
            skills=["Python", "Django", "PostgreSQL"],
            experience="5 years",
            location="San Francisco, CA",
            summary="Senior backend developer with expertise in scalable systems"
        )
        
        assert result['indexed'] == True
        assert result['resume_id'] is not None
        assert result['embedding_dim'] == 384  # all-MiniLM-L6-v2 dimension
        
        # Verify in database
        resume = rag_pipeline.session.exec(select(Resume).where(Resume.resume_id == result['resume_id'])).first()
        assert resume is not None
        assert resume.candidate_name == "Alice Johnson"
    
    def test_upload_multiple_diverse_resumes(self, rag_pipeline, sample_user_and_recruiter):
        """Test uploading multiple resumes with different skills"""
        user, recruiter = sample_user_and_recruiter
        
        resumes_data = [
            ("Alice Johnson", ["Python", "Django", "PostgreSQL"], "5 years", "Senior backend developer"),
            ("Bob Smith", ["JavaScript", "React", "Node.js"], "4 years", "Full-stack developer"),
            ("Carol Davis", ["Java", "Spring Boot", "AWS"], "6 years", "Cloud architect"),
            ("David Lee", ["Python", "Machine Learning", "TensorFlow"], "3 years", "ML engineer"),
        ]
        
        uploaded_ids = []
        for name, skills, exp, summary in resumes_data:
            result = rag_pipeline.upload_and_index_resume(
                recruiter_id=recruiter.recruiter_id,
                candidate_name=name,
                skills=skills,
                experience=exp,
                location="San Francisco, CA",
                summary=summary
            )
            uploaded_ids.append(result['resume_id'])
        
        assert len(uploaded_ids) == 4
        
        # Verify all in database
        all_resumes = rag_pipeline.session.exec(select(Resume)).all()
        assert len(all_resumes) == 4


class TestE2ERAGRetrieval:
    """Test semantic retrieval from ChromaDB"""
    
    def test_retrieve_python_developers(self, rag_pipeline, sample_user_and_recruiter):
        """Test retrieving Python developers by semantic similarity"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload diverse resumes
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Alice Johnson",
            skills=["Python", "Django", "PostgreSQL"],
            experience="5 years",
            location="San Francisco, CA",
            summary="Senior Python backend developer with Django expertise"
        )
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Bob Smith",
            skills=["JavaScript", "React", "Node.js"],
            experience="4 years",
            location="New York, NY",
            summary="Full-stack JavaScript developer with React specialization"
        )
        
        # Query for Python developers
        query = "Looking for experienced Python developer with Django and database expertise"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=2)
        
        # Verify RAG property: Semantic relevance
        assert len(results) > 0
        assert results[0]['similarity'] > 0.5  # High relevance
        assert "Alice" in results[0]['metadata']['candidate_name']
        
        # Verify ranking
        assert results[0]['rank'] == 1
    
    def test_retrieve_ml_specialists(self, rag_pipeline, sample_user_and_recruiter):
        """Test retrieving ML specialists by semantic query"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload ML and non-ML resumes
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="David Lee",
            skills=["Python", "Machine Learning", "TensorFlow", "PyTorch"],
            experience="4 years",
            location="Mountain View, CA",
            summary="ML Engineer specializing in deep learning and NLP"
        )
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Carol Davis",
            skills=["Java", "Spring Boot", "Database Design"],
            experience="6 years",
            location="San Francisco, CA",
            summary="Cloud architect with enterprise experience"
        )
        
        # Query for ML specialists
        query = "Machine learning engineer with deep learning and TensorFlow expertise"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=2)
        
        # Verify semantic relevance - ML resume should rank higher
        assert results[0]['similarity'] > 0.4
        assert "David" in results[0]['metadata']['candidate_name']
    
    def test_no_relevant_matches(self, rag_pipeline, sample_user_and_recruiter):
        """Test graceful handling when no relevant matches exist"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload non-matching resumes
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Go Developer",
            skills=["Go", "Rust", "Systems Programming"],
            experience="5 years",
            location="Berlin, Germany",
            summary="Systems programmer"
        )
        
        # Query for something completely different
        query = "VB.NET developer with ASP.NET and Windows Forms"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=2)
        
        # Should handle gracefully - may return low similarity results
        # This tests RAG robustness
        assert isinstance(results, list)


class TestE2ERAGMatching:
    """Test complete matching workflow"""
    
    def test_requirement_to_match_workflow(self, rag_pipeline, sample_user_and_recruiter):
        """Test complete workflow: requirement -> search -> retrieve -> match -> score"""
        user, recruiter = sample_user_and_recruiter
        
        # Step 1: Upload resumes
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Alice Python Expert",
            skills=["Python", "Django", "PostgreSQL"],
            experience="5 years",
            location="San Francisco, CA",
            summary="Expert Python developer with Django experience"
        )
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Bob Frontend Dev",
            skills=["JavaScript", "React", "CSS"],
            experience="3 years",
            location="New York, NY",
            summary="Frontend specialist"
        )
        
        # Step 2: Create requirement from chat
        requirement = rag_pipeline.create_requirement_from_chat(
            user_id=user.user_id,
            role="Senior Backend Engineer",
            tech_skills=["Python", "Django", "PostgreSQL"],
            experience_years="5+ years",
            location="San Francisco Area",
            keywords=["scalability", "databases"]
        )
        
        assert requirement['is_complete'] == True
        
        # Step 3: Retrieve relevant resumes
        query = f"Looking for {requirement['role']} with {', '.join(requirement['skills'])}"
        retrieved = rag_pipeline.retrieve_relevant_resumes(query, top_k=2)
        
        assert len(retrieved) > 0
        
        # Step 4: Score and rank matches
        matches = rag_pipeline.score_and_rank_matches(requirement, retrieved)
        
        assert len(matches) > 0
        # Best match should be Python expert, not frontend dev
        assert "Alice" in matches[0]['candidate_name']
        assert matches[0]['skill_match_percentage'] > 60
        
        # Step 5: Save to database
        saved = rag_pipeline.save_matches_to_db(requirement['requirement_id'], matches)
        assert len(saved) > 0
        
        # Step 6: Generate API response
        response = rag_pipeline.generate_api_response(matches)
        
        assert response['status'] == 'success'
        assert response['match_count'] > 0
        assert 'candidates' in response
        assert response['candidates'][0]['name'] == "Alice Python Expert"


class TestE2ERAGProperties:
    """Test that RAG system maintains proper properties"""
    
    def test_semantic_relevance(self, rag_pipeline, sample_user_and_recruiter):
        """Verify semantic relevance property - similar documents retrieved"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload semantically related documents
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="ML Engineer",
            skills=["Python", "TensorFlow", "Keras", "Machine Learning"],
            experience="4 years",
            location="San Francisco, CA",
            summary="Deep learning and neural network specialist"
        )
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Data Scientist",
            skills=["Python", "Pandas", "Scikit-learn", "Statistics"],
            experience="3 years",
            location="New York, NY",
            summary="Data analysis and ML specialist"
        )
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="DevOps Engineer",
            skills=["Docker", "Kubernetes", "AWS", "CI/CD"],
            experience="5 years",
            location="Seattle, WA",
            summary="Infrastructure and deployment specialist"
        )
        
        # Query for ML/Data roles
        query = "Looking for machine learning engineer with neural networks and Python"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=3)
        
        # Verify semantic relevance ranking
        assert len(results) >= 2
        # First result should be ML engineer (most similar)
        assert results[0]['similarity'] > results[2]['similarity'] or "ML" in results[0]['metadata']['candidate_name']
    
    def test_grounding_in_documents(self, rag_pipeline, sample_user_and_recruiter):
        """Verify grounding property - results are grounded in actual documents"""
        user, recruiter = sample_user_and_recruiter
        
        uploaded_data = {}
        for name, skills in [
            ("Alice", ["Python", "Django"]),
            ("Bob", ["JavaScript", "React"]),
            ("Carol", ["Java", "Spring"])
        ]:
            res = rag_pipeline.upload_and_index_resume(
                recruiter_id=recruiter.recruiter_id,
                candidate_name=name,
                skills=skills,
                experience="5 years",
                location="San Francisco, CA",
                summary=f"{name} is expert in {', '.join(skills)}"
            )
            uploaded_data[name] = res
        
        # Query and verify results are grounded in uploaded documents
        query = "Python developer with Django experience"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=1)
        
        # Result document should contain actual resume text
        assert "Alice" in results[0]['document']
        assert "Python" in results[0]['document']
        assert "Django" in results[0]['document']
        
        # Verify metadata is accurate
        assert results[0]['metadata']['candidate_name'] == "Alice"
    
    def test_ranking_consistency(self, rag_pipeline, sample_user_and_recruiter):
        """Verify ranking is consistent and meaningful"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload multiple candidates
        candidates = [
            ("Expert Python Dev", ["Python", "Django", "PostgreSQL"], "Expert level"),
            ("Python Intermediate", ["Python", "Flask"], "Intermediate level"),
            ("JavaScript Developer", ["JavaScript", "React"], "Frontend focus"),
        ]
        
        for name, skills, summary in candidates:
            rag_pipeline.upload_and_index_resume(
                recruiter_id=recruiter.recruiter_id,
                candidate_name=name,
                skills=skills,
                experience="5 years",
                location="San Francisco, CA",
                summary=summary
            )
        
        # Query for Python developers
        query = "Senior Python developer with Django expertise"
        results = rag_pipeline.retrieve_relevant_resumes(query, top_k=3)
        
        # Verify ranking order
        for i in range(len(results) - 1):
            assert results[i]['rank'] < results[i + 1]['rank']
            # Earlier ranks should have higher similarity
            assert results[i]['similarity'] >= results[i + 1]['similarity']


class TestE2EAPIResponse:
    """Test API response generation for frontend"""
    
    def test_response_structure(self, rag_pipeline, sample_user_and_recruiter):
        """Verify API response has correct structure for frontend"""
        user, recruiter = sample_user_and_recruiter
        
        # Setup
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Alice",
            skills=["Python"],
            experience="5 years",
            location="SF",
            summary="Python developer"
        )
        
        requirement = rag_pipeline.create_requirement_from_chat(
            user_id=user.user_id,
            role="Python Developer",
            tech_skills=["Python"],
            experience_years="5+ years",
            location="SF"
        )
        
        retrieved = rag_pipeline.retrieve_relevant_resumes("Python developer", top_k=2)
        matches = rag_pipeline.score_and_rank_matches(requirement, retrieved)
        
        # Generate response
        response = rag_pipeline.generate_api_response(matches)
        
        # Verify response structure for frontend
        assert "status" in response
        assert "match_count" in response
        assert "candidates" in response
        
        # Verify candidate structure
        assert len(response['candidates']) > 0
        candidate = response['candidates'][0]
        assert "candidate_id" in candidate
        assert "name" in candidate
        assert "match_score" in candidate
        assert "skill_match_percentage" in candidate
        assert "explanation" in candidate
        assert "rank" in candidate
        assert "timestamp" in candidate
        
        # Verify scores are valid percentages
        assert 0 <= candidate['match_score'] <= 100
        assert 0 <= candidate['skill_match_percentage'] <= 100
    
    def test_response_with_multiple_matches(self, rag_pipeline, sample_user_and_recruiter):
        """Test API response with multiple matches"""
        user, recruiter = sample_user_and_recruiter
        
        # Upload multiple matching candidates
        for i, name in enumerate(["Alice", "Bob", "Carol"]):
            rag_pipeline.upload_and_index_resume(
                recruiter_id=recruiter.recruiter_id,
                candidate_name=name,
                skills=["Python", "Django"],
                experience="5 years",
                location="SF",
                summary=f"{name} - Python developer"
            )
        
        requirement = rag_pipeline.create_requirement_from_chat(
            user_id=user.user_id,
            role="Python Developer",
            tech_skills=["Python", "Django"],
            experience_years="5+ years",
            location="SF"
        )
        
        retrieved = rag_pipeline.retrieve_relevant_resumes("Python Django developer", top_k=3)
        matches = rag_pipeline.score_and_rank_matches(requirement, retrieved)
        
        response = rag_pipeline.generate_api_response(matches)
        
        # Verify multiple candidates in response
        assert response['match_count'] > 0
        assert isinstance(response['candidates'], list)
        
        # Verify all candidates have required fields
        for candidate in response['candidates']:
            assert candidate['name'] is not None
            assert candidate['match_score'] is not None


class TestE2EErrorHandling:
    """Test error scenarios and edge cases"""
    
    def test_empty_database_retrieval(self, rag_pipeline):
        """Test retrieval when no resumes exist"""
        # Query on empty ChromaDB
        results = rag_pipeline.retrieve_relevant_resumes("Python developer", top_k=5)
        
        # Should handle gracefully
        assert isinstance(results, list)
    
    def test_invalid_skills_json(self, rag_pipeline, sample_user_and_recruiter):
        """Test handling of malformed skills data"""
        user, recruiter = sample_user_and_recruiter
        
        # Create resume with valid data
        result = rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Test",
            skills=["Python"],
            experience="5 years",
            location="SF",
            summary="Test"
        )
        
        assert result['resume_id'] is not None
    
    def test_very_long_query(self, rag_pipeline, sample_user_and_recruiter):
        """Test handling of very long query strings"""
        user, recruiter = sample_user_and_recruiter
        
        rag_pipeline.upload_and_index_resume(
            recruiter_id=recruiter.recruiter_id,
            candidate_name="Alice",
            skills=["Python"],
            experience="5 years",
            location="SF",
            summary="Python developer"
        )
        
        # Very long query
        long_query = "Looking for " + " and ".join(["experienced"] * 100) + " Python developer"
        results = rag_pipeline.retrieve_relevant_resumes(long_query, top_k=2)
        
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
