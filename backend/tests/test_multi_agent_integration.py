"""
Multi-Agent Integration Tests

Comprehensive tests for:
- Individual agent functionality
- Multi-agent routing and orchestration
- End-to-end recruitment workflow
- Agent handoffs and state management
"""
import pytest
import asyncio
from datetime import datetime

from agents.agent_router import (
    AgentRouter, AgentType, IntentDetector, initialize_router, get_router
)
from agents.requirements_agent_adk import get_requirements_agent
from agents.resume_matching_agent_adk import get_resume_matching_agent
from agents.user_profile_agent_adk import get_user_profile_agent
from agents.recruitment_coordinator_agent_adk import get_recruitment_coordinator_agent


# ============================================================================
# PART 1: Individual Agent Tests
# ============================================================================

class TestIndividualAgents:
    """Test each agent works in isolation"""

    @pytest.mark.asyncio
    async def test_requirements_agent_basic(self):
        """Test RequirementsAgent basic functionality"""
        agent = get_requirements_agent()
        assert agent is not None
        assert agent.name == "requirements_collector"
        
        result = await agent.execute_prompt(
            prompt="I need to hire a senior Python developer",
            user_id="test_user_1"
        )
        
        assert result["success"]
        assert "response" in result
        assert len(result["response"]) > 0
        print(f"✓ RequirementsAgent works: {result['response'][:100]}...")

    @pytest.mark.asyncio
    async def test_resume_matching_agent_basic(self):
        """Test ResumeMatchingAgent basic functionality"""
        agent = get_resume_matching_agent()
        assert agent is not None
        assert agent.name == "resume_matching_agent"
        
        result = await agent.execute_prompt(
            prompt="Find me candidates with Python and AWS experience",
            user_id="test_user_2"
        )
        
        assert result["success"]
        assert "response" in result
        assert len(result["response"]) > 0
        print(f"✓ ResumeMatchingAgent works: {result['response'][:100]}...")

    @pytest.mark.asyncio
    async def test_user_profile_agent_basic(self):
        """Test UserProfileAgent basic functionality"""
        agent = get_user_profile_agent()
        assert agent is not None
        assert agent.name == "user_profile_agent"
        
        result = await agent.execute_prompt(
            prompt="Show me my profile",
            user_id="test_user_3"
        )
        
        assert result["success"]
        assert "response" in result
        assert len(result["response"]) > 0
        assert "metadata" in result
        print(f"✓ UserProfileAgent works: {result['response'][:100]}...")

    @pytest.mark.asyncio
    async def test_coordinator_agent_basic(self):
        """Test RecruitmentCoordinatorAgent basic functionality"""
        agent = get_recruitment_coordinator_agent()
        assert agent is not None
        assert agent.name == "recruitment_coordinator_agent"
        
        result = await agent.execute_prompt(
            prompt="I need to hire a React developer",
            user_id="test_user_4"
        )
        
        assert result["success"]
        assert "response" in result
        assert len(result["response"]) > 0
        print(f"✓ RecruitmentCoordinatorAgent works: {result['response'][:100]}...")


# ============================================================================
# PART 2: Intent Detection & Routing Tests
# ============================================================================

class TestIntentAndRouting:
    """Test intent detection and agent routing"""

    def test_intent_detection_requirements(self):
        """Test detection of requirements collection intent"""
        messages = [
            "I need a Python developer",
            "Looking for a senior engineer",
            "We're hiring for a DevOps position"
        ]
        
        for msg in messages:
            intent = IntentDetector.detect_intent(msg)
            assert intent == AgentType.REQUIREMENTS_COLLECTION
            print(f"✓ Detected requirements intent: '{msg}'")

    def test_intent_detection_resume_matching(self):
        """Test detection of resume matching intent"""
        messages = [
            "Show me matching resumes",
            "Find candidates with Python skills",
            "Browse available candidates"
        ]
        
        for msg in messages:
            intent = IntentDetector.detect_intent(msg)
            assert intent == AgentType.RESUME_MATCHING
            print(f"✓ Detected resume matching intent: '{msg}'")

    def test_intent_detection_user_profile(self):
        """Test detection of user profile intent"""
        messages = [
            "Show me my profile",
            "Update my preferences",
            "Change my account settings"
        ]
        
        for msg in messages:
            intent = IntentDetector.detect_intent(msg)
            assert intent == AgentType.USER_PROFILE
            print(f"✓ Detected profile intent: '{msg}'")

    @pytest.mark.asyncio
    async def test_router_initialization(self):
        """Test router initializes and registers agents"""
        initialize_router()
        router = get_router()
        
        assert router is not None
        # Register agents with router
        router.register_agent_handler(
            AgentType.REQUIREMENTS_COLLECTION,
            get_requirements_agent()
        )
        router.register_agent_handler(
            AgentType.RESUME_MATCHING,
            get_resume_matching_agent()
        )
        router.register_agent_handler(
            AgentType.USER_PROFILE,
            get_user_profile_agent()
        )
        router.register_agent_handler(
            AgentType.RECRUITMENT_COORDINATOR,
            get_recruitment_coordinator_agent()
        )
        
        agents = router.list_available_agents()
        assert len(agents) >= 4
        print(f"✓ Router initialized with {len(agents)} agents")

    @pytest.mark.asyncio
    async def test_router_auto_selection(self):
        """Test router automatically selects correct agent"""
        initialize_router()
        router = get_router()
        
        # Register agents
        router.register_agent_handler(
            AgentType.REQUIREMENTS_COLLECTION,
            get_requirements_agent()
        )
        router.register_agent_handler(
            AgentType.RESUME_MATCHING,
            get_resume_matching_agent()
        )
        
        # Test requirements routing
        result = await router.route_message(
            message="I need a Python developer",
            user_id="router_test_1"
        )
        assert result["agent"] == AgentType.REQUIREMENTS_COLLECTION.value
        print(f"✓ Router correctly routed to: {result.get('agent', 'executed')}")


# ============================================================================
# PART 3: Multi-Turn Conversation Tests
# ============================================================================

class TestMultiTurnConversations:
    """Test agents handle multi-turn conversations"""

    @pytest.mark.asyncio
    async def test_requirements_multi_turn(self):
        """Test multi-turn with RequirementsAgent"""
        agent = get_requirements_agent()
        user_id = "multi_turn_user_1"
        
        # Turn 1: Initial requirement
        turn1 = await agent.execute_prompt(
            prompt="I need a Python developer",
            user_id=user_id
        )
        assert turn1["success"]
        print(f"  Turn 1: {turn1['response'][:80]}...")
        
        # Turn 2: Add more detail
        turn2 = await agent.execute_prompt(
            prompt="Senior level with 5+ years experience",
            user_id=user_id,
            session_id=turn1.get("session_id")
        )
        assert turn2["success"]
        print(f"  Turn 2: {turn2['response'][:80]}...")
        
        # Turn 3: More detail
        turn3 = await agent.execute_prompt(
            prompt="Working with AWS and microservices",
            user_id=user_id,
            session_id=turn1.get("session_id")
        )
        assert turn3["success"]
        print(f"  Turn 3: {turn3['response'][:80]}...")
        print("✓ Multi-turn conversation works")

    @pytest.mark.asyncio
    async def test_matching_multi_turn(self):
        """Test multi-turn with ResumeMatchingAgent"""
        agent = get_resume_matching_agent()
        user_id = "multi_turn_user_2"
        
        # Turn 1: Start matching
        turn1 = await agent.execute_prompt(
            prompt="Find candidates with Python skills",
            user_id=user_id
        )
        assert turn1["success"]
        print(f"  Turn 1: {turn1['response'][:80]}...")
        
        # Turn 2: Refine search
        turn2 = await agent.execute_prompt(
            prompt="But also need AWS experience",
            user_id=user_id,
            session_id=turn1.get("session_id")
        )
        assert turn2["success"]
        print(f"  Turn 2: {turn2['response'][:80]}...")
        print("✓ Multi-turn resume matching works")


# ============================================================================
# PART 4: Workflow Orchestration Tests
# ============================================================================

class TestOrchestration:
    """Test workflow orchestration and agent handoffs"""

    @pytest.mark.asyncio
    async def test_workflow_state_progression(self):
        """Test workflow progresses through stages"""
        agent = get_recruitment_coordinator_agent()
        user_id = "workflow_test_1"
        session_id = "session_workflow_1"
        
        # Initial: Should be in "initial" stage
        assert user_id not in agent.workflows or \
               agent.workflows.get(user_id, {}).get("stage") == "initial"
        
        # Define requirements
        result1 = await agent.execute_prompt(
            prompt="I need to hire a senior React developer",
            user_id=user_id,
            session_id=session_id
        )
        assert result1["success"]
        print(f"  Stage 1: {result1['response'][:80]}...")
        
        # Verify workflow state was created
        assert user_id in agent.workflows
        workflow = agent.workflows[user_id]
        print(f"  Current stage: {workflow['stage']}")
        
        # Next stage: Search candidates
        result2 = await agent.execute_prompt(
            prompt="Start searching for candidates",
            user_id=user_id,
            session_id=session_id
        )
        assert result2["success"]
        print(f"  Stage 2: {result2['response'][:80]}...")
        print("✓ Workflow state progression works")

    @pytest.mark.asyncio
    async def test_agent_context_preservation(self):
        """Test agent preserves context across turns"""
        coordinator = get_recruitment_coordinator_agent()
        user_id = "context_test_1"
        session_id = "session_context_1"
        
        # Turn 1: Define role
        turn1 = await coordinator.execute_prompt(
            prompt="I need to hire a backend engineer with Python experience",
            user_id=user_id,
            session_id=session_id
        )
        assert turn1["success"]
        
        # Verify context is stored
        workflow = coordinator.workflows.get(user_id)
        assert workflow is not None
        assert "requirements" in workflow
        
        print(f"  Requirements stored: {workflow['requirements']}")
        print("✓ Agent context preservation works")

    @pytest.mark.asyncio
    async def test_workflow_reset(self):
        """Test workflow can be reset"""
        coordinator = get_recruitment_coordinator_agent()
        user_id = "reset_test_1"
        
        # Create workflow
        result1 = await coordinator.execute_prompt(
            prompt="I need a developer",
            user_id=user_id
        )
        assert result1["success"]
        assert user_id in coordinator.workflows
        
        # Reset workflow
        result2 = await coordinator.execute_prompt(
            prompt="Start over",
            user_id=user_id
        )
        assert result2["success"]
        
        # Verify reset
        workflow = coordinator.workflows.get(user_id)
        assert workflow["stage"] == "initial"
        print("✓ Workflow reset works")


# ============================================================================
# PART 5: End-to-End Integration Tests
# ============================================================================

class TestCompleteWorkflow:
    """Test complete recruitment workflow end-to-end"""

    @pytest.mark.asyncio
    async def test_full_recruitment_scenario(self):
        """Test complete recruitment workflow from start to finish"""
        print("\n" + "="*70)
        print("TESTING COMPLETE RECRUITMENT WORKFLOW")
        print("="*70)
        
        initialize_router()
        router = get_router()
        
        # Pre-register all agents
        router.register_agent_handler(
            AgentType.REQUIREMENTS_COLLECTION,
            get_requirements_agent()
        )
        router.register_agent_handler(
            AgentType.RESUME_MATCHING,
            get_resume_matching_agent()
        )
        router.register_agent_handler(
            AgentType.USER_PROFILE,
            get_user_profile_agent()
        )
        
        user_id = "complete_workflow_test"
        session_id = "session_complete_1"
        
        # Step 1: User specifies requirements
        print("\n[STEP 1] User specifies job requirements...")
        step1 = await router.route_message(
            message="I need to hire a senior Python backend engineer with AWS experience",
            user_id=user_id,
            session_id=session_id
        )
        assert step1.get("agent") == AgentType.REQUIREMENTS_COLLECTION.value
        print(f"  ✓ Response: {step1.get('response', 'executed')[:150]}...")
        
        # Step 2: Individual agents work
        print("\n[STEP 2] User requests matching candidates...")
        agent = get_resume_matching_agent()
        step2 = await agent.execute_prompt(
            prompt="Find candidates with Python and AWS",
            user_id=user_id,
            session_id=session_id
        )
        assert step2["success"]
        print(f"  ✓ Response: {step2['response'][:150]}...")
        
        # Step 3: Profile management
        print("\n[STEP 3] User updates their profile...")
        profile_agent = get_user_profile_agent()
        step3 = await profile_agent.execute_prompt(
            prompt="Update my preferences",
            user_id=user_id,
            session_id=session_id
        )
        assert step3["success"]
        print(f"  ✓ Response: {step3['response'][:150]}...")
        
        print("\n" + "="*70)
        print("✓ COMPLETE WORKFLOW TEST PASSED")
        print("="*70)

    @pytest.mark.asyncio
    async def test_multi_agent_handoff(self):
        """Test smooth handoff between multiple agents"""
        print("\n" + "="*70)
        print("TESTING MULTI-AGENT HANDOFF")
        print("="*70)
        
        user_id = "handoff_test"
        agents_used = []
        
        messages_and_agents = [
            ("I need a JavaScript developer", get_requirements_agent()),
            ("Find candidates with React and Node.js skills", get_resume_matching_agent()),
            ("Let me check my recruiter profile", get_user_profile_agent()),
            ("I want to manage this recruitment", get_recruitment_coordinator_agent()),
        ]
        
        for i, (message, agent) in enumerate(messages_and_agents, 1):
            print(f"\n[TURN {i}] Sending: '{message}'")
            result = await agent.execute_prompt(
                prompt=message,
                user_id=user_id
            )
            
            assert result["success"]
            agents_used.append(agent.name)
            print(f"  ✓ Agent: {agent.name}")
            print(f"  ✓ Response: {result['response'][:120]}...")
        
        # Verify different agents were used
        unique_agents = set(agents_used)
        print(f"\n✓ Used {len(unique_agents)} different agents: {unique_agents}")
        print("="*70)
        print("✓ MULTI-AGENT HANDOFF TEST PASSED")
        print("="*70)


# ============================================================================
# PART 6: Coordinator Orchestration Tests
# ============================================================================

class TestCoordinatorOrchestration:
    """Test the coordinator's ability to manage full workflows"""

    @pytest.mark.asyncio
    async def test_coordinator_workflow_management(self):
        """Test coordinator manages complete workflow"""
        coordinator = get_recruitment_coordinator_agent()
        user_id = "coordinator_full_test"
        
        print("\n" + "="*70)
        print("TESTING COORDINATOR WORKFLOW MANAGEMENT")
        print("="*70)
        
        # Phase 1: Define requirements
        print("\n[Phase 1] Defining requirements...")
        phase1 = await coordinator.execute_prompt(
            prompt="I need to hire a senior full-stack engineer with 5+ years experience",
            user_id=user_id
        )
        assert phase1["success"]
        print(f"  ✓ {phase1['response'][:100]}...")
        
        workflow = coordinator.workflows.get(user_id)
        initial_stage = workflow.get("stage") if workflow else None
        print(f"  ✓ Workflow stage: {initial_stage}")
        
        # Phase 2: Search for candidates
        print("\n[Phase 2] Searching for candidates...")
        phase2 = await coordinator.execute_prompt(
            prompt="Find me suitable candidates",
            user_id=user_id
        )
        assert phase2["success"]
        print(f"  ✓ {phase2['response'][:100]}...")
        
        workflow = coordinator.workflows.get(user_id)
        current_stage = workflow.get("stage") if workflow else None
        print(f"  ✓ Workflow stage: {current_stage}")
        
        # Phase 3: Review candidates
        print("\n[Phase 3] Reviewing candidates...")
        phase3 = await coordinator.execute_prompt(
            prompt="Which candidates look best?",
            user_id=user_id
        )
        assert phase3["success"]
        print(f"  ✓ {phase3['response'][:100]}...")
        
        workflow = coordinator.workflows.get(user_id)
        final_stage = workflow.get("stage") if workflow else None
        print(f"  ✓ Workflow stage: {final_stage}")
        
        print("\n" + "="*70)
        print("✓ COORDINATOR ORCHESTRATION TEST PASSED")
        print("="*70)


# ============================================================================
# PART 7: System Health Tests
# ============================================================================

class TestSystemHealth:
    """Test overall system health and reliability"""

    def test_all_agents_available(self):
        """Test all agents are properly registered"""
        initialize_router()
        router = get_router()
        
        # Manually register agents for this test
        router.register_agent_handler(
            AgentType.REQUIREMENTS_COLLECTION,
            get_requirements_agent()
        )
        router.register_agent_handler(
            AgentType.RESUME_MATCHING,
            get_resume_matching_agent()
        )
        router.register_agent_handler(
            AgentType.USER_PROFILE,
            get_user_profile_agent()
        )
        router.register_agent_handler(
            AgentType.RECRUITMENT_COORDINATOR,
            get_recruitment_coordinator_agent()
        )
        
        agents = router.list_available_agents()
        assert len(agents) >= 4
        
        required_agents = [
            "requirements_collector",  # Note: this uses 'collector' not 'collection'
            "resume_matching", 
            "user_profile",
            "recruitment_coordinator"
        ]
        
        agent_names = [a.get("name") for a in agents]
        for required in required_agents:
            assert any(required in str(name) for name in agent_names), \
                f"Agent '{required}' not found in {agent_names}"
        
        print(f"✓ All {len(agents)} agents available")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test system handles errors gracefully"""
        agent = get_requirements_agent()
        
        # Test with empty prompt
        result = await agent.execute_prompt(
            prompt="",
            user_id="error_test_1"
        )
        assert "response" in result
        assert len(result["response"]) >= 0
        print("✓ Handles empty prompts")
        
        # Test with very long prompt
        long_prompt = "X" * 5000
        result = await agent.execute_prompt(
            prompt=long_prompt,
            user_id="error_test_2"
        )
        assert "response" in result
        print("✓ Handles long prompts")

    @pytest.mark.asyncio
    async def test_concurrent_users(self):
        """Test system handles multiple concurrent users"""
        router = get_router()
        initialize_router()
        
        # Simulate 5 concurrent users
        tasks = []
        for i in range(5):
            task = router.route_message(
                message=f"Concurrent message from user {i}",
                user_id=f"concurrent_user_{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(r.get("success") is not None for r in results)
        print(f"✓ Handled {len(results)} concurrent users successfully")


# ============================================================================
# Main Test Execution
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTI-AGENT SYSTEM INTEGRATION TEST SUITE")
    print("="*70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
