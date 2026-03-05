"""
Tool Registry - Central registration point for all ADK tools

Tools are registered here during app startup and accessed throughout
the application via the tool registry.
"""
import logging
from typing import Callable, Dict, Any, Optional, List
import json
import os

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for ADK tools with validation"""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._loaded_guardrails: Dict[str, Any] = {}
        logger.info("[Tool Registry] Initialized")
    
    def load_guardrails(self, guardrails_path: str) -> None:
        """Load guardrails configuration from JSON file"""
        try:
            if not os.path.isfile(guardrails_path):
                logger.warning(f"[Tool Registry] Guardrails file not found: {guardrails_path}")
                self._loaded_guardrails = {}
                return
            
            with open(guardrails_path, 'r') as f:
                self._loaded_guardrails = json.load(f)
            
            logger.info(f"[Tool Registry] Loaded guardrails from {guardrails_path}")
        except Exception as e:
            logger.error(f"[Tool Registry] Failed to load guardrails: {e}")
            self._loaded_guardrails = {}
    
    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a tool
        
        Args:
            name: Tool name (unique identifier)
            description: Tool description
            handler: Async function that executes the tool
            input_schema: JSON schema for tool inputs
            output_schema: JSON schema for tool outputs
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "input_schema": input_schema or {},
            "output_schema": output_schema or {},
            "guardrails": self._loaded_guardrails.get(name, {}).get("guardrails", [])
        }
        logger.info(f"[Tool Registry] Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name"""
        return self._tools.get(name)
    
    def get_tool_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler function"""
        tool = self._tools.get(name)
        return tool["handler"] if tool else None
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names"""
        return list(self._tools.keys())
    
    def list_tools_with_descriptions(self) -> Dict[str, str]:
        """Get tools with descriptions"""
        return {name: tool["description"] for name, tool in self._tools.items()}
    
    def get_tool_guardrails(self, name: str) -> List[Dict[str, Any]]:
        """Get guardrails for a specific tool"""
        tool = self._tools.get(name)
        return tool["guardrails"] if tool else []
    
    def validate_tool_exists(self, name: str) -> bool:
        """Check if tool is registered"""
        return name in self._tools
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools (for debugging)"""
        return self._tools.copy()


# Global singleton instance
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    return _registry


def register_tool(
    name: str,
    description: str,
    handler: Callable,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None
) -> None:
    """Register a tool in the global registry"""
    _registry.register(name, description, handler, input_schema, output_schema)


def initialize_tool_registry(guardrails_path: str) -> ToolRegistry:
    """
    Initialize the tool registry with guardrails
    
    Call this during app startup
    """
    logger.info("[Tool Registry] Initializing...")
    _registry.load_guardrails(guardrails_path)
    return _registry
