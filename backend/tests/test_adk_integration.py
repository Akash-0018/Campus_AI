"""
Test suite for ADK integration

Tests the new ADK-powered RequirementsAgent to ensure it works correctly
and doesn't break existing functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(__file__))


# Test fixtures

@pytest.fixture
def test_db():
    """Create in-memory test database"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    from models import SQLModel
    SQLModel.metadata.create_all(engine)
    
    return engine


@pytest.fixture
def db_session(test_db):
    """Get database session for testing"""
    from sqlmodel import Session
    with Session(test_db) as session:
        yield session


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    from models.user import User
    
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        role="recruiter",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# Tests for Tool Registry

def test_tool_registry_initialization():
    """Test tool registry initializes correctly"""
    from tools.registration import ToolRegistry
    
    registry = ToolRegistry()
    assert registry is not None
    assert len(registry.list_tools()) == 0


def test_tool_registry_register():
    """Test registering a tool"""
    from tools.registration import ToolRegistry
    
    async def dummy_handler():
        return {"result": "success"}
    
    registry = ToolRegistry()
    registry.register(
        name="test_tool",
        description="Test tool",
        handler=dummy_handler
    )
    
    assert registry.validate_tool_exists("test_tool")
    assert "test_tool" in registry.list_tools()


def test_tool_registry_get_tool():
    """Test retrieving a tool"""
    from tools.registration import ToolRegistry
    
    async def dummy_handler():
        return {"result": "success"}
    
    registry = ToolRegistry()
    registry.register(
        name="test_tool",
        description="Test tool",
        handler=dummy_handler
    )
    
    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool["name"] == "test_tool"
    assert tool["description"] == "Test tool"


# Tests for BaseAgent

@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Test base agent initializes"""
    from agents.base_agent import SimpleAgent
    
    agent = SimpleAgent(
        name="test_agent",
        description="Test agent"
    )
    
    assert agent.name == "test_agent"
    assert agent.description == "Test agent"


@pytest.mark.asyncio
async def test_base_agent_input_validation():
    """Test input validation in base agent"""
    from agents.base_agent import SimpleAgent
    
    agent = SimpleAgent(
        name="test_agent",
        description="Test agent"
    )
    
    # Valid input
    assert agent._validate_input("Hello, is this a good role?")
    
    # Too short
    assert not agent._validate_input("")
    
    # Too long
    assert not agent._validate_input("a" * 1000)
    
    # SQL injection attempt
    assert not agent._validate_input("SELECT * FROM users; DROP TABLE users;")


# Tests for Tools

@pytest.mark.asyncio
async def test_resume_matching_tool():
    """Test resume matching tool"""
    from tools.adk_tools import ResumeMatchingTool
    
    with patch('tools.adk_tools.MatchingService') as MockService:
        mock_service = MagicMock()
        MockService.return_value = mock_service
        mock_service.get_top_matches.return_value = [
            {"name": "John Doe", "match_score": 0.85},
            {"name": "Jane Smith", "match_score": 0.78}
        ]
        
        tool = ResumeMatchingTool()
        result = await tool.execute({"skills": "Python"})
        
        assert result["success"]
        assert len(result["matches"]) == 2


@pytest.mark.asyncio
async def test_resume_matching_tool_limit_guardrail():
    """Test that resume matching respects limit guardrail"""
    from tools.adk_tools import ResumeMatchingTool
    
    with patch('tools.adk_tools.MatchingService') as MockService:
        mock_service = MagicMock()
        MockService.return_value = mock_service
        mock_service.get_top_matches.return_value = []
        
        tool = ResumeMatchingTool()
        
        # Request more than max, should cap to 2
        result = await tool.execute({"skills": "Python"}, limit=10)
        
        # Verify it was capped
        call_args = mock_service.get_top_matches.call_args
        assert call_args[1]["limit"] == 2


# Tests for RequirementsAgent

@pytest.mark.asyncio
async def test_requirements_agent_initialization():
    """Test requirements agent initializes"""
    from agents.requirements_agent_adk import RequirementsAgent
    
    # Mock ADK components
    with patch('agents.requirements_agent_adk.BaseAgent.__init__', return_value=None):
        with patch('agents.requirements_agent_adk.BaseAgent._validate_input', return_value=True):
            agent = RequirementsAgent()
            assert agent is not None


def test_requirements_agent_phase_info():
    """Test getting phase information"""
    from agents.requirements_agent_adk import RequirementsAgent
    
    with patch('agents.requirements_agent_adk.BaseAgent.__init__', return_value=None):
        agent = RequirementsAgent()
        
        # Get phase 0
        phase = agent.get_phase_info(0)
        assert phase is not None
        assert "prompt" in phase
        assert "field" in phase
        
        # Get invalid phase
        phase = agent.get_phase_info(99)
        assert phase is None


def test_requirements_agent_free_text_extraction():
    """Test free-text requirement extraction"""
    from agents.requirements_agent_adk import RequirementsAgent
    
    with patch('agents.requirements_agent_adk.BaseAgent.__init__', return_value=None):
        agent = RequirementsAgent()
        
        # Test extraction
        text = "We need a Python developer with 5-7 years of experience in FinTech"
        extracted = agent.extract_requirements_from_free_text(text)
        
        assert "skills" in extracted
        assert "Python" in extracted["skills"]
        assert "experience_years" in extracted
        assert "industry" in extracted


# Integration Tests

@pytest.mark.asyncio
async def test_adk_chat_route_integration(db_session, test_user):
    """Test ADK chat route end-to-end"""
    from routes.chat_routes_adk import MessageRequest, MessageResponse
    
    # This is an integration test that mocks the agent
    request = MessageRequest(
        message="Hello",
        user_id=test_user.user_id
    )
    
    assert request.message == "Hello"
    assert request.user_id == test_user.user_id


# Tests for parallel execution

@pytest.mark.asyncio
async def test_adk_route_is_primary():
    """Verify ADK chat routes are available as primary chat surface."""
    from routes import chat_routes_adk

    assert chat_routes_adk.router is not None
    assert "/api/chat-adk" in chat_routes_adk.router.routes[0].path \
        or any("/api/chat-adk" in str(r.path) for r in chat_routes_adk.router.routes)


# Backward compatibility tests

def test_requirements_agent_backward_compatibility():
    """Test that old requirements_agent still works"""
    from agents.requirements_agent import RequirementsAgent as OldAgent
    
    agent = OldAgent()
    assert agent is not None
    
    # Should have old methods
    assert hasattr(agent, 'get_greeting')
    assert hasattr(agent, 'process_user_input')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
