"""
LM Studio Caller Module

Handles LM Studio API calls with global lock serialization.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LMCaller:
    """Handles LM Studio API calls with global lock serialization."""

    def __init__(
        self,
        lm_studio_client: Any,
        tools: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        executor: Optional[ThreadPoolExecutor] = None,
        lm_studio_lock: Optional[Any] = None,
        use_tool_calling: bool = True
    ):
        """Initialize LM caller.

        Args:
            lm_studio_client: LMStudioClient instance
            tools: List of tool definitions
            temperature: Temperature for responses
            max_tokens: Max tokens for responses
            executor: Thread pool executor
            lm_studio_lock: Global asyncio.Lock
            use_tool_calling: Whether to use tool calling
        """
        self.lm_studio_client = lm_studio_client
        self._tools = tools
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._executor = executor or ThreadPoolExecutor(max_workers=2)
        self._lm_studio_lock = lm_studio_lock
        self.use_tool_calling = use_tool_calling

    def update_params(self, tools: Optional[List] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """Update caller parameters."""
        if tools is not None:
            self._tools = tools
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens

    async def call(
        self,
        messages_for_lm: List[Dict],
        channel_id: int,
        use_tool_calling: Optional[bool] = None
    ) -> Dict:
        """Make a call to LM Studio API with global lock.

        Args:
            messages_for_lm: Messages to send to LM Studio
            channel_id: Channel ID for logging
            use_tool_calling: Override default tool calling setting

        Returns:
            LM Studio API response dict
        """
        use_tc = use_tool_calling if use_tool_calling is not None else self.use_tool_calling
        return await self._make_lm_call(messages_for_lm, channel_id, use_tc)

    async def _make_lm_call(
        self,
        messages_for_lm: List[Dict],
        channel_id: int,
        use_tool_calling: bool
    ) -> Dict:
        """Internal LM Studio call with lock."""
        if self._lm_studio_lock is not None:
            channel_info = f" (channel {channel_id})" if channel_id else ""
            logger.info(f"Waiting for LM Studio lock{channel_info}")
            async with self._lm_studio_lock:
                logger.info(f"Acquired LM Studio lock{channel_info}, calling API")
                loop = asyncio.get_event_loop()
                if use_tool_calling:
                    result = await loop.run_in_executor(
                        self._executor,
                        self.lm_studio_client.chat_with_tools,
                        messages_for_lm, self._tools,
                        self.temperature, self.max_tokens
                    )
                else:
                    result = await loop.run_in_executor(
                        self._executor,
                        lambda: self.lm_studio_client.chat(
                            messages=messages_for_lm,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    )
                logger.info(f"Released LM Studio lock{channel_info}")
                return result
        else:
            logger.warning("No LM Studio lock available, calling API directly")
            loop = asyncio.get_event_loop()
            if use_tool_calling:
                return await loop.run_in_executor(
                    self._executor,
                    self.lm_studio_client.chat_with_tools,
                    messages_for_lm, self._tools,
                    self.temperature, self.max_tokens
                )
            else:
                return await loop.run_in_executor(
                    self._executor,
                    lambda: self.lm_studio_client.chat(
                        messages=messages_for_lm,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                )