"""
Discord API Module - Flask Endpoints and Thread Management

This module handles all Discord-related Flask API endpoints and the background
thread management for the Discord bot.
"""

import asyncio
import threading
import os
import discord.errors

from src.logger import logger
from src.config import Config

# Import global state from app module
# These are set by app.py and accessed here
discord_connected = False
discord_bot_instance = None
discord_status_message = "Not connected"
discord_bot_thread = None
_discord_event_loop = None
_bot_stop_event = None
_client = None  # LMStudioClient reference (set by app.py)


def set_app_references(client=None, config=None):
    """Set references to app-level objects needed by this module.
    
    Args:
        client: LMStudioClient instance for AI responses
        config: Config instance for server configuration (FEAT-001)
    """
    global _client, _config
    _client = client
    _config = config


def force_reset_discord_state():
    """Force reset all Discord-related global state.
    
    This is essential when the Flask app restarts via the debug reloader,
    as old Discord bot threads may still be running while module globals
    get reset to their initial values.
    
    After calling this, all Discord state will be cleared and the bot
    can be started fresh.
    """
    global discord_connected, discord_bot_instance, discord_status_message
    global discord_bot_thread, _discord_event_loop, _bot_stop_event
    
    logger.info("Force resetting all Discord state", module="discord_api")
    
    # Reset all global state variables
    discord_connected = False
    discord_bot_instance = None
    discord_status_message = "Not connected"
    discord_bot_thread = None
    _discord_event_loop = None
    _bot_stop_event = None
    
    logger.info("Discord state reset complete", module="discord_api")


def get_or_create_event_loop():
    """Get or create an event loop for the Discord bot."""
    global _discord_event_loop
    if _discord_event_loop is None or _discord_event_loop.is_closed():
        _discord_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_discord_event_loop)
    return _discord_event_loop


def _discord_bot_thread_func(token, stop_event, lm_client=None, config=None):
    """Thread function for running the Discord bot.
    
    Args:
        token: Discord bot token
        stop_event: Threading event for graceful shutdown
        lm_client: LMStudioClient instance for AI responses
        config: Config instance for server configuration (FEAT-001)
    """
    global discord_connected, discord_status_message, discord_bot_instance
    from src.discord_bot import DiscordBot
    
    bot_instance = None
    try:
        if config is None:
            config = Config()
        bot = DiscordBot(
            token=token, 
            lm_studio_client=lm_client, 
            system_prompt=config.system_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            message_delay=config.message_delay,
            config=config  # FEAT-001: Pass config for server/channel access control
        )
        bot_instance = bot
        discord_bot_instance = bot
        loop = get_or_create_event_loop()
        
        # Set up callbacks
        async def on_status_change(status, details):
            global discord_connected, discord_status_message
            discord_status_message = details
            if status == "connected":
                discord_connected = True
            else:
                discord_connected = False
        
        async def on_message(msg_type, author, content, response):
            pass  # Could be used for logging to GUI
        
        bot.set_on_status_change_callback(on_status_change)
        
        # Run the bot until stop event is set or bot stops
        async def run_with_stop():
            stop_task = asyncio.create_task(_wait_for_stop_event(stop_event))
            bot_task = asyncio.create_task(_run_bot_safely(bot, stop_event))
            
            done, pending = await asyncio.wait(
                [stop_task, bot_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        
        loop.run_until_complete(run_with_stop())
        
    except Exception as e:
        discord_connected = False
        discord_status_message = f"Error: {str(e)}"
        print(f"Discord bot error: {e}")
    finally:
        discord_connected = False
        discord_status_message = "Disconnected"


async def _wait_for_stop_event(stop_event):
    """Wait for a threading stop event to be set."""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)


async def _run_bot_safely(bot, stop_event):
    """Run the bot and handle exceptions.
    
    Args:
        bot: DiscordBot instance
        stop_event: Threading event to signal shutdown
        
    Returns:
        tuple: (connected_status, status_message) or (None, None) on success
    """
    try:
        await bot.start_async()
        return (None, None)
    except discord.errors.LoginFailure:
        return (False, "Login failed - check token")
    except asyncio.CancelledError:
        try:
            await asyncio.wait_for(bot.client.close(), timeout=3.0)
        except Exception:
            pass
        return (None, None)
    except Exception as e:
        return (False, f"Error: {str(e)}")


def start_discord_bot_thread(token):
    """Start the Discord bot in a separate thread.
    
    Args:
        token: Discord bot token
        
    Returns:
        tuple: (success, message)
    """
    global discord_bot_thread, _bot_stop_event
    
    # First, ensure any stale state is cleaned up
    if discord_connected:
        logger.warning("Discord state shows connected but attempting fresh start - cleaning up", module="discord_api")
        # Force reset state before starting
        force_reset_discord_state()
    
    # Check if there's still an alive thread from previous run
    if discord_bot_thread and discord_bot_thread.is_alive():
        logger.warning("Existing bot thread still alive, attempting to stop it first", module="discord_api")
        # Try to stop the stale thread
        _bot_stop_event = threading.Event()
        _bot_stop_event.set()  # Signal immediate stop
        try:
            discord_bot_thread.join(timeout=3)
        except Exception as e:
            logger.error(f"Error joining stale thread: {e}", module="discord_api")
        
        if discord_bot_thread.is_alive():
            logger.error("Stale bot thread did not stop, forcing reset", module="discord_api")
            force_reset_discord_state()
            return False, "Previous bot thread could not be stopped. Please restart the application."
    
    # Create fresh stop event and thread
    _bot_stop_event = threading.Event()
    discord_bot_thread = threading.Thread(
        target=_discord_bot_thread_func,
        args=(token, _bot_stop_event, _client, _config),
        daemon=True
    )
    discord_bot_thread.start()
    logger.info("New Discord bot thread started successfully", module="discord_api")
    return True, "Bot starting..."


def stop_discord_bot():
    """Stop the Discord bot gracefully.
    
    This function handles edge cases where the bot thread may be None,
    already stopped, or unresponsive.
    """
    global discord_connected, discord_status_message, _discord_event_loop, _bot_stop_event, discord_bot_instance
    
    logger.info(f"stop_discord_bot called (connected={discord_connected}, thread={discord_bot_thread})", module="discord_api")
    
    # Set stop event if it exists
    if _bot_stop_event:
        _bot_stop_event.set()
        logger.info("Stop event set for Discord bot thread", module="discord_api")
    else:
        # Create and set a stop event even if one wasn't tracked
        _bot_stop_event = threading.Event()
        _bot_stop_event.set()
        logger.info("Created and set stop event (was None)", module="discord_api")
    
    # Stop the bot instance if it exists
    # NOTE: We do NOT try to call client.close() from here. The bot thread's
    # run_with_stop() handles graceful shutdown via _wait_for_stop_event().
    # Calling asyncio.run_until_complete() from a different thread's event loop
    # causes RuntimeWarning: coroutine was never awaited.
    if discord_bot_instance:
        try:
            # Just clear the reference; the thread will clean up the client
            discord_bot_instance = None
        except Exception as e:
            logger.error(f"Clearing bot instance reference: {e}", module="discord_api")
    
    # Join the thread if it's alive
    if discord_bot_thread and discord_bot_thread.is_alive():
        logger.info("Joining Discord bot thread (timeout=10s)", module="discord_api")
        try:
            discord_bot_thread.join(timeout=10)
            if discord_bot_thread.is_alive():
                logger.warning("Discord bot thread did not stop within timeout", module="discord_api")
                discord_bot_thread.daemon = True
            else:
                logger.info("Discord bot thread stopped successfully", module="discord_api")
        except Exception as e:
            logger.error(f"Error waiting for bot thread: {e}", module="discord_api")
    
    # Always reset all state
    discord_connected = False
    discord_status_message = "Disconnected"
    
    logger.info("Discord bot shutdown completed", module="discord_api")


def register_discord_blueprints(bp):
    """Register Discord-related API endpoints with a Blueprint.
    
    Args:
        bp: Flask Blueprint instance
    """
    from flask import jsonify, request
    
    @bp.route("/api/discord/connect", methods=["POST"])
    def discord_connect():
        """Connect to Discord using the bot token."""
        global discord_connected, discord_status_message
        
        logger.info("Discord connect requested", module="discord_api")
        
        if discord_connected:
            logger.warning("Discord connect requested but already connected", module="discord_api")
            return jsonify({
                "success": False,
                "message": "Bot is already connected to Discord"
            }), 400
        
        if _client and not _client.is_connected:
            logger.warning("Discord connect attempted without LM Studio connection", module="discord_api")
            return jsonify({
                "success": False,
                "message": "Please connect to LM Studio first before connecting Discord bot"
            }), 400
        
        data = request.get_json() or {}
        token = data.get("token") or os.getenv("DISCORD_BOT_TOKEN")
        
        if not token:
            logger.error("No Discord bot token available", module="discord_api")
            return jsonify({
                "success": False,
                "message": "No Discord bot token provided. Set DISCORD_BOT_TOKEN in .env file."
            }), 400
        
        if len(token) < 10:
            logger.error(f"Invalid Discord token format (too short)", module="discord_api")
            return jsonify({
                "success": False,
                "message": "Invalid Discord bot token format"
            }), 400
        
        logger.info(f"Starting Discord bot thread...", module="discord_api")
        
        success, message = start_discord_bot_thread(token)
        
        if success:
            logger.info(f"Discord bot thread started successfully", module="discord_api")
            return jsonify({
                "success": True,
                "message": "Discord bot is starting with LM Studio integration..."
            })
        else:
            logger.error(f"Failed to start Discord bot: {message}", module="discord_api")
            return jsonify({
                "success": False,
                "message": message
            }), 400

    @bp.route("/api/discord/status", methods=["GET"])
    def discord_status():
        """Get Discord bot status."""
        return jsonify({
            "connected": discord_connected,
            "status": discord_status_message
        })

    @bp.route("/api/discord/disconnect", methods=["POST"])
    def discord_disconnect():
        """Disconnect from Discord."""
        global discord_connected, discord_status_message
        
        logger.info(f"Discord disconnect requested (connected={discord_connected}, status={discord_status_message})", module="discord_api")
        
        if discord_bot_thread and discord_bot_thread.is_alive():
            stop_discord_bot()
            logger.info("Discord bot thread stopped", module="discord_api")
        elif discord_connected:
            stop_discord_bot()
            logger.info("Discord bot disconnected (was connected)", module="discord_api")
        else:
            stop_discord_bot()
            logger.info("Discord disconnect requested but no active bot thread", module="discord_api")
        
        return jsonify({
            "success": True,
            "message": "Discord bot disconnected"
        })

    @bp.route("/api/discord/info", methods=["GET"])
    def discord_info():
        """Get Discord bot info."""
        if not discord_connected:
            return jsonify({
                "success": False,
                "message": "Bot is not connected"
            }), 400
        
        return jsonify({
            "success": True,
            "connected": discord_connected,
            "status": discord_status_message
        })

    @bp.route("/api/discord/force_reset", methods=["POST"])
    def discord_force_reset():
        """Force reset all Discord state. Use this when the bot is stuck."""
        logger.info("Force Discord reset requested via API", module="discord_api")
        force_reset_discord_state()
        return jsonify({
            "success": True,
            "message": "All Discord state has been reset"
        })

    # ====================================================================
    # Server Configuration Endpoints (FEAT-001)
    # ====================================================================

    @bp.route("/api/servers", methods=["GET"])
    def get_all_servers():
        """Get all server configurations (FEAT-001).
        
        Returns:
            JSON with all server configurations
        """
        from src.config import Config
        config = Config()
        servers = config.get_servers()
        
        return jsonify({
            "success": True,
            "servers": servers
        })

    @bp.route("/api/servers/<server_id>", methods=["GET"])
    def get_server_config(server_id):
        """Get configuration for a specific server (FEAT-001).
        
        Args:
            server_id: Discord server/guild ID
            
        Returns:
            JSON with server configuration
        """
        from src.config import Config
        config = Config()
        server_config = config.get_server_config(server_id)
        
        return jsonify({
            "success": True,
            "server_id": server_id,
            "config": server_config
        })

    @bp.route("/api/servers/update", methods=["POST"])
    def update_server_config():
        """Update server configuration (FEAT-001).
        
        Expected JSON body:
        {
            "server_id": "123456789012345678",
            "config": {
                "enabled": true,
                "allowed_channels": ["111", "222"],
                "denied_channels": ["333"]
            }
        }
        
        Returns:
            JSON with success/failure
        """
        from src.config import Config
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        server_id = data.get("server_id")
        if not server_id:
            return jsonify({"success": False, "error": "server_id is required"}), 400
        
        config = data.get("config", {})
        
        # Validate config
        if not isinstance(config, dict):
            return jsonify({"success": False, "error": "config must be an object"}), 400
        
        if "enabled" not in config:
            config["enabled"] = True
        if "allowed_channels" not in config:
            config["allowed_channels"] = []
        if "denied_channels" not in config:
            config["denied_channels"] = []
        
        config_obj = Config()
        config_obj.set_server_config(server_id, config)
        
        logger.info(f"Server config updated: {server_id} -> enabled={config['enabled']}, "
                    f"allowed={len(config['allowed_channels'])} channels, "
                    f"denied={len(config['denied_channels'])} channels", module="discord_api")
        
        return jsonify({
            "success": True,
            "message": f"Server {server_id} configuration saved",
            "config": config
        })

    @bp.route("/api/servers/add_channel", methods=["POST"])
    def add_channel_to_server():
        """Add a channel to a server's channel list (FEAT-001).
        
        Expected JSON body:
        {
            "server_id": "123456789012345678",
            "channel_id": "111111111111111111",
            "list_type": "allowed"
        }
        
        Returns:
            JSON with success/failure
        """
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        server_id = data.get("server_id")
        channel_id = data.get("channel_id")
        list_type = data.get("list_type", "allowed")
        
        if not server_id or not channel_id:
            return jsonify({"success": False, "error": "server_id and channel_id are required"}), 400
        
        if list_type not in ("allowed", "denied"):
            return jsonify({"success": False, "error": "list_type must be 'allowed' or 'denied'"}), 400
        
        config_obj = Config()
        config_obj.add_channel_to_server(server_id, channel_id, list_type)
        
        return jsonify({
            "success": True,
            "message": f"Channel {channel_id} added to {list_type} list for server {server_id}"
        })

    @bp.route("/api/servers/remove_channel", methods=["POST"])
    def remove_channel_from_server():
        """Remove a channel from a server's channel list (FEAT-001).
        
        Expected JSON body:
        {
            "server_id": "123456789012345678",
            "channel_id": "111111111111111111",
            "list_type": "allowed"
        }
        
        Returns:
            JSON with success/failure
        """
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        server_id = data.get("server_id")
        channel_id = data.get("channel_id")
        list_type = data.get("list_type", "allowed")
        
        if not server_id or not channel_id:
            return jsonify({"success": False, "error": "server_id and channel_id are required"}), 400
        
        if list_type not in ("allowed", "denied"):
            return jsonify({"success": False, "error": "list_type must be 'allowed' or 'denied'"}), 400
        
        config_obj = Config()
        config_obj.remove_channel_from_server(server_id, channel_id, list_type)
        
        return jsonify({
            "success": True,
            "message": f"Channel {channel_id} removed from {list_type} list for server {server_id}"
        })

    @bp.route("/api/servers/remove", methods=["POST"])
    def remove_server_from_config():
        """Remove a server from the configuration (FEAT-001).
        
        Expected JSON body:
        {
            "server_id": "123456789012345678"
        }
        
        Returns:
            JSON with success/failure
        """
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        server_id = data.get("server_id")
        if not server_id:
            return jsonify({"success": False, "error": "server_id is required"}), 400
        
        config_obj = Config()
        config_obj.remove_server_from_config(server_id)
        
        return jsonify({
            "success": True,
            "message": f"Server {server_id} removed from configuration"
        })

    return bp
