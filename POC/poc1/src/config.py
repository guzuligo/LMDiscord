"""
Configuration Management Module

Handles loading and saving application configuration from/to config.json.
"""

import json
import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration manager."""
    
    DEFAULT_CONFIG = {
        "discord": {
            "bot_token": "",
            "app_id": "",
            "public_key": ""
        },
        "lm_studio": {
            "hostname": "localhost",
            "port": 1234,
            "api_endpoint": "/v1/chat/completions"
        },
        "settings": {
            "bot_prefix": "@",
            "max_response_length": 2000,
            "temperature": 0.7,
            "max_tokens": 2500,
            "enabled_tools": ["math_calc", "image_describe"],
            "suppress_werkzeug_logging": False,
            "message_delay": 5,
            "system_prompt": "You are a helpful assistant in a Discord server.",
            "allowed_image_hostnames": [
                "cdn.discordapp.com",
                "media.discordapp.net"
            ]
        },
        "tools_config": {
            "reasoning_brevity": True,
            "tool_max_tokens": 2048,
            "tool_temperature": 0.3,
            "final_max_tokens": 8192,
            "use_tool_calling": True,
            "max_tool_turns": 5,
            "context_lm_max_tokens": 4096
        },
        "context_management": {
            "compression": {
                "token_threshold_percent": 80,
                "message_count_threshold": 20,
                "messages_to_keep_fresh": 6,
                "default_summary_length": 300,
                "enabled": True
            }
        },
        "servers": {}
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config file. Defaults to config.json in project root.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).parent.parent / "config.json"
        
        self._data = dict(self.DEFAULT_CONFIG)
        self.load()
    
    def load(self) -> None:
        """Load configuration from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    saved = json.load(f)
                    # Merge saved config with defaults
                    for key in self._data:
                        if key in saved:
                            if isinstance(self._data[key], dict):
                                self._data[key].update(saved[key])
                            else:
                                self._data[key] = saved[key]
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file: {e}")
        else:
            self.save()
    
    def save(self) -> None:
        """Save configuration to JSON file."""
        with open(self.config_path, "w") as f:
            json.dump(self._data, f, indent=2)
    
    def get(self, section: str, key: str, default=None):
        """Get a configuration value.
        
        Args:
            section: Configuration section (e.g., 'lm_studio')
            key: Configuration key (e.g., 'hostname')
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        return self._data.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value) -> None:
        """Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value
    
    @property
    def lm_studio_hostname(self) -> str:
        return self.get("lm_studio", "hostname", "localhost")
    
    @lm_studio_hostname.setter
    def lm_studio_hostname(self, value: str) -> None:
        self.set("lm_studio", "hostname", value)
    
    @property
    def lm_studio_port(self) -> int:
        return self.get("lm_studio", "port", 1234)
    
    @lm_studio_port.setter
    def lm_studio_port(self, value: int) -> None:
        self.set("lm_studio", "port", value)
    
    @property
    def lm_studio_url(self) -> str:
        """Get the full LM Studio API URL."""
        return f"http://{self.lm_studio_hostname}:{self.lm_studio_port}{self.get('lm_studio', 'api_endpoint', '/v1/chat/completions')}"
    
    @property
    def discord_token(self) -> str:
        return self.get("discord", "bot_token", "")
    
    @discord_token.setter
    def discord_token(self, value: str) -> None:
        self.set("discord", "bot_token", value)
    
    @property
    def temperature(self) -> float:
        """Get temperature setting."""
        return self.get("settings", "temperature", 0.7)
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        """Set temperature setting."""
        self.set("settings", "temperature", value)
    
    @property
    def max_tokens(self) -> int:
        return self.get("settings", "max_tokens", 2500)
    
    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        self.set("settings", "max_tokens", value)
    
    @property
    def max_response_length(self) -> int:
        """Get max response length setting."""
        return self.get("settings", "max_response_length", 2000)
    
    @max_response_length.setter
    def max_response_length(self, value: int) -> None:
        """Set max response length setting."""
        self.set("settings", "max_response_length", value)
    
    @property
    def suppress_werkzeug_logging(self) -> bool:
        return self.get("settings", "suppress_werkzeug_logging", False)
    
    @suppress_werkzeug_logging.setter
    def suppress_werkzeug_logging(self, value: bool) -> None:
        self.set("settings", "suppress_werkzeug_logging", value)
    
    @property
    def message_delay(self) -> int:
        return self.get("settings", "message_delay", 5)
    
    @message_delay.setter
    def message_delay(self, value: int) -> None:
        self.set("settings", "message_delay", value)
    
    @property
    def system_prompt(self) -> str:
        return self.get("settings", "system_prompt", "You are a helpful assistant in a Discord server.")
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        self.set("settings", "system_prompt", value)
    
    @property
    def allowed_image_hostnames(self) -> list:
        """Get list of allowed hostnames for image downloads."""
        return self.get("settings", "allowed_image_hostnames", [
            "cdn.discordapp.com",
            "media.discordapp.net"
        ])
    
    @allowed_image_hostnames.setter
    def allowed_image_hostnames(self, value: list) -> None:
        """Set list of allowed hostnames for image downloads."""
        self.set("settings", "allowed_image_hostnames", value)

    # ====================================================================
    # Logging Configuration Properties
    # ====================================================================

    @property
    def log_level(self) -> str:
        """Get the log level setting.
        
        Returns:
            Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        return self.get("settings", "log_level", "WARNING")

    @log_level.setter
    def log_level(self, value: str) -> None:
        """Set the log level setting.
        
        Args:
            value: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        self.set("settings", "log_level", value.upper())

    # ====================================================================
    # Server Configuration Methods (FEAT-001)
    # ====================================================================

    def get_servers(self) -> dict:
        """Get all server configurations.
        
        Returns:
            Dict of server_id -> server config
        """
        return self._data.get("servers", {})

    def get_server_config(self, server_id: str) -> dict:
        """Get configuration for a specific server.
        
        Args:
            server_id: Discord server/guild ID
            
        Returns:
            Server config dict with enabled, allowed_channels, denied_channels
            Returns default config (enabled, all channels) if server not in config.
        """
        servers = self.get_servers()
        if server_id in servers:
            server = servers[server_id]
            return {
                "enabled": server.get("enabled", True),
                "allowed_channels": server.get("allowed_channels", []),
                "denied_channels": server.get("denied_channels", [])
            }
        # Default: enabled, all channels allowed
        return {
            "enabled": True,
            "allowed_channels": [],
            "denied_channels": []
        }

    def is_server_enabled(self, server_id: str) -> bool:
        """Check if a server is enabled.
        
        Args:
            server_id: Discord server/guild ID
            
        Returns:
            True if server is enabled or not in config (default), False if explicitly disabled
        """
        config = self.get_server_config(server_id)
        return config["enabled"]

    def is_channel_allowed(self, server_id: str, channel_id: str) -> bool:
        """Check if a channel is allowed in a server.
        
        Rules:
        - If denied_channels contains channel_id → False (takes precedence)
        - If allowed_channels is non-empty and doesn't contain channel_id → False
        - Otherwise → True
        
        Args:
            server_id: Discord server/guild ID
            channel_id: Discord channel ID
            
        Returns:
            True if the channel is allowed, False otherwise
        """
        config = self.get_server_config(server_id)
        
        # Denied channels take precedence
        if channel_id in config["denied_channels"]:
            return False
        
        # If allowed_channels is empty, all channels are allowed
        if not config["allowed_channels"]:
            return True
        
        # Check if channel is in allowed list
        return channel_id in config["allowed_channels"]

    def set_server_config(self, server_id: str, config: dict) -> None:
        """Set configuration for a server.
        
        Args:
            server_id: Discord server/guild ID
            config: Dict with 'enabled', 'allowed_channels', 'denied_channels'
        """
        servers = self.get_servers()
        servers[server_id] = {
            "enabled": config.get("enabled", True),
            "allowed_channels": config.get("allowed_channels", []),
            "denied_channels": config.get("denied_channels", [])
        }
        self._data["servers"] = servers
        self.save()

    def add_channel_to_server(self, server_id: str, channel_id: str, 
                               list_type: str = "allowed") -> None:
        """Add a channel to a server's channel list.
        
        Args:
            server_id: Discord server/guild ID
            channel_id: Discord channel ID to add
            list_type: "allowed" or "denied"
        """
        config = self.get_server_config(server_id)
        
        if list_type == "allowed":
            if channel_id not in config["allowed_channels"]:
                config["allowed_channels"].append(channel_id)
        elif list_type == "denied":
            if channel_id not in config["denied_channels"]:
                config["denied_channels"].append(channel_id)
        
        self.set_server_config(server_id, config)

    def remove_channel_from_server(self, server_id: str, channel_id: str,
                                    list_type: str = "allowed") -> None:
        """Remove a channel from a server's channel list.
        
        Args:
            server_id: Discord server/guild ID
            channel_id: Discord channel ID to remove
            list_type: "allowed" or "denied"
        """
        config = self.get_server_config(server_id)
        
        if list_type == "allowed":
            if channel_id in config["allowed_channels"]:
                config["allowed_channels"].remove(channel_id)
        elif list_type == "denied":
            if channel_id in config["denied_channels"]:
                config["denied_channels"].remove(channel_id)
        
        self.set_server_config(server_id, config)

    def remove_server_from_config(self, server_id: str) -> None:
        """Remove a server from the configuration.
        
        Args:
            server_id: Discord server/guild ID to remove
        """
        servers = self.get_servers()
        if server_id in servers:
            del servers[server_id]
            self._data["servers"] = servers
            self.save()

    # ====================================================================
    # LM Instance Integration (FEAT-006)
    # ====================================================================

    @property
    def lm_model(self) -> str:
        """Get the selected model name (backward compat, reads from lm_instances active)."""
        active_lm = self._data.get("lm_instances", {}).get(
            self._data.get("active_instance", "local"), {}
        )
        return active_lm.get("selected_model", "")

    @lm_model.setter
    def lm_model(self, value: str) -> None:
        """Set the selected model name on the active instance."""
        active_id = self._data.get("active_instance", "local")
        if active_id in self._data.get("lm_instances", {}):
            self._data["lm_instances"][active_id]["selected_model"] = value
            self.save()

    # ====================================================================
    # Tools Configuration Properties
    # ====================================================================

    @property
    def tool_reasoning_brevity(self) -> bool:
        """Get reasoning brevity setting."""
        return self.get("tools_config", "reasoning_brevity", True)

    @tool_reasoning_brevity.setter
    def tool_reasoning_brevity(self, value: bool) -> None:
        """Set reasoning brevity setting."""
        self.set("tools_config", "reasoning_brevity", value)

    @property
    def tool_max_tokens(self) -> int:
        """Get max_tokens for tool-calling requests."""
        return self.get("tools_config", "tool_max_tokens", 2048)

    @tool_max_tokens.setter
    def tool_max_tokens(self, value: int) -> None:
        """Set max_tokens for tool-calling requests."""
        self.set("tools_config", "tool_max_tokens", value)

    @property
    def tool_temperature(self) -> float:
        """Get temperature for tool-calling requests."""
        return self.get("tools_config", "tool_temperature", 0.3)

    @tool_temperature.setter
    def tool_temperature(self, value: float) -> None:
        """Set temperature for tool-calling requests."""
        self.set("tools_config", "tool_temperature", value)

    @property
    def final_max_tokens(self) -> int:
        """Get max_tokens for final response requests."""
        return self.get("tools_config", "final_max_tokens", 8192)

    @final_max_tokens.setter
    def final_max_tokens(self, value: int) -> None:
        """Set max_tokens for final response requests."""
        self.set("tools_config", "final_max_tokens", value)

    @property
    def tools_use_tool_calling(self) -> bool:
        """Get tool calling enabled setting."""
        return self.get("tools_config", "use_tool_calling", True)

    @tools_use_tool_calling.setter
    def tools_use_tool_calling(self, value: bool) -> None:
        """Set tool calling enabled setting."""
        self.set("tools_config", "use_tool_calling", value)

    @property
    def max_tool_turns(self) -> int:
        """Get maximum number of tool turns per message processing."""
        return self.get("tools_config", "max_tool_turns", 5)

    @max_tool_turns.setter
    def max_tool_turns(self, value: int) -> None:
        """Set maximum number of tool turns per message processing."""
        self.set("tools_config", "max_tool_turns", value)

    def get_tools_config(self) -> dict:
        """Get all tools configuration as a dict."""
        tc = self._data.get("tools_config", {})
        return {
            "reasoning_brevity": tc.get("reasoning_brevity", True),
            "tool_max_tokens": tc.get("tool_max_tokens", 2048),
            "tool_temperature": tc.get("tool_temperature", 0.3),
            "final_max_tokens": tc.get("final_max_tokens", 8192),
            "use_tool_calling": tc.get("use_tool_calling", True),
            "max_tool_turns": tc.get("max_tool_turns", 5),
            "context_lm_max_tokens": tc.get("context_lm_max_tokens", 4096)
        }

    def set_tools_config(self, config: dict) -> None:
        """Set tools configuration from a dict."""
        self._data.setdefault("tools_config", {})
        for key, value in config.items():
            self._data["tools_config"][key] = value
        self.save()

    # ====================================================================
    # Memory Configuration Properties
    # ====================================================================

    @property
    def memory_db_path(self) -> str:
        """Get the memory database file path."""
        return self.get("memory_config", "db_path", "user/data/memory/memory.db")

    @memory_db_path.setter
    def memory_db_path(self, value: str) -> None:
        """Set the memory database file path."""
        self.set("memory_config", "db_path", value)

    def get_memory_config(self) -> dict:
        """Get all memory configuration as a dict."""
        mc = self._data.get("memory_config", {})
        return {
            "db_path": mc.get("db_path", "user/data/memory/memory.db")
        }

    def set_memory_config(self, config: dict) -> None:
        """Set memory configuration from a dict."""
        self._data.setdefault("memory_config", {})
        for key, value in config.items():
            self._data["memory_config"][key] = value
        self.save()

    # ====================================================================
    # Context Management Configuration Properties
    # ====================================================================

    @property
    def context_compression_enabled(self) -> bool:
        """Get context compression enabled setting."""
        return self.get("context_management", "compression", {}).get("enabled", True)

    @context_compression_enabled.setter
    def context_compression_enabled(self, value: bool) -> None:
        """Set context compression enabled setting."""
        self._data.setdefault("context_management", {})
        self._data["context_management"]["compression"] = {
            **self._data["context_management"].get("compression", {}),
            "enabled": value
        }
        self.save()

    @property
    def context_compression_token_threshold(self) -> int:
        """Get token threshold percentage for context compression trigger."""
        return self.get("context_management", "compression", {}).get("token_threshold_percent", 80)

    @context_compression_token_threshold.setter
    def context_compression_token_threshold(self, value: int) -> None:
        """Set token threshold percentage for context compression trigger."""
        self._data.setdefault("context_management", {})
        self._data["context_management"]["compression"] = {
            **self._data["context_management"].get("compression", {}),
            "token_threshold_percent": value
        }
        self.save()

    @property
    def context_compression_message_threshold(self) -> int:
        """Get message count threshold for context compression trigger."""
        return self.get("context_management", "compression", {}).get("message_count_threshold", 20)

    @context_compression_message_threshold.setter
    def context_compression_message_threshold(self, value: int) -> None:
        """Set message count threshold for context compression trigger."""
        self._data.setdefault("context_management", {})
        self._data["context_management"]["compression"] = {
            **self._data["context_management"].get("compression", {}),
            "message_count_threshold": value
        }
        self.save()

    @property
    def context_compression_messages_to_keep_fresh(self) -> int:
        """Get number of recent messages to keep uncompressed."""
        return self.get("context_management", "compression", {}).get("messages_to_keep_fresh", 6)

    @context_compression_messages_to_keep_fresh.setter
    def context_compression_messages_to_keep_fresh(self, value: int) -> None:
        """Set number of recent messages to keep uncompressed."""
        self._data.setdefault("context_management", {})
        self._data["context_management"]["compression"] = {
            **self._data["context_management"].get("compression", {}),
            "messages_to_keep_fresh": value
        }
        self.save()

    @property
    def context_compression_default_summary_length(self) -> int:
        """Get default summary length for context compression."""
        return self.get("context_management", "compression", {}).get("default_summary_length", 300)

    @context_compression_default_summary_length.setter
    def context_compression_default_summary_length(self, value: int) -> None:
        """Set default summary length for context compression."""
        self._data.setdefault("context_management", {})
        self._data["context_management"]["compression"] = {
            **self._data["context_management"].get("compression", {}),
            "default_summary_length": value
        }
        self.save()

    def get_context_management_config(self) -> dict:
        """Get all context management configuration as a dict."""
        cm = self._data.get("context_management", {})
        return {
            "compression": {
                "token_threshold_percent": cm.get("compression", {}).get("token_threshold_percent", 80),
                "message_count_threshold": cm.get("compression", {}).get("message_count_threshold", 20),
                "messages_to_keep_fresh": cm.get("compression", {}).get("messages_to_keep_fresh", 6),
                "default_summary_length": cm.get("compression", {}).get("default_summary_length", 300),
                "enabled": cm.get("compression", {}).get("enabled", True)
            }
        }

    def set_context_management_config(self, config: dict) -> None:
        """Set context management configuration from a dict."""
        self._data.setdefault("context_management", {})
        for key, value in config.items():
            self._data["context_management"][key] = value
        self.save()
