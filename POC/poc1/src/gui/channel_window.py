"""
Channel Configuration Window Module

This module implements the popup window for configuring per-channel bot behavior.
It allows setting different behavior settings and allowed tools per Discord channel.

Key Responsibilities:
- Display list of servers/channels the bot has access to
- Allow configuring per-channel behavior settings
- Allow selecting allowed tools per channel
- Save channel-specific configuration to config.json
- Reset channel config to defaults
- Close without saving

UI Elements:
- Server selector (combobox)
- Channel selector (combobox)
- Reply to Messages checkbox
- Read Messages checkbox
- Start Session on Mention checkbox
- Dynamic Allowed Tools checkboxes
- Save Channel Config button
- Reset to Default button
- Close button

Key Features:
- Dynamic tool checkboxes based on registered tools
- Per-channel configuration persistence
- Server/channel listing from Discord API
- Default configuration reset
"""

# TODO: Implement ChannelWindow class
# - Popup window (tk.Toplevel)
# - Server/Channel selectors (comboboxes populated from Discord API)
# - Checkboxes: reply_enabled, read_enabled, mention_session_enabled
# - Dynamic tool checkboxes from tool registry
# - Save: update config.json channels section
# - Reset: clear channel config to defaults
# - Close: destroy window without saving