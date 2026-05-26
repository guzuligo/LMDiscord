"""
Memory Module

SQLite-based memory storage with high-level management API.

Components:
- memorylite: SQLite storage client with CRUD, search, and user management
- memory_manager: High-level API for session memory creation, keyword extraction,
  memory type assignment, and relevant memory retrieval
- memorybot: Specialized memory search assistant with fresh isolated context
- memorybot_prompt: System prompt templates for MemoryBot

Usage:
    from src.memory import MemoryManager, MemoryBot, get_memorybot_system_prompt

    manager = MemoryManager(db_path="data/memory.db")
    manager.ensure_user("123456789", "username")
    manager.create_session("sess_001", "123456789", guild_id="guild_1", channel_id="chan_1")
    memory = manager.create_session_memory("sess_001", "Conversation content", "123456789")
    relevant = manager.get_relevant_memories("search query", user_id="123456789")
    
    memorybot = MemoryBot(manager)
    result = memorybot.run_search("what did user say about project?")
    manager.close()
"""

from .memorylite import MemoryLite
from .memory_manager import MemoryManager
from .memorybot import MemoryBot
from .memorybot_prompt import (
    MEMORYBOT_SYSTEM_PROMPT,
    MEMORYBOT_USER_PROMPT,
    MEMORYBOT_REFINEMENT_PROMPT,
    get_memorybot_system_prompt,
    get_memorybot_user_prompt,
    get_memorybot_refinement_prompt,
)

__all__ = [
    "MemoryLite",
    "MemoryManager",
    "MemoryBot",
    "MEMORYBOT_SYSTEM_PROMPT",
    "MEMORYBOT_USER_PROMPT",
    "MEMORYBOT_REFINEMENT_PROMPT",
    "get_memorybot_system_prompt",
    "get_memorybot_user_prompt",
    "get_memorybot_refinement_prompt",
]
