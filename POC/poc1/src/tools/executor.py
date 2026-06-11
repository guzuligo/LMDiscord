"""
Tool Execution Handler Module

This module provides the ToolExecutor class that handles executing tools
by name. It manages the tool registry and provides a safe interface for
tool execution with proper error handling.

Key Responsibilities:
- Execute tools by name
- Handle execution errors gracefully
- Return standardized result format
- Support both text and image tool results
"""

import json
from typing import Any, Dict

from .base import BaseTool, ToolResult


class ToolExecutor:
    """Executes tools by name with proper error handling.
    
    The executor takes tool results and formats them for the LM Studio API:
    - Regular tools return: {"type": "text", "content": <json_string>}
    - Image tools return: {"type": "image", "base64_data": <str>, "mime_type": <str>}
    """

    def __init__(self, tools: Dict[str, BaseTool]):
        """Initialize the executor with a registry of tools.
        
        Args:
            tools: Dictionary mapping tool names to BaseTool instances
        """
        self._tools = tools

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool by name with the given arguments.
        
        The executor now handles the new structured ToolResult format:
        - status="success" → pass content to LM as normal
        - status="no_results" → pass a "no results" message for LM to handle gracefully
        - status="error" → pass an error message for LM to handle gracefully
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            dict: Result in OpenAI-compatible format:
                  {"type": "text", "content": <json_string>} for regular tools
                  {"type": "image", "base64_data": <str>, "mime_type": <str>} for image tools
        """
        tool = self._tools.get(tool_name)
        
        if tool is None:
            return {
                "type": "text",
                "content": json.dumps({"error": f"Unknown tool: {tool_name}"})
            }
        
        # Validate required parameters
        if not tool.validate_params(arguments):
            required = tool.parameters.get("required", [])
            return {
                "type": "text",
                "content": json.dumps({
                    "error": f"Missing required parameters: {', '.join(required)}"
                })
            }
        
        try:
            result: ToolResult = tool.execute(**arguments)
            
            # Handle structured status values
            if result.status == "error":
                return {
                    "type": "text",
                    "content": json.dumps({
                        "status": "error",
                        "message": result.message or result.error,
                        "tool": tool_name
                    })
                }
            
            if result.status == "no_results":
                return {
                    "type": "text",
                    "content": json.dumps({
                        "status": "no_results",
                        "message": result.message or "No results found.",
                        "tool": tool_name
                    })
                }
            
            # status="success" — pass content to LM as normal
            return {
                "type": "text",
                "content": result.content if result.content else result.message
            }
            
        except Exception as exc:
            return {
                "type": "text",
                "content": json.dumps({
                    "status": "error",
                    "message": str(exc),
                    "tool": tool_name
                })
            }

    def execute_with_image_support(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool, with special handling for image-based results.
        
        Some tools (like image_describe) return processed image data that needs
        special handling. This method checks for that and returns the appropriate format.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            dict: Result in OpenAI-compatible format with image support
        """
        tool = self._tools.get(tool_name)
        
        if tool is None:
            return {
                "type": "text",
                "content": json.dumps({"error": f"Unknown tool: {tool_name}"})
            }
        
        try:
            result: ToolResult = tool.execute(**arguments)
            
            # Handle structured status values
            if result.status == "error":
                return {
                    "type": "text",
                    "content": json.dumps({
                        "status": "error",
                        "message": result.message or result.error,
                        "tool": tool_name
                    })
                }
            
            if result.status == "no_results":
                return {
                    "type": "text",
                    "content": json.dumps({
                        "status": "no_results",
                        "message": result.message or "No results found.",
                        "tool": tool_name
                    })
                }
            
            # Check if this is an image tool result
            # Image tools return content as JSON with base64_data and mime_type
            try:
                content_data = json.loads(result.content if result.content else result.message)
                if "base64_data" in content_data and "mime_type" in content_data:
                    return {
                        "type": "image",
                        "base64_data": content_data["base64_data"],
                        "mime_type": content_data["mime_type"]
                    }
            except (json.JSONDecodeError, TypeError):
                pass  # Not JSON content, treat as regular text
            
            return {
                "type": "text",
                "content": result.content if result.content else result.message
            }
            
        except Exception as exc:
            return {
                "type": "text",
                "content": json.dumps({
                    "status": "error",
                    "message": str(exc),
                    "tool": tool_name
                })
            }
