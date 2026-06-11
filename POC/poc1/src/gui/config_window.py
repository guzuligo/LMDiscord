"""
Configuration Window Module

This module implements the popup window for configuring Discord and LM Studio API credentials.
It provides a dialog for editing the configuration values defined in config.json.

Key Responsibilities:
- Display current configuration values in editable fields
- Allow editing of Discord bot token, app ID, public key
- Allow editing of LM Studio hostname and port
- Save configuration to config.json file
- Cancel without saving
- Validate input before saving

UI Elements:
- Discord Bot Token (password entry)
- Discord App ID (entry)
- Discord Public Key (entry)
- LM Studio Hostname (entry)
- LM Studio Port (entry)
- Save button
- Cancel button

Key Features:
- Password masking for bot token
- Input validation (port number, hostname format)
- Auto-load existing config on window open
- Thread-safe config saving
"""

# TODO: Implement ConfigWindow class
# - Popup window (tk.Toplevel)
# - Entry fields for Discord token (password), app_id, public_key
# - Entry fields for LM Studio hostname, port
# - Save button: validate -> save to config.json -> close
# - Cancel button: close without saving
# - Load existing config on initialization
# - Validation: port must be integer 1-65535, token not empty