"""
Memory Tool

This module implements a tool for saving and searching memories using the memorylite system.
It integrates with the MemoryLite client for SQLite-based memory storage and retrieval.

Key Responsibilities:
- Save conversation summaries to memory after session ends
- Search existing memories by keywords
- Retrieve memories by ID
- List memories with filters
- Delete memories
- Get memory statistics
- Link memories to users

Tool Definition:
- name: "memory_tool"
- description: "Save, search, retrieve, and manage memories using memorylite"
- operations: save, search, retrieve, delete, list, statistics, search_recent, search_by_importance
"""

import json
from typing import Optional

from ..base import BaseTool, ToolResult
from src.memory.memorylite import MemoryLite


class MemoryTool(BaseTool):
    """Tool for saving, searching, and managing memories using memorylite.
    
    This tool provides LM Studio with the ability to:
    - Save information to persistent memory (save operation)
    - Search memories by keywords (search operation)
    - Retrieve specific memories by ID (retrieve operation)
    - List memories with optional filters (list operation)
    - Delete memories (delete operation)
    - Get memory storage statistics (statistics operation)
    - Search recently updated memories (search_recent operation)
    - Search high-importance memories (search_by_importance operation)
    """

    def __init__(self, memory: Optional[MemoryLite] = None, db_path: Optional[str] = None):
        """Initialize the MemoryTool.
        
        Args:
            memory: Optional MemoryLite instance. If not provided, creates a default one.
            db_path: Optional database path for MemoryLite. Ignored if memory is provided.
        """
        if memory is not None:
            self._memory = memory
        elif db_path is not None:
            self._memory = MemoryLite(db_path=db_path)
        else:
            self._memory = MemoryLite()

    @property
    def name(self) -> str:
        return "memory_tool"

    @property
    def description(self) -> str:
        return (
            "Save, search, retrieve, and manage memories for persistent knowledge. "
            "Use 'save' to store important facts, preferences, or context. "
            "Use 'search' to find memories by keywords. "
            "Use 'retrieve' to get a specific memory by ID. "
            "Use 'list' to browse memories with optional filters. "
            "Use 'delete' to remove a memory. "
            "Use 'statistics' to get memory storage stats. "
            "Use 'search_recent' to get recently updated memories. "
            "Use 'search_by_importance' to get high-importance memories. "
            "Memory types: fact, preference, context, relationship, deprecated. "
            "This tool enables persistent knowledge across conversations."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform: save, search, retrieve, list, delete, statistics, search_recent, search_by_importance",
                    "enum": ["save", "search", "retrieve", "list", "delete", "statistics", "search_recent", "search_by_importance"]
                },
                # Parameters for 'save'
                "content": {
                    "type": "string",
                    "description": "The memory content text to save (required for save operation)"
                },
                "memory_type": {
                    "type": "string",
                    "description": "Memory type: fact, preference, context, relationship, or deprecated (default: fact)",
                    "enum": ["fact", "preference", "context", "relationship", "deprecated"],
                    "default": "fact"
                },
                "user_ids": {
                    "type": "array",
                    "description": "List of user IDs associated with this memory",
                    "items": {"type": "string"}
                },
                "session_id": {
                    "type": "string",
                    "description": "Source session ID for tracking memory origin"
                },
                "explicit_weight": {
                    "type": "number",
                    "description": "Explicit importance weight (0.0-1.0, default: 0.5)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                # Parameters for 'search'
                "keywords": {
                    "type": "array",
                    "description": "List of keywords to search for in memory content",
                    "items": {"type": "string"}
                },
                # Parameters for 'retrieve'
                "memory_id": {
                    "type": "string",
                    "description": "Memory ID to retrieve (required for retrieve operation)"
                },
                # Parameters for 'list'
                "list_memory_type": {
                    "type": "string",
                    "description": "Filter by memory type when listing"
                },
                "list_status": {
                    "type": "string",
                    "description": "Filter by status when listing: active, deprecated, expired, superseded"
                },
                "list_user_id": {
                    "type": "string",
                    "description": "Filter by user ID when listing"
                },
                "list_limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return (default: 20)",
                    "default": 20
                },
                "list_order_by": {
                    "type": "string",
                    "description": "Sort field: created_at, updated_at, importance, update_count (default: updated_at)",
                    "default": "updated_at"
                },
                # Parameters for 'delete'
                # memory_id is reused from retrieve
                # Parameters for 'search_recent'
                "recent_limit": {
                    "type": "integer",
                    "description": "Maximum number of recent memories to return (default: 10)",
                    "default": 10
                },
                # Parameters for 'search_by_importance'
                "min_importance": {
                    "type": "number",
                    "description": "Minimum importance threshold (0.0-1.0, default: 0.5)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10, used by search and search_by_importance)",
                    "default": 10
                }
            },
            "required": ["operation"]
        }

    def execute(self, operation: str, **kwargs) -> ToolResult:
        """Execute the memory operation.
        
        Args:
            operation: The operation to perform (save, search, retrieve, list, delete, 
                       statistics, search_recent, search_by_importance)
            **kwargs: Additional parameters for the operation
            
        Returns:
            ToolResult with content as formatted memory data or error message
        """
        try:
            if operation == "save":
                return self._save_memory(kwargs)
            elif operation == "search":
                return self._search_memories(kwargs)
            elif operation == "retrieve":
                return self._retrieve_memory(kwargs)
            elif operation == "list":
                return self._list_memories(kwargs)
            elif operation == "delete":
                return self._delete_memory(kwargs)
            elif operation == "statistics":
                return self._get_statistics()
            elif operation == "search_recent":
                return self._search_recent(kwargs)
            elif operation == "search_by_importance":
                return self._search_by_importance(kwargs)
            else:
                return ToolResult(
                    status="error",
                    message=f"Unknown operation: {operation}. Valid operations: save, search, retrieve, list, delete, statistics, search_recent, search_by_importance",
                    error=f"Unknown operation: {operation}",
                    success=False,
                    content=""
                )
        except Exception as exc:
            return ToolResult(
                status="error",
                message=f"Memory tool execution failed: {str(exc)}",
                error=f"Memory tool execution failed: {str(exc)}",
                success=False,
                content=""
            )

    def _save_memory(self, kwargs: dict) -> ToolResult:
        """Save a new memory.
        
        Args:
            kwargs: Parameters including content, memory_type, user_ids, session_id, explicit_weight
            
        Returns:
            ToolResult with the saved memory details
        """
        content = kwargs.get("content")
        if not content:
            return ToolResult(
                status="error",
                message="Missing required parameter: content. Please provide the memory content to save.",
                error="Missing required parameter: content",
                success=False,
                content=""
            )

        memory_type = kwargs.get("memory_type", "fact")
        user_ids = kwargs.get("user_ids")
        session_id = kwargs.get("session_id")
        explicit_weight = kwargs.get("explicit_weight", 0.5)

        try:
            memory = self._memory.create_memory(
                content=content,
                memory_type=memory_type,
                user_ids=user_ids,
                session_id=session_id,
                explicit_weight=explicit_weight,
            )
            return ToolResult(
                status="success",
                message=self._format_memory(memory),
                data=self._format_memory(memory),
                success=True,
                content=self._format_memory(memory)
            )
        except ValueError as exc:
            return ToolResult(
                status="error",
                message=f"Failed to save memory: {str(exc)}",
                error=str(exc),
                success=False,
                content=""
            )

    def _search_memories(self, kwargs: dict) -> ToolResult:
        """Search memories by keywords.
        
        Args:
            kwargs: Parameters including keywords, limit, memory_type
            
        Returns:
            ToolResult with matching memories
        """
        keywords = kwargs.get("keywords", [])
        if not keywords:
            return ToolResult(
                status="error",
                message="Missing required parameter: keywords. Please provide a list of search terms.",
                error="Missing required parameter: keywords",
                success=False,
                content=""
            )

        limit = kwargs.get("limit", 10)
        memory_type = kwargs.get("memory_type")

        results = self._memory.search_by_keywords(
            keywords=keywords,
            limit=limit,
            memory_type=memory_type,
        )

        if not results:
            return ToolResult(
                status="no_results",
                message="No memories found matching the specified keywords.",
                success=True,
                content="No memories found matching the specified keywords."
            )

        return ToolResult(
            status="success",
            message=self._format_memory_list(results, f"Search Results ({len(results)} memories):"),
            data=self._format_memory_list(results, f"Search Results ({len(results)} memories):"),
            success=True,
            content=self._format_memory_list(results, f"Search Results ({len(results)} memories):")
        )

    def _retrieve_memory(self, kwargs: dict) -> ToolResult:
        """Retrieve a specific memory by ID.
        
        Args:
            kwargs: Parameters including memory_id
            
        Returns:
            ToolResult with the memory details
        """
        memory_id = kwargs.get("memory_id")
        if not memory_id:
            return ToolResult(
                status="error",
                message="Missing required parameter: memory_id. Please provide a memory ID to retrieve.",
                error="Missing required parameter: memory_id",
                success=False,
                content=""
            )

        memory = self._memory.get_memory(memory_id)
        if not memory:
            return ToolResult(
                status="no_results",
                message=f"Memory not found: {memory_id}",
                success=True,
                content=f"Memory not found: {memory_id}"
            )

        return ToolResult(
            status="success",
            message=self._format_memory(memory),
            data=self._format_memory(memory),
            success=True,
            content=self._format_memory(memory)
        )

    def _list_memories(self, kwargs: dict) -> ToolResult:
        """List memories with optional filters.
        
        Args:
            kwargs: Parameters including list_memory_type, list_status, list_user_id, list_limit, list_order_by
            
        Returns:
            ToolResult with the memory list
        """
        memory_type = kwargs.get("list_memory_type")
        status = kwargs.get("list_status")
        user_id = kwargs.get("list_user_id")
        limit = kwargs.get("list_limit", 20)
        order_by = kwargs.get("list_order_by", "updated_at")

        results = self._memory.list_memories(
            memory_type=memory_type,
            status=status,
            user_id=user_id,
            limit=limit,
            order_by=order_by,
        )

        if not results:
            return ToolResult(
                status="no_results",
                message="No memories found matching the specified filters.",
                success=True,
                content="No memories found matching the specified filters."
            )

        return ToolResult(
            status="success",
            message=self._format_memory_list(results, f"Memory List ({len(results)} memories):"),
            data=self._format_memory_list(results, f"Memory List ({len(results)} memories):"),
            success=True,
            content=self._format_memory_list(results, f"Memory List ({len(results)} memories):")
        )

    def _delete_memory(self, kwargs: dict) -> ToolResult:
        """Delete a memory by ID.
        
        Args:
            kwargs: Parameters including memory_id
            
        Returns:
            ToolResult indicating success or failure
        """
        memory_id = kwargs.get("memory_id")
        if not memory_id:
            return ToolResult(
                status="error",
                message="Missing required parameter: memory_id. Please provide a memory ID to delete.",
                error="Missing required parameter: memory_id",
                success=False,
                content=""
            )

        deleted = self._memory.delete_memory(memory_id)
        if deleted:
            return ToolResult(
                status="success",
                message=f"Memory {memory_id} has been deleted.",
                data=f"Memory {memory_id} has been deleted.",
                success=True,
                content=f"Memory {memory_id} has been deleted."
            )
        else:
            return ToolResult(
                status="no_results",
                message=f"Memory not found: {memory_id}",
                success=True,
                content=f"Memory not found: {memory_id}"
            )

    def _get_statistics(self) -> ToolResult:
        """Get memory storage statistics.
        
        Returns:
            ToolResult with statistics summary
        """
        stats = self._memory.get_statistics()

        lines = [
            "📊 Memory Statistics:",
            "",
            f"  Total memories: {stats.get('total_memories', 0)}",
            f"  Total users: {stats.get('total_users', 0)}",
            f"  Total sessions: {stats.get('total_sessions', 0)}",
            f"  Active sessions: {stats.get('active_sessions', 0)}",
            "",
            "  By type:",
        ]

        by_type = stats.get("by_type", {})
        if by_type:
            for mtype, count in sorted(by_type.items()):
                lines.append(f"    - {mtype}: {count}")
        else:
            lines.append("    (none)")

        lines.append("")
        lines.append("  By status:")

        by_status = stats.get("by_status", {})
        if by_status:
            for status, count in sorted(by_status.items()):
                lines.append(f"    - {status}: {count}")
        else:
            lines.append("    (none)")

        avg_imp = stats.get("avg_importance")
        max_imp = stats.get("max_importance")
        min_imp = stats.get("min_importance")
        if avg_imp is not None:
            lines.extend([
                "",
                f"  Importance range: {min_imp:.3f} - {max_imp:.3f}",
                f"  Average importance: {avg_imp:.3f}",
            ])

        formatted = "\n".join(lines)
        return ToolResult(
            status="success",
            message=formatted,
            data=formatted,
            success=True,
            content=formatted
        )

    def _search_recent(self, kwargs: dict) -> ToolResult:
        """Search recently updated memories.
        
        Args:
            kwargs: Parameters including limit
            
        Returns:
            ToolResult with recent memories
        """
        limit = kwargs.get("recent_limit", kwargs.get("limit", 10))

        results = self._memory.search_recent(limit=limit)

        if not results:
            return ToolResult(
                status="no_results",
                message="No recent memories found.",
                success=True,
                content="No recent memories found."
            )

        return ToolResult(
            status="success",
            message=self._format_memory_list(results, f"Recent Memories ({len(results)} memories):"),
            data=self._format_memory_list(results, f"Recent Memories ({len(results)} memories):"),
            success=True,
            content=self._format_memory_list(results, f"Recent Memories ({len(results)} memories):")
        )

    def _search_by_importance(self, kwargs: dict) -> ToolResult:
        """Search memories by minimum importance threshold.
        
        Args:
            kwargs: Parameters including min_importance, limit
            
        Returns:
            ToolResult with high-importance memories
        """
        min_importance = kwargs.get("min_importance", 0.5)
        limit = kwargs.get("limit", 50)

        results = self._memory.search_by_importance(
            min_importance=min_importance,
            limit=limit,
        )

        if not results:
            return ToolResult(
                status="no_results",
                message=f"No memories found with importance >= {min_importance}.",
                success=True,
                content=f"No memories found with importance >= {min_importance}."
            )

        return ToolResult(
            status="success",
            message=self._format_memory_list(results, f"High-Importance Memories (>= {min_importance}, {len(results)} memories):"),
            data=self._format_memory_list(results, f"High-Importance Memories (>= {min_importance}, {len(results)} memories):"),
            success=True,
            content=self._format_memory_list(results, f"High-Importance Memories (>= {min_importance}, {len(results)} memories):")
        )

    def _format_memory(self, memory: dict) -> str:
        """Format a single memory for display.
        
        Args:
            memory: Memory dict from MemoryLite
            
        Returns:
            Formatted string representation
        """
        if not memory:
            return "(empty)"

        lines = [
            f"  ID: {memory.get('memory_id', 'N/A')}",
            f"  Content: {memory.get('content', 'N/A')}",
            f"  Type: {memory.get('type', 'N/A')}",
            f"  Status: {memory.get('status', 'N/A')}",
            f"  Importance: {memory.get('importance', 0):.3f}",
            f"  Update count: {memory.get('update_count', 0)}",
            f"  Created: {memory.get('created_at', 'N/A')}",
            f"  Updated: {memory.get('updated_at', 'N/A')}",
        ]

        expires = memory.get("expires_at")
        if expires:
            lines.append(f"  Expires: {expires}")

        metadata = memory.get("metadata")
        if metadata:
            if isinstance(metadata, dict):
                lines.append(f"  Metadata: {json.dumps(metadata, indent=2)}")
            elif isinstance(metadata, str):
                lines.append(f"  Metadata: {metadata}")

        return "\n".join(lines)

    def _format_memory_list(self, memories: list, header: str = "Memories:") -> str:
        """Format a list of memories for display.
        
        Args:
            memories: List of memory dicts
            header: Header text for the output
            
        Returns:
            Formatted string representation
        """
        lines = [header, ""]
        for i, memory in enumerate(memories, 1):
            lines.append(f"--- Memory #{i} ---")
            lines.append(self._format_memory(memory))
            lines.append("")

        lines.append(f"Total memories: {len(memories)}")
        return "\n".join(lines)