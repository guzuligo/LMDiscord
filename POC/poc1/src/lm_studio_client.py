"""
LM Studio Client Module

Handles communication with LM Studio API using the OpenAI-compatible endpoint.
"""

import requests
import json
import time
import logging
import asyncio
from typing import Optional, Generator, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class LMStudioError(Exception):
    """Custom exception for LM Studio errors with response body details."""
    
    def __init__(self, status_code: Optional[int], message: str, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LMStudioClient:
    """Client for LM Studio API communication."""
    
    def __init__(self, hostname: str = "localhost", port: int = 1234):
        """Initialize LM Studio client.
        
        Args:
            hostname: LM Studio server hostname
            port: LM Studio server port
        """
        self.hostname = hostname
        self.port = port
        self._selected_model: str = ""  # Empty = let LM Studio pick
        self.base_url = f"http://{hostname}:{port}/v1"
        self.chat_url = f"{self.base_url}/chat/completions"
        self._is_connected = False
        self._model = "local-model"
        self._models: List[str] = []
        self._config: Optional[Any] = None

    @property
    def selected_model(self) -> str:
        """Get the selected model name (may be empty)."""
        return self._selected_model

    @selected_model.setter
    def selected_model(self, value: str) -> None:
        """Set the selected model name.
        
        If already connected, also updates _model immediately so the
        new model takes effect without requiring a reconnect.
        """
        self._selected_model = value
        if self._is_connected and value:
            self._model = value

    def switch_to(self, hostname: str, port: int = 1234) -> bool:
        """Switch to a different LM Studio instance.
        
        Args:
            hostname: New LM Studio server hostname
            port: New LM Studio server port
            
        Returns:
            True if switch successful, False otherwise
        """
        try:
            old_hostname = self.hostname
            old_port = self.port
            self.hostname = hostname
            self.port = port
            self.base_url = f"http://{hostname}:{port}/v1"
            self.chat_url = f"{self.base_url}/chat/completions"
            
            # Test connection
            if self.connect():
                return True
            # Revert on failure
            self.hostname = old_hostname
            self.port = old_port
            self.base_url = f"http://{old_hostname}:{old_port}/v1"
            self.chat_url = f"{self.base_url}/chat/completions"
            return False
        except Exception:
            return False
    
    @property
    def config(self) -> Optional[Any]:
        """Configuration object (optional, may be None)."""
        return self._config
    
    @config.setter
    def config(self, config: Any) -> None:
        """Set configuration object."""
        self._config = config
    
    def connect(self) -> bool:
        """Test connection to LM Studio and fetch available models.
        
        If a selected_model is configured (non-empty), it will be used
        as the active model regardless of what LM Studio has loaded.
        When no selected_model is set, falls back to the first available
        model from LM Studio.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self._models = [m.get("id", "") for m in data.get("data", [])]
                
                # Priority: (1) explicit selected_model, (2) first available
                if self._selected_model:
                    # Use the configured selected model even if not in discovered list
                    # (LM Studio may have reloaded a different model)
                    self._model = self._selected_model
                elif self._models:
                    self._model = self._models[0]
                self._is_connected = True
                return True
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            self._is_connected = False
            self._models = []
            return False
        except Exception:
            self._is_connected = False
            self._models = []
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to LM Studio."""
        return self._is_connected
    
    @property
    def models(self) -> List[str]:
        """Get available models."""
        return self._models
    
    @property
    def model(self) -> str:
        """Get current model."""
        return self._model
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2500,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request to LM Studio.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to current model)
            
        Returns:
            Response dict from LM Studio API
            
        Raises:
            ConnectionError: If not connected to LM Studio
            LMStudioError: If request fails
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Not connected to LM Studio")
        
        payload = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            self.chat_url,
            json=payload,
            timeout=120
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Extract error details from response body for better error reporting
            error_body = ""
            status_code = response.status_code
            try:
                error_data = response.json()
                error_body = json.dumps(error_data)
                # Extract the error message for logging
                error_msg = error_data.get("error", {}).get("message", str(e))
                logger.error(f"LM Studio HTTP Error {status_code}: {error_msg}. Response: {error_body[:2000]}")
            except (json.JSONDecodeError, KeyError):
                logger.error(f"LM Studio HTTP Error {status_code}: {e}. Response: {response.text[:2000]}")
                error_body = response.text
            
            # Retry once for transient 400 model loading errors
            if status_code == 400 and "failed to load" in error_body.lower():
                logger.info("Transient 400 model loading error detected, retrying once...")
                time.sleep(2)  # Wait for model to finish loading
                try:
                    response = requests.post(
                        self.chat_url,
                        json=payload,
                        timeout=120
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError as retry_e:
                    logger.warning(f"Retry failed, original error will be raised")
            
            # Raise custom exception with response body for better error handling upstream
            raise LMStudioError(
                status_code=status_code,
                message=str(e),
                response_body=error_body if error_body else response.text
            )
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2500,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request with tool calling support.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions (OpenAI-compatible format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to current model)
            
        Returns:
            Response dict from LM Studio API including tool_calls if present
            
        Raises:
            ConnectionError: If not connected to LM Studio
            LMStudioError: If request fails
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Not connected to LM Studio")
        
        payload = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": "auto"  # Let model decide whether to use tools
        }
        
        response = requests.post(
            self.chat_url,
            json=payload,
            timeout=120
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Extract error details from response body for better error reporting
            error_body = ""
            status_code = response.status_code
            try:
                error_data = response.json()
                error_body = json.dumps(error_data)
                error_msg = error_data.get("error", {}).get("message", str(e))
                logger.error(f"LM Studio HTTP Error {status_code}: {error_msg}. Response: {error_body[:2000]}")
            except (json.JSONDecodeError, KeyError):
                logger.error(f"LM Studio HTTP Error {status_code}: {e}. Response: {response.text[:2000]}")
                error_body = response.text
            
            # Retry once for transient 400 model loading errors
            if status_code == 400 and "failed to load" in error_body.lower():
                logger.info("Transient 400 model loading error detected, retrying once...")
                time.sleep(2)  # Wait for model to finish loading
                try:
                    response = requests.post(
                        self.chat_url,
                        json=payload,
                        timeout=120
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError as retry_e:
                    logger.warning(f"Retry failed, original error will be raised")
            
            raise LMStudioError(
                status_code=status_code,
                message=str(e),
                response_body=error_body if error_body else response.text
            )
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2500,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Send a streaming chat completion request to LM Studio.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to current model)
            
        Yields:
            Partial response text chunks
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Not connected to LM Studio")
        
        payload = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        response = requests.post(
            self.chat_url,
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except GeneratorExit:
            pass

    def chat_with_tools_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2500,
        model: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Send a streaming chat completion request with tool calling support.
        
        Yields chunks as they arrive, plus final usage stats.
        Each yield is a dict with keys:
          - "chunk": text content string (may be empty for tool calls)
          - "tool_calls": list of tool call dicts (if any)
          - "usage": usage dict (only in the final event)
          - "done": bool, True on the final event
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions (OpenAI-compatible format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to current model)
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Not connected to LM Studio")
        
        payload = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": "auto",
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        
        response = requests.post(
            self.chat_url,
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            usage = data.get("usage")
                            
                            chunk_info = {
                                "chunk": "",
                                "tool_calls": [],
                                "usage": None,
                                "done": False
                            }
                            
                            if choices:
                                delta = choices[0].get("delta", {})
                                
                                # Get text content
                                content = delta.get("content")
                                if content:
                                    chunk_info["chunk"] = content
                                
                                # Get tool calls
                                tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
                                if tool_calls:
                                    chunk_info["tool_calls"] = tool_calls
                            
                            # Usage is in the last event
                            if usage:
                                chunk_info["usage"] = usage
                                chunk_info["done"] = True
                            else:
                                chunk_info["done"] = False
                            
                            yield chunk_info
                        except json.JSONDecodeError:
                            continue
        except GeneratorExit:
            pass

    def chat_stream_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2500,
        model: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Send a streaming chat completion request and yield chunks with usage.
        
        This is the non-tool-calling version of chat_with_tools_stream.
        Handles reasoning models that output content in reasoning_content instead of content.
        
        Yields dicts with keys:
          - "chunk": text content string
          - "usage": usage dict (only in final event, may be None)
          - "done": bool
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to current model)
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Not connected to LM Studio")
        
        payload = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        
        response = requests.post(
            self.chat_url,
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            usage = data.get("usage")
                            
                            chunk_info = {
                                "chunk": "",
                                "usage": None,
                                "done": False
                            }
                            
                            if choices:
                                delta = choices[0].get("delta", {})
                                
                                # Try content first, then reasoning_content (for reasoning models)
                                content = delta.get("content")
                                if not content:
                                    content = delta.get("reasoning_content")
                                if not content:
                                    content = delta.get("reasoning")
                                
                                if content:
                                    chunk_info["chunk"] = content
                            
                            if usage:
                                chunk_info["usage"] = usage
                                chunk_info["done"] = True
                            
                            yield chunk_info
                        except json.JSONDecodeError:
                            continue
        except GeneratorExit:
            pass
