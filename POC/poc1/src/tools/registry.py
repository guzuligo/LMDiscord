"""
Tool Registry Module

This module provides the ToolRegistry class for managing tool registration,
unregistration, and retrieval. It serves as the central hub for all available tools.

Key Responsibilities:
- Register and unregister tools
- Retrieve tool definitions for OpenAI API
- Filter tools by enabled status
- Provide tool instances by name
"""

from typing import Dict, List, Optional

from .base import BaseTool


class ToolRegistry:
    """Central registry for managing available tools.
    
    The registry maintains a collection of tools and provides methods to:
    - Register new tools
    - Get tool definitions in OpenAI-compatible format
    - Filter tools by enabled status (from config)
    """

    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry.
        
        Args:
            tool: The BaseTool instance to register
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name.
        
        Args:
            name: The name of the tool to unregister
        """
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            The BaseTool instance, or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """List all registered tools.
        
        Returns:
            List of all registered BaseTool instances
        """
        return list(self._tools.values())

    def get_all_definitions(self) -> List[dict]:
        """Get all tool definitions in OpenAI-compatible format.
        
        Returns:
            List of tool definition dictionaries ready for LM Studio API
        """
        return [tool.to_dict() for tool in self._tools.values()]

    def get_enabled_definitions(self, enabled_tools: List[str]) -> List[dict]:
        """Get tool definitions for only the enabled tools.
        
        Args:
            enabled_tools: List of tool names that are enabled in config
            
        Returns:
            List of tool definition dictionaries for enabled tools only
        """
        return [
            tool.to_dict() 
            for tool in self._tools.values() 
            if tool.name in enabled_tools
        ]

    def is_registered(self, name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            name: The name of the tool
            
        Returns:
            True if the tool is registered, False otherwise
        """
        return name in self._tools