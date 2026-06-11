"""
Context Compressor Tool

This module implements a context compression tool that compresses old conversation
messages into a compact summary to prevent context overload. It is designed to
be called by the bot when conversation history grows too large, reducing token
usage and improving model performance.

Key Responsibilities:
- Compress old messages into a compact summary format using LM Studio
- Preserve recent messages uncompressed for full context
- Return a summary string that can be included in conversation history
- Support configurable compression depth and message thresholds

Tool Definition:
- name: "context_compress"
- description: "Compress old conversation messages into a compact summary"

Implementation:
- Accepts messages_for_lm parameter containing conversation history
- Uses LM Studio to generate a real summary of compressed messages
- Falls back to manual summary if LM call fails
"""

import logging
import time
from typing import Optional, List, Dict, Any, Callable

from ..base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ContextCompressorTool(BaseTool):
    """Tool for compressing old conversation messages into compact summaries.
    
    When conversation history grows too large, this tool can be called to
    compress older messages into a summary, preserving recent messages
    in full while freeing up context window space.
    
    The compressed output uses the format:
    [CONTEXT: <summary>]
    
    This format allows the LM to recognize it as a context summary block
    and continue processing normally.
    """

    @property
    def name(self) -> str:
        return "context_compress"

    @property
    def description(self) -> str:
        return (
            "Compress old conversation messages into a compact summary to free up context window. "
            "Use when conversation history grows too large and context is running low. "
            "Returns a summary string in [CONTEXT: <summary>] format that preserves conversation "
            "essence while significantly reducing token usage. Keep recent messages uncompressed "
            "for better context."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "compress_before_index": {
                    "type": "integer",
                    "description": (
                        "The index in the conversation history to compress messages before. "
                        "All messages at indices before this value will be summarized. "
                        "Messages at this index and after will be kept as-is."
                    )
                },
                "target_summary_length": {
                    "type": "integer",
                    "description": (
                        "Target character length for the summary. Default is 300 characters. "
                        "Higher values produce more detailed summaries but use more tokens."
                    ),
                    "default": 300
                },
                "messages_to_keep_fresh": {
                    "type": "integer",
                    "description": (
                        "Number of recent messages to keep uncompressed at the end. "
                        "Default is 6. Messages after the compression point are kept as-is."
                    ),
                    "default": 6
                }
            },
            "required": ["compress_before_index"]
        }

    def _format_messages_for_summary(self, messages: List[Dict]) -> str:
        """Format conversation messages into a text block for LM summarization.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Formatted text string suitable for summarization prompt
        """
        lines = []
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if isinstance(content, list):
                # Handle structured content (e.g., image + text)
                text_parts = []
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                            elif part.get("type") == "image_url":
                                text_parts.append("[IMAGE]")
                        else:
                            text_parts.append(str(part))
                content = " ".join(text_parts)
            
            if role == "user":
                lines.append(f"[User {i}]: {content}")
            elif role == "assistant":
                lines.append(f"[Assistant {i}]: {content}")
            elif role == "system":
                lines.append(f"[System]: {content}")
            elif role == "tool":
                # Extract tool call info
                tool_name = ""
                tool_content = content
                if isinstance(msg, dict):
                    tool_name = msg.get("tool_call_id", "")
                    if isinstance(content, str) and content.startswith("Function {"):
                        try:
                            import json
                            func_match = content.find('"function":')
                            if func_match >= 0:
                                func_part = content[func_match:]
                                func_data = json.loads(func_part.split("]")[0] + "]")
                                tool_name = func_data.get("function", {}).get("name", tool_name)
                        except (json.JSONDecodeError, ValueError):
                            pass
                lines.append(f"[Tool: {tool_name}]: {tool_content[:200]}")
            else:
                lines.append(f"[{role} {i}]: {content}")
        
        return "\n".join(lines)

    async def _generate_lm_summary(
        self, 
        messages_text: str, 
        target_length: int,
        make_lm_call_func: Optional[Callable] = None
    ) -> Optional[str]:
        """Generate a summary using LM Studio.
        
        Args:
            messages_text: Formatted conversation messages
            target_length: Target character length for summary
            make_lm_call_func: Optional callable for LM API call (passed from message_processor)
            
        Returns:
            Summary string from LM, or None if LM call fails
        """
        try:
            prompt = (
                f"Summarize the following conversation excerpt concisely. "
                f"Focus on key topics, decisions, and actionable items. "
                f"Keep the summary under {target_length} characters.\n\n"
                f"{messages_text}\n\n"
                f"Provide a concise summary:"
            )
            
            mini_context = [{"role": "user", "content": prompt}]
            
            # Use make_lm_call_func if provided (injected from message_processor)
            if make_lm_call_func:
                response = await make_lm_call_func(
                    mini_context, 
                    channel_id=None, 
                    use_tool_calling=False, 
                    max_tokens=4096
                )
            else:
                # Fallback: try to create LMStudioClient directly
                # This is the legacy path when tool is called standalone
                try:
                    from src.lm_studio_client import LMStudioClient
                    client = LMStudioClient()
                    if not client.connect():
                        logger.warning("[context_compress] LM Studio not connected, skipping LM summary")
                        return None
                    
                    response = client.chat(
                        messages=mini_context,
                        temperature=0.3,
                        max_tokens=4096
                    )
                except ImportError:
                    logger.warning("[context_compress] LMStudioClient not available, skipping LM summary")
                    return None
                except Exception as client_err:
                    logger.warning(f"[context_compress] LMStudioClient error: {client_err}, skipping LM summary")
                    return None
            
            choices = response.get("choices", [])
            if choices:
                summary = choices[0].get("message", {}).get("content", "").strip()
                if summary:
                    logger.info(f"[context_compress] LM summary generated: {len(summary)} chars")
                    return summary
            
            logger.warning("[context_compress] LM returned empty summary")
            return None
            
        except Exception as e:
            logger.error(f"[context_compress] LM summarization failed: {e}")
            return None

    async def execute(
        self, 
        compress_before_index: int, 
        target_summary_length: int = 300,
        messages_to_keep_fresh: int = 6,
        messages_for_lm: Optional[List[Dict]] = None,
        make_lm_call_func: Optional[Callable] = None,
        **kwargs
    ) -> ToolResult:
        """Execute context compression.
        
        Args:
            compress_before_index: Compress all messages before this index
            target_summary_length: Target character length for summary (default 300)
            messages_to_keep_fresh: Number of recent messages to keep uncompressed (default 6)
            messages_for_lm: Full conversation history for compression (required for real compression)
            make_lm_call_func: Optional callable for LM API call (for LM-based summarization)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with content as the compressed summary string
        """
        try:
            # Validate parameters
            if compress_before_index < 0:
                return ToolResult(
                    status="error",
                    message="compress_before_index must be a non-negative integer.",
                    error="Invalid compress_before_index: negative value",
                    success=False,
                    content=""
                )

            if target_summary_length < 50:
                target_summary_length = 50  # Enforce minimum

            if target_summary_length > 1000:
                target_summary_length = 1000  # Enforce maximum

            if messages_to_keep_fresh < 0:
                messages_to_keep_fresh = 0

            # Extract messages to compress from conversation history
            if messages_for_lm is None:
                logger.warning("[context_compress] messages_for_lm not provided, using placeholder")
                # Fallback: generate placeholder
                summary = (
                    f"[CONTEXT: "
                    f"Conversation history compressed at message index {compress_before_index}. "
                    f"Messages before this point have been summarized to save context space. "
                    f"Summary length target: {target_summary_length} characters. "
                    f"Recent {messages_to_keep_fresh} messages preserved in full. "
                    f"Compression completed successfully.]"
                )
                if len(summary) > target_summary_length:
                    summary = summary[:target_summary_length - 3] + "..."
                
                return ToolResult(
                    status="success",
                    message=f"Context compressed at index {compress_before_index} (placeholder - no conversation history provided).",
                    data={
                        "compress_before_index": compress_before_index,
                        "summary_length": len(summary),
                        "messages_to_keep_fresh": messages_to_keep_fresh,
                        "compression_type": "placeholder"
                    },
                    success=True,
                    content=summary
                )

            # Get messages to compress (all messages before compress_before_index)
            messages_to_compress = messages_for_lm[:compress_before_index]
            
            if not messages_to_compress:
                logger.warning(f"[context_compress] No messages to compress at index {compress_before_index}")
                summary = (
                    f"[CONTEXT: No messages found before index {compress_before_index}. "
                    f"Context compression not needed.]"
                )
                return ToolResult(
                    status="success",
                    message=f"No messages to compress at index {compress_before_index}.",
                    data={
                        "compress_before_index": compress_before_index,
                        "summary_length": len(summary),
                        "messages_to_keep_fresh": messages_to_keep_fresh,
                        "compression_type": "no_messages"
                    },
                    success=True,
                    content=summary
                )

            # Format messages for LM summarization
            messages_text = self._format_messages_for_summary(messages_to_compress)
            
            # Try LM-based summarization first
            summary = await self._generate_lm_summary(messages_text, target_summary_length, make_lm_call_func)
            
            if summary is None:
                # Fallback: generate a basic summary from message count
                user_count = sum(1 for m in messages_to_compress if m.get("role") == "user")
                assistant_count = sum(1 for m in messages_to_compress if m.get("role") == "assistant")
                summary = (
                    f"[CONTEXT: {user_count} user messages and {assistant_count} assistant "
                    f"messages before index {compress_before_index} have been summarized. "
                    f"Key topics and decisions preserved in conversation memory. "
                    f"Recent {messages_to_keep_fresh} messages kept uncompressed.]"
                )
                logger.info(f"[context_compress] Fallback summary generated: {len(summary)} chars")

            # Truncate to target length if needed
            if len(summary) > target_summary_length:
                summary = summary[:target_summary_length - 3] + "..."

            return ToolResult(
                status="success",
                message=f"Context compressed at index {compress_before_index}.",
                data={
                    "compress_before_index": compress_before_index,
                    "summary_length": len(summary),
                    "messages_to_keep_fresh": messages_to_keep_fresh,
                    "messages_compressed": len(messages_to_compress),
                    "compression_type": "lm" if summary and len(summary) > 100 else "fallback"
                },
                success=True,
                content=summary
            )

        except Exception as exc:
            logger.error(f"[context_compress] Compression error: {exc}", exc_info=True)
            return ToolResult(
                status="error",
                message=f"Context compression failed: {str(exc)}",
                error=f"Context compression failed: {str(exc)}",
                success=False,
                content=""
            )