"""
Chat API Module - Flask Endpoints for Chat and LM Studio Communication

This module handles all chat-related Flask API endpoints including LM Studio
connection, chat messages, model management, and streaming token metrics.
"""

import json
import time
import threading
from flask import jsonify, request, session, Response, stream_with_context

from src.logger import logger
from src.config import Config


# Global token usage tracking (thread-safe)
_last_token_usage = {}
_token_usage_lock = threading.Lock()


def set_last_token_usage(usage_data):
    """Set the last received token usage data.
    
    Args:
        usage_data: Dict with token usage information
    """
    with _token_usage_lock:
        _last_token_usage.update(usage_data)


def get_last_token_usage():
    """Get the last received token usage data.
    
    Returns:
        Dict with token usage information
    """
    with _token_usage_lock:
        return dict(_last_token_usage)


def register_chat_blueprints(bp, client, config):
    """Register chat-related API endpoints with a Blueprint.
    
    Args:
        bp: Flask Blueprint instance
        client: LMStudioClient instance
        config: Config instance
    """
    
    @bp.route("/api/connect", methods=["POST"])
    def connect():
        """Connect to LM Studio.
        
        Request body:
            hostname (str): LM Studio hostname
            port (int): LM Studio port
        """
        data = request.get_json()
        hostname = data.get("hostname", "localhost")
        port = data.get("port", 1234)
        
        logger.info(f"Connecting to LM Studio at {hostname}:{port}", module="chat_api")
        
        client.hostname = hostname
        client.port = port
        client.base_url = f"http://{hostname}:{port}/v1"
        client.chat_url = f"{client.base_url}/chat/completions"
        
        success = client.connect()
        
        if success:
            config.lm_studio_hostname = hostname
            config.lm_studio_port = port
            config.save()
            
            logger.info(f"Successfully connected to LM Studio (model: {client.model})", module="chat_api")
            
            return jsonify({
                "success": True,
                "message": f"Connected to LM Studio",
                "model": client.model,
                "models": client.models
            })
        else:
            logger.error(f"Failed to connect to LM Studio at {hostname}:{port}", module="chat_api")
            
            return jsonify({
                "success": False,
                "message": f"Failed to connect to {hostname}:{port}",
                "model": None,
                "models": []
            }), 500

    @bp.route("/api/models", methods=["GET"])
    def get_models():
        """Get available models from LM Studio."""
        if client.is_connected:
            return jsonify({
                "success": True,
                "models": client.models,
                "current_model": client.model
            })
        else:
            return jsonify({
                "success": False,
                "models": [],
                "current_model": None,
                "message": "Not connected to LM Studio"
            }), 400

    @bp.route("/api/chat", methods=["POST"])
    def chat():
        """Send a message to LM Studio and get a response.
        
        Request body:
            message (str): User message
            model (str, optional): Model to use
        """
        data = request.get_json()
        message = data.get("message", "").strip()
        model = data.get("model")
        
        if not message:
            logger.warning("Empty message received", module="chat_api")
            return jsonify({
                "success": False,
                "error": "Empty message"
            }), 400
        
        if not client.is_connected:
            logger.warning("Chat attempted without LM Studio connection", module="chat_api")
            if not client.connect():
                return jsonify({
                    "success": False,
                    "error": "Not connected to LM Studio"
                }), 400
        
        logger.info(f"User message: {message[:100]}...", module="chat_api")
        
        if "messages" not in session:
            session["messages"] = []
        
        session["messages"].append({"role": "user", "content": message})
        
        try:
            response = client.chat(
                messages=session["messages"],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                model=model
            )
            
            choices = response.get("choices", [])
            if choices:
                assistant_message = choices[0].get("message", {}).get("content", "")
            else:
                assistant_message = "(No response)"
            
            session["messages"].append({"role": "assistant", "content": assistant_message})
            
            logger.info(f"LM Studio response: {assistant_message[:100]}...", module="chat_api")
            
            return jsonify({
                "success": True,
                "response": assistant_message,
                "model": response.get("model", client.model)
            })
            
        except ConnectionError as e:
            logger.error(f"Connection error during chat: {e}", module="chat_api", exc=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
        except Exception as e:
            logger.error(f"Error during chat: {e}", module="chat_api", exc=True)
            return jsonify({
                "success": False,
                "error": f"Error: {str(e)}"
            }), 500

    @bp.route("/api/clear", methods=["POST"])
    def clear_chat():
        """Clear the conversation history."""
        logger.info("Chat history cleared", module="chat_api")
        session["messages"] = []
        return jsonify({"success": True, "message": "Chat cleared"})

    @bp.route("/api/chat/stream", methods=["POST"])
    def chat_stream():
        """Send a message to LM Studio and get a streaming response with real-time token metrics.
        
        This returns an SSE (Server-Sent Events) stream.
        Each event is a JSON line with:
          - event: "chunk" | "usage" | "done"
          - data: { "content": "...", "tokens_used": N, "tokens_per_second": N.N }
        
        Request body:
            message (str): User message
            model (str, optional): Model to use
        """
        data = request.get_json()
        message = data.get("message", "").strip()
        model = data.get("model")
        
        if not message:
            logger.warning("Empty message received in stream", module="chat_api")
            return jsonify({
                "success": False,
                "error": "Empty message"
            }), 400
        
        if not client.is_connected:
            logger.warning("Stream attempted without LM Studio connection", module="chat_api")
            if not client.connect():
                return jsonify({
                    "success": False,
                    "error": "Not connected to LM Studio"
                }), 400
        
        logger.info(f"User message (stream): {message[:100]}...", module="chat_api")
        
        if "messages" not in session:
            session["messages"] = []
        
        session["messages"].append({"role": "user", "content": message})
        
        messages_for_api = list(session["messages"])
        
        start_time = time.time()
        total_completion_tokens = 0
        total_prompt_tokens = 0
        
        def generate():
            nonlocal total_completion_tokens, total_prompt_tokens, start_time
            
            try:
                for chunk_data in client.chat_stream_with_usage(
                    messages=messages_for_api,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    model=model
                ):
                    chunk_text = chunk_data.get("chunk", "")
                    usage = chunk_data.get("usage")
                    is_done = chunk_data.get("done", False)
                    
                    # Yield content chunk
                    if chunk_text:
                        elapsed = time.time() - start_time
                        tokens_per_sec = round(total_completion_tokens / elapsed, 1) if elapsed > 0 else 0
                        
                        event_data = {
                            "content": chunk_text,
                            "tokens_used": total_completion_tokens,
                            "tokens_per_second": tokens_per_sec,
                            "elapsed": round(elapsed, 1)
                        }
                        yield f"event: chunk\ndata: {json.dumps(event_data)}\n\n"
                    
                    # Yield usage data when available
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)
                        
                        total_prompt_tokens = prompt_tokens
                        total_completion_tokens = completion_tokens
                        
                        elapsed = time.time() - start_time
                        tokens_per_sec = round(completion_tokens / elapsed, 1) if elapsed > 0 else 0
                        
                        usage_data = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                            "tokens_per_second": tokens_per_sec,
                            "total_time": round(elapsed, 1)
                        }
                        
                        # Store for later retrieval
                        set_last_token_usage(usage_data)
                        
                        yield f"event: usage\ndata: {json.dumps(usage_data)}\n\n"
                    
                    # Signal completion
                    yield f"event: done\ndata: {{}}\n\n"
                    
            except ConnectionError as e:
                logger.error(f"Connection error during stream: {e}", module="chat_api", exc=True)
                error_data = {"error": str(e)}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
            except Exception as e:
                logger.error(f"Error during stream: {e}", module="chat_api", exc=True)
                error_data = {"error": f"Error: {str(e)}"}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )

    @bp.route("/api/tokens/last", methods=["GET"])
    def get_last_tokens():
        """Get the last received token usage statistics.
        
        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens, tokens_per_second, total_time
        """
        usage = get_last_token_usage()
        
        if not usage:
            return jsonify({
                "success": True,
                "usage": None,
                "message": "No token usage data yet"
            })
        
        return jsonify({
            "success": True,
            "usage": usage
        })

    @bp.route("/api/tokens/reset", methods=["POST"])
    def reset_tokens():
        """Reset the last token usage data."""
        with _token_usage_lock:
            _last_token_usage.clear()
        
        return jsonify({
            "success": True,
            "message": "Token usage data reset"
        })

    return bp
