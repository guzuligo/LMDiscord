"""
Logging Utility Module

This module provides a centralized logging system with dual output:
- In-memory log buffer (accessed via Flask API for web UI)
- Optional file logging (app.log in project root)

Key Responsibilities:
- Centralized log management for the web application
- Thread-safe log storage with configurable max size
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Timestamp formatting with timezone awareness
- Module/source tracking
- Real-time log feed for web UI via API endpoint

Usage:
    from src.logger import logger
    logger.info("Connected to LM Studio")
    logger.warning("Discord token not found in .env")
    logger.error("Failed to send message", exc=True)
"""

import os
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pathlib import Path


class LogLevel(Enum):
    """Log level enum with numeric values for filtering."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

    @property
    def color(self) -> str:
        """Return CSS color for this log level."""
        colors = {
            LogLevel.DEBUG: "#6c7086",
            LogLevel.INFO: "#89b4fa",
            LogLevel.WARNING: "#f9e2af",
            LogLevel.ERROR: "#f38ba8",
            LogLevel.CRITICAL: "#fab387",
        }
        return colors.get(self, "#cdd6f4")

    @property
    def icon(self) -> str:
        """Return icon character for this log level."""
        icons = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🔥",
        }
        return icons.get(self, "•")


class LogEntry:
    """Represents a single log entry."""

    def __init__(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        timestamp: Optional[datetime] = None,
    ):
        self.level = level
        self.message = message
        self.module = module
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level.name,
            "level_color": self.level.color,
            "level_icon": self.level.icon,
            "message": self.message,
            "module": self.module,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_formatted": self.timestamp.strftime("%H:%M:%S"),
        }

    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.level.icon} [{self.module or 'App'}] {self.message}"


class Logger:
    """
    Centralized logger with in-memory buffer and optional file output.

    This logger is designed for the web application and provides:
    - In-memory ring buffer of log entries (max 1000 by default)
    - Optional file logging to app.log
    - Thread-safe operations
    - Log level filtering
    - Timestamp and module tracking

    Usage:
        logger = Logger(max_entries=1000, log_to_file=True)
        logger.info("Application started")
        logger.warning("Low memory", module="memory")
        entries = logger.get_logs(level_filter=LogLevel.INFO)
    """

    def __init__(
        self,
        max_entries: int = 1000,
        log_to_file: bool = True,
        log_file: Optional[str] = None,
    ):
        """
        Initialize the logger.

        Args:
            max_entries: Maximum number of log entries to keep in memory
            log_to_file: Whether to also write to a log file
            log_file: Path to the log file (defaults to app.log in project root)
        """
        self.max_entries = max_entries
        self.log_to_file = log_to_file
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()
        self._level_filter = LogLevel.DEBUG  # Accept all levels by default

        # Set up file logging
        if self.log_to_file and log_file is None:
            project_root = Path(__file__).parent.parent
            log_file = str(project_root / "app.log")
        self._log_file = log_file

        if self.log_to_file and self._log_file:
            try:
                # Ensure log directory exists
                log_path = Path(self._log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                # Create or truncate the log file
                with open(self._log_file, "w", encoding="utf-8") as f:
                    f.write(f"--- Log started at {datetime.now(timezone.utc).isoformat()} ---\n")
            except (OSError, PermissionError):
                self.log_to_file = False

    def _add_log(self, entry: LogEntry):
        """
        Add a log entry to the buffer (internal, thread-safe).

        Args:
            entry: LogEntry to add
        """
        with self._lock:
            self._logs.append(entry)
            # Trim oldest entries if over max
            if len(self._logs) > self.max_entries:
                overflow = len(self._logs) - self.max_entries
                self._logs = self._logs[overflow:]

    def _write_to_file(self, entry: LogEntry):
        """
        Write a log entry to the file (internal, thread-safe).

        Args:
            entry: LogEntry to write
        """
        if not self.log_to_file:
            return
        try:
            line = (
                f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
                f" [{entry.level.name}]"
                f" [{entry.module or 'App'}]"
                f" {entry.message}\n"
            )
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except (OSError, PermissionError):
            pass

    def _log(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        exc: bool = False,
    ):
        """
        Core logging method.

        Args:
            level: Log level
            message: Log message
            module: Module name for source tracking
            exc: Whether to include exception info
        """
        if level.value < self._level_filter.value:
            return

        # Extract exception info if requested
        if exc:
            import traceback
            message = f"{message}\n{traceback.format_exc()}"

        entry = LogEntry(
            level=level,
            message=message,
            module=module or self._get_caller_module(),
        )

        self._add_log(entry)
        self._write_to_file(entry)

    def _get_caller_module(self) -> str:
        """
        Extract the calling module name from the call stack.

        Returns:
            Module name string
        """
        import inspect
        frame = inspect.currentframe()
        try:
            # Go up 2 frames: _log -> caller method -> actual caller
            caller_frame = frame.f_back.f_back if frame and frame.f_back else None
            if caller_frame:
                module = inspect.getmodule(caller_frame)
                if module:
                    return module.__name__.split(".")[-1]
            return ""
        finally:
            del frame

    def debug(self, message: str, module: str = ""):
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, module)

    def info(self, message: str, module: str = ""):
        """Log an info message."""
        self._log(LogLevel.INFO, message, module)

    def warning(self, message: str, module: str = ""):
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, module)

    def error(self, message: str, module: str = "", exc: bool = False):
        """Log an error message."""
        self._log(LogLevel.ERROR, message, module, exc=exc)

    def critical(self, message: str, module: str = "", exc: bool = False):
        """Log a critical message."""
        self._log(LogLevel.CRITICAL, message, module, exc=exc)

    def get_logs(
        self,
        limit: int = 100,
        level_filter: Optional[LogLevel] = None,
        module_filter: Optional[str] = None,
    ) -> List[dict]:
        """
        Retrieve log entries with optional filtering.

        Args:
            limit: Maximum number of entries to return
            level_filter: Filter by log level (None = all levels)
            module_filter: Filter by module name (None = all modules)

        Returns:
            List of log entry dictionaries (newest first)
        """
        with self._lock:
            logs = list(self._logs)

        # Apply filters
        if level_filter:
            logs = [l for l in logs if l.level == level_filter]
        if module_filter:
            logs = [l for l in logs if l.module == module_filter]

        # Return newest first, limited
        return [l.to_dict() for l in logs[-limit:]][::-1]

    def clear(self):
        """Clear all log entries."""
        with self._lock:
            self._logs.clear()

    def get_stats(self) -> dict:
        """
        Get log statistics.

        Returns:
            Dictionary with log counts by level and total
        """
        with self._lock:
            stats = {level.name: 0 for level in LogLevel}
            for entry in self._logs:
                stats[entry.level.name] += 1
            stats["total"] = len(self._logs)
            return stats

    def __repr__(self) -> str:
        return f"Logger(entries={len(self._logs)}, filter={self._level_filter.name})"


# Global logger instance
logger = Logger(max_entries=1000, log_to_file=True)