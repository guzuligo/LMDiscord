"""
Base Tool Class Module

This module defines the abstract base class for all tools in the application.
All tools must inherit from this base class and implement the required methods.

Key Responsibilities:
- Define the tool interface (name, description, parameters, execute)
- Provide tool definition format for OpenAI-compatible API
- Handle tool parameter validation
- Define execution result format
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Standardized result format for tool execution."""
    success: bool
    content: str
    error: str = ""


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    All tools must inherit from this class and implement:
    - name: unique identifier for the tool
    - description: human-readable description for LM Studio
    - parameters: JSON schema describing expected inputs
    - execute(): the actual tool logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool (used for registration and calling)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Description shown to LM Studio to help it decide when to use this tool."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON schema describing the tool's parameters (OpenAI-compatible format)."""
        ...

    def to_dict(self) -> dict:
        """Convert tool definition to OpenAI-compatible function calling format.
        
        Returns:
            dict: Tool definition in the format expected by the OpenAI API
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given arguments.
        
        Args:
            **kwargs: Tool parameters passed as keyword arguments
            
        Returns:
            ToolResult: Standardized result with success status, content, and optional error
        """
        ...

    def validate_params(self, params: dict) -> bool:
        """Validate that all required parameters are present.
        
        Args:
            params: Dictionary of parameters to validate
            
        Returns:
            bool: True if all required parameters are present
        """
        required = self.parameters.get("required", [])
        return all(k in params for k in required)