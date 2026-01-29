"""LLM Service for Chat with Google Gemini or OpenAI"""
import logging
import json
from utils.config import LLM_PROVIDER, GOOGLE_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM interactions"""
    
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.setup_provider()
    
    def setup_provider(self):
        """Initialize the chosen LLM provider"""
        if self.provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=GOOGLE_API_KEY)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                logger.info("✓ Google Gemini LLM initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Gemini: {e}")
                raise
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.model = "gpt-3.5-turbo"
                logger.info("✓ OpenAI LLM initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                raise
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt using the configured LLM provider.
        Used for resume parsing and other text generation tasks.
        """
        try:
            logger.info(f"[LLM_GENERATE_TEXT_START] Generating text using {self.provider} provider")
            logger.debug(f"[LLM_PROMPT] Prompt length: {len(prompt)} characters")
            logger.debug(f"[LLM_PROMPT_CONTENT] Prompt: {prompt[:200]}...")
            
            if self.provider == "google":
                response = self.model.generate_content(prompt)
                generated_text = response.text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
                generated_text = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
            
            logger.info(f"[LLM_GENERATE_TEXT_SUCCESS] Generated text length: {len(generated_text)} characters")
            logger.debug(f"[LLM_GENERATED_CONTENT] Generated text: {generated_text}")
            return generated_text
            
        except Exception as e:
            logger.error(f"[LLM_GENERATE_TEXT_ERROR] Error generating text: {e}", exc_info=True)
            raise
    
    def process_user_message(self, user_message: str, conversation_history: list = None) -> str:
        """Process user message and return AI response"""
        
        if conversation_history is None:
            conversation_history = []
        
        system_prompt = """
        You are Campus AI, an intelligent executive recruiter assistant for hiring CTOs, CISOs, VP Engineers, and Chief Product Officers.
        
        Your role is to help companies understand their needs and find the perfect executive match.
        
        CONVERSATION FLOW:
        1. Phase 1: Ask about the ROLE (CTO, CISO, VP Engineering, CPO)
        2. Phase 2: Ask about INDUSTRY (FinTech, Healthcare, SaaS, E-commerce)
        3. Phase 3: Ask about ENGAGEMENT TYPE (Fractional, Interim, Advisory, Full-time)
        4. Phase 4: Ask about TEAM SIZE (how many engineers they'll manage)
        5. Phase 5: Ask about LEADERSHIP STYLE (Hands-on, Strategic, Balanced)
        
        IMPORTANT RULES:
        - Don't skip phases - ask all questions before suggesting matches
        - Be conversational, friendly, and professional
        - Extract one piece of information per question
        - Remember previous answers
        - When all info is gathered (after phase 5), say: "Perfect! I have all the details I need. Let me find the best matches for you."
        - Always be specific about what you're asking next
        
        Start by asking about the role they're trying to fill.
        """
        
        try:
            if self.provider == "google":
                response = self.model.generate_content(f"{system_prompt}\n\nUser: {user_message}")
                return response.text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "I apologize, there was an error processing your request. Please try again."
    
    def extract_requirements(self, conversation_text: str) -> dict:
        """Extract structured requirements from conversation"""
        
        prompt = f"""
        Analyze this conversation and extract requirements in JSON format.
        Extract the following fields if mentioned (return "unknown" if not mentioned):
        - role: One of [CTO, CISO, VP Engineering, CPO, unknown]
        - industry: One of [FinTech, Healthcare, SaaS, E-commerce, unknown]
        - engagement_type: One of [Fractional, Interim, Advisory, Full-time, unknown]
        - team_size: Number or "unknown"
        - leadership_style: One of [Hands-on, Strategic, Balanced, unknown]
        - tech_stacks: List of mentioned technologies
        - compliance_needs: List of mentioned compliance requirements
        - all_phases_complete: true/false (are all 5 phases answered?)
        
        Return ONLY valid JSON, no other text.
        
        Conversation:
        {conversation_text}
        """
        
        try:
            if self.provider == "google":
                response = self.model.generate_content(prompt)
                text = response.text.strip()
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=500
                )
                text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse LLM response as JSON: {text}")
            return {
                "role": "unknown",
                "industry": "unknown",
                "engagement_type": "unknown",
                "team_size": "unknown",
                "leadership_style": "unknown",
                "tech_stacks": [],
                "compliance_needs": [],
                "all_phases_complete": False
            }
        except Exception as e:
            logger.error(f"Error extracting requirements: {e}")
            return {
                "role": "unknown",
                "industry": "unknown",
                "engagement_type": "unknown",
                "team_size": "unknown",
                "leadership_style": "unknown",
                "tech_stacks": [],
                "compliance_needs": [],
                "all_phases_complete": False
            }


# Singleton instance
llm_service = LLMService()
