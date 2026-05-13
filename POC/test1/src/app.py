"""
Flask Web Application for LM Studio Chat + Discord Bot POC

This module implements a web-based chat interface for communicating with LM Studio
and a Discord bot for Discord integration. It provides a simple REST API and an
HTML chat interface.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.lm_studio_client import LMStudioClient
from src.logger import logger, LogLevel
from src.chat_api import register_chat_blueprints
# Import the discord_api module to access its attributes dynamically.
# We import the module (not individual variables) because bot_core.py updates
# discord_connected/discord_bot_instance directly as module attributes.
# If we imported them as local variables here, they would become stale copies.
from src import discord_api
from src.discord_api import set_app_references, register_discord_blueprints, force_reset_discord_state

# Create local aliases that always read from the module (not stale copies)
def _get_discord_connected():
    return discord_api.discord_connected
def _get_discord_bot_instance():
    return discord_api.discord_bot_instance
def _get_discord_status_message():
    return discord_api.discord_status_message
from flask import Flask, render_template, jsonify, request, session
from flask.blueprints import Blueprint

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize config and client
config = Config()
client = LMStudioClient(config.lm_studio_hostname, config.lm_studio_port)
client.config = config  # Pass config reference for downstream modules

# Link app references for discord_api module
set_app_references(client, config)

# ====================================================================
# Discord State Reset on Startup
# ====================================================================
# When Flask's debug reloader restarts the process, module-level globals
# get reset but old Discord bot threads may still be running.
# Force reset ensures clean state on every app startup.
force_reset_discord_state()

# Re-import force_reset_discord_state after module is fully loaded
# (It was imported above but we want to ensure it's called on the correct module reference)

# Log level tracking for WebSocket-like polling
_current_log_level_filter = LogLevel.DEBUG


# ==================== Main Route ====================

@app.route("/")
def index():
    """Render the main chat page."""
    return render_template("index.html")


# ==================== Status Endpoint ====================

@app.route("/api/status", methods=["GET"])
def status():
    """Get connection status."""
    status_data = {
        "lm_connected": client.is_connected,
        "lm_hostname": client.hostname,
        "lm_port": client.port,
        "lm_model": client.model,
        "lm_models": client.models,
        "discord_connected": _get_discord_connected(),
        "discord_status": _get_discord_status_message()
    }
    
    if _get_discord_bot_instance():
        try:
            status_data["discord_bot_user"] = str(_get_discord_bot_instance().user) if _get_discord_bot_instance().user else None
        except Exception:
            pass
    
    return jsonify(status_data)


# ==================== Logging Endpoints ====================

@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Get log entries with optional filtering."""
    global _current_log_level_filter
    
    limit = request.args.get("limit", 100, type=int)
    level = request.args.get("level", "").upper()
    module = request.args.get("module", "")
    
    if not config.suppress_werkzeug_logging:
        logger.debug(f"Logs requested: limit={limit}, level={level or 'all'}, module={module or 'all'}", module="app")
    
    if level:
        try:
            _current_log_level_filter = LogLevel[level]
            logger.info(f"Log level filter set to: {level}", module="app")
        except KeyError:
            return jsonify({
                "success": False,
                "error": f"Invalid log level: {level}"
            }), 400
    
    level_filter = _current_log_level_filter if level else None
    
    if module:
        logs = logger.get_logs(limit=limit, level_filter=level_filter, module_filter=module)
    else:
        logs = logger.get_logs(limit=limit, level_filter=level_filter)
    
    if not config.suppress_werkzeug_logging:
        logger.debug(f"Returning {len(logs)} log entries", module="app")
    
    return jsonify({
        "success": True,
        "logs": logs,
        "total": len(logs),
        "stats": logger.get_stats()
    })


@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    """Clear all log entries."""
    if not config.suppress_werkzeug_logging:
        logger.info("Logs cleared via API", module="app")
    logger.clear()
    return jsonify({
        "success": True,
        "message": "Logs cleared"
    })


@app.route("/api/logs/stats", methods=["GET"])
def get_logs_stats():
    """Get log statistics."""
    return jsonify({
        "success": True,
        "stats": logger.get_stats()
    })


@app.route("/api/logs/config", methods=["GET"])
def get_log_config():
    """Get logger configuration."""
    return jsonify({
        "success": True,
        "config": {
            "max_entries": logger.max_entries,
            "log_to_file": logger.log_to_file,
            "log_file": logger._log_file,
            "current_filter": _current_log_level_filter.name,
            "total_entries": len(logger._logs)
        }
    })


# ==================== Werkzeug Logging Toggle ====================

def apply_werkzeug_logging_config():
    """Apply Werkzeug logging configuration based on app settings."""
    import logging
    log = logging.getLogger('werkzeug')
    if config.suppress_werkzeug_logging:
        log.setLevel(logging.ERROR)
    else:
        log.setLevel(logging.INFO)


apply_werkzeug_logging_config()


@app.route("/api/settings/logging", methods=["GET"])
def get_logging_settings():
    """Get logging toggle settings."""
    return jsonify({
        "success": True,
        "suppress_werkzeug_logging": config.suppress_werkzeug_logging
    })


@app.route("/api/settings/logging", methods=["POST"])
def set_logging_settings():
    """Update logging toggle settings."""
    data = request.get_json()
    suppress = data.get("suppress_werkzeug_logging", False)
    
    config.suppress_werkzeug_logging = suppress
    config.save()
    
    apply_werkzeug_logging_config()
    
    logger.info(f"Werkzeug logging {'suppressed' if suppress else 'enabled'}", module="app")
    
    return jsonify({
        "success": True,
        "suppress_werkzeug_logging": config.suppress_werkzeug_logging
    })


# ==================== Message Delay Settings ====================

@app.route("/api/settings/delay", methods=["GET"])
def get_delay_settings():
    """Get message delay settings."""
    return jsonify({
        "success": True,
        "message_delay": config.message_delay
    })


@app.route("/api/settings/delay", methods=["POST"])
def set_delay_settings():
    """Update message delay setting."""
    data = request.get_json()
    delay = data.get("message_delay", 5)
    
    if not isinstance(delay, int) or delay < 1 or delay > 30:
        return jsonify({
            "success": False,
            "error": "Delay must be an integer between 1 and 30 seconds"
        }), 400
    
    config.message_delay = delay
    config.save()
    
    # Task 5: Apply to Discord bot if running
    _bot = _get_discord_bot_instance()
    if _bot:
        _bot.set_message_delay(delay)
    
    logger.info(f"Message delay set to: {delay} seconds", module="app")
    
    return jsonify({
        "success": True,
        "message_delay": config.message_delay
    })


# ==================== Max Tokens Settings ====================

@app.route("/api/settings/max_tokens", methods=["GET"])
def get_max_tokens():
    """Get the current max_tokens setting."""
    return jsonify({
        "success": True,
        "max_tokens": config.max_tokens
    })


@app.route("/api/settings/max_tokens", methods=["POST"])
def set_max_tokens():
    """Update the max_tokens setting."""
    data = request.get_json()
    tokens = data.get("max_tokens", 2500)
    
    if not isinstance(tokens, int) or tokens < 1 or tokens > 8192:
        return jsonify({
            "success": False,
            "error": "Max tokens must be an integer between 1 and 8192"
        }), 400
    
    config.max_tokens = tokens
    config.save()
    
    _bot = _get_discord_bot_instance()
    if _bot:
        _bot.set_lm_studio_params(temperature=config.temperature, max_tokens=config.max_tokens)
    
    logger.info(f"Max tokens set to: {tokens}", module="app")
    
    return jsonify({
        "success": True,
        "max_tokens": config.max_tokens
    })


# ==================== System Prompt Settings ====================

@app.route("/api/settings/system_prompt", methods=["GET"])
def get_system_prompt():
    """Get the current system prompt."""
    return jsonify({
        "success": True,
        "system_prompt": config.system_prompt
    })


@app.route("/api/settings/system_prompt", methods=["POST"])
def set_system_prompt():
    """Update the system prompt."""
    data = request.get_json()
    prompt = data.get("system_prompt", "")
    
    if not prompt or not prompt.strip():
        prompt = "You are a helpful assistant in a Discord server."
    
    config.system_prompt = prompt
    config.save()
    
    _bot = _get_discord_bot_instance()
    if _bot:
        _bot.set_system_prompt(prompt)
    
    logger.info(f"System prompt updated", module="app")
    
    return jsonify({
        "success": True,
        "system_prompt": config.system_prompt
    })


# ==================== Temperature Settings ====================

@app.route("/api/settings/temperature", methods=["GET"])
def get_temperature():
    """Get the current temperature setting."""
    return jsonify({
        "success": True,
        "temperature": config.temperature
    })


@app.route("/api/settings/temperature", methods=["POST"])
def set_temperature():
    """Update the temperature setting."""
    data = request.get_json()
    temp = data.get("temperature")
    
    if temp is None:
        return jsonify({
            "success": False,
            "error": "Temperature value is required"
        }), 400
    
    try:
        temp = float(temp)
        if temp < 0.0 or temp > 2.0:
            return jsonify({
                "success": False,
                "error": "Temperature must be between 0.0 and 2.0"
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid temperature value"
        }), 400
    
    config.temperature = temp
    config.save()
    
    # Task 5: Apply to Discord bot if running
    _bot = _get_discord_bot_instance()
    if _bot:
        _bot.set_lm_studio_params(temperature=temp, max_tokens=config.max_tokens)
    
    logger.info(f"Temperature set to: {temp}", module="app")
    
    return jsonify({
        "success": True,
        "temperature": config.temperature
    })


# ==================== Max Response Length Settings ====================

@app.route("/api/settings/max_response_length", methods=["GET"])
def get_max_response_length():
    """Get the current max_response_length setting."""
    return jsonify({
        "success": True,
        "max_response_length": config.max_response_length
    })


@app.route("/api/settings/max_response_length", methods=["POST"])
def set_max_response_length():
    """Update the max_response_length setting."""
    data = request.get_json()
    length = data.get("max_response_length")
    
    if length is None:
        return jsonify({
            "success": False,
            "error": "max_response_length value is required"
        }), 400
    
    try:
        length = int(length)
        if length < 100 or length > 10000:
            return jsonify({
                "success": False,
                "error": "max_response_length must be between 100 and 10000"
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid max_response_length value"
        }), 400
    
    config.max_response_length = length
    config.save()
    
    logger.info(f"Max response length set to: {length}", module="app")
    
    return jsonify({
        "success": True,
        "max_response_length": config.max_response_length
    })


# ==================== Debug Panel Route ====================

@app.route("/debug")
def debug_panel():
    """Render the debug panel page."""
    return render_template("debug.html")


# ==================== Session Management Endpoints ====================

@app.route("/api/discord/sessions", methods=["GET"])
def get_sessions():
    """Get information about active Discord sessions."""
    _bot = _get_discord_bot_instance()
    if not _bot:
        return jsonify({
            "success": False,
            "message": "Discord bot is not running",
            "sessions": []
        })
    
    try:
        sessions = []
        session_info = _bot.get_session_info()
        # get_session_info() returns a dict with "channels" key (dict) and optionally "sessions" (list)
        if isinstance(session_info, dict):
            channels = session_info.get("channels", {})
            if isinstance(channels, dict):
                for channel_id, history_length in channels.items():
                    # Get session data from session manager
                    session = _bot._session_manager.sessions.get(channel_id)
                    if session:
                        sessions.append({
                            "channel_id": channel_id,
                            "user": session.user,
                            "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else "unknown",
                            "last_activity": session.last_activity.strftime("%Y-%m-%d %H:%M:%S") if session.last_activity else "unknown",
                            "message_count": session.message_count,
                            "history_length": history_length
                        })
            elif isinstance(channels, list):
                # channels is a list of channel IDs
                for channel_id in channels:
                    session = _bot._session_manager.sessions.get(channel_id)
                    if session:
                        sessions.append({
                            "channel_id": channel_id,
                            "user": session.user,
                            "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else "unknown",
                            "last_activity": session.last_activity.strftime("%Y-%m-%d %H:%M:%S") if session.last_activity else "unknown",
                            "message_count": session.message_count,
                            "history_length": 0
                        })
        
        return jsonify({
            "success": True,
            "sessions": sessions,
            "active_count": len(sessions)
        })
    except Exception as e:
        logger.error(f"Error getting sessions: {e}", module="app", exc=True)
        return jsonify({
            "success": False,
            "message": str(e),
            "sessions": []
        }), 500


@app.route("/api/discord/clear_session", methods=["POST"])
def clear_session():
    """Clear the session for a specific Discord channel."""
    _bot = _get_discord_bot_instance()
    if not _bot:
        return jsonify({
            "success": False,
            "message": "Discord bot is not running"
        }), 400
    
    data = request.get_json()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        return jsonify({
            "success": False,
            "message": "channel_id is required"
        }), 400
    
    try:
        _bot.clear_session(int(channel_id))
        logger.info(f"Session cleared for channel {channel_id} via debug panel", module="app")
        
        return jsonify({
            "success": True,
            "message": f"Session cleared for channel {channel_id}"
        })
    except Exception as e:
        logger.error(f"Error clearing session: {e}", module="app", exc=True)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/discord/clear_all_sessions", methods=["POST"])
def clear_all_sessions():
    """Clear all Discord sessions."""
    _bot = _get_discord_bot_instance()
    if not _bot:
        return jsonify({
            "success": False,
            "message": "Discord bot is not running"
        }), 400
    
    try:
        # Get all active channel IDs
        channels = list(_bot._session_manager.sessions.keys())
        cleared_count = 0
        
        for channel_id in channels:
            _bot.clear_session(int(channel_id))
            cleared_count += 1
        
        logger.info(f"All {cleared_count} sessions cleared via debug panel", module="app")
        
        return jsonify({
            "success": True,
            "message": f"All {cleared_count} sessions cleared",
            "cleared_count": cleared_count
        })
    except Exception as e:
        logger.error(f"Error clearing all sessions: {e}", module="app", exc=True)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/tokens/debug/refresh", methods=["GET"])
def get_debug_token_metrics():
    """Get token metrics for debug panel."""
    _bot = _get_discord_bot_instance()
    if not _bot:
        return jsonify({
            "success": True,
            "usage": None,
            "message": "Discord bot is not running"
        })
    
    try:
        usage = _bot.get_last_discord_token_usage()
        return jsonify({
            "success": True,
            "usage": usage
        })
    except Exception as e:
        logger.error(f"Error getting token metrics: {e}", module="app", exc=True)
        return jsonify({
            "success": False,
            "usage": None,
            "message": str(e)
        }), 500


# ==================== Blueprint Registration ====================

# Create blueprints for modular routing
chat_bp = Blueprint("chat", __name__)
discord_bp = Blueprint("discord", __name__)

# Register endpoint modules
register_chat_blueprints(chat_bp, client, config)
register_discord_blueprints(discord_bp)

# Register blueprints with main app
app.register_blueprint(chat_bp)
app.register_blueprint(discord_bp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)