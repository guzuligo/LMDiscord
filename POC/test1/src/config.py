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
