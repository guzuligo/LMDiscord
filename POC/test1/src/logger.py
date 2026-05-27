"""
Logging Utility Module

This module provides a centralized logging system with triple output:
- In-memory log buffer (accessed via Flask API for web UI)
- Optional file logging (app.log in project root)
- Terminal log file (terminal.log in project root) - mirrors terminal print output EXACTLY
- Bridge from Python's standard logging module (LoggingHandler)

Key Responsibilities:
- Centralized log management for the web application
- Thread-safe log storage with configurable max size
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Timestamp formatting with timezone awareness
- Module/source tracking
- Real-time log feed for web UI via API endpoint
- Module-level filtering for user-facing logs (suppress noisy modules)
- terminal.log file for debugging - auto-cleared on app startup, mirrors stdout exactly

Usage:
    from src.logger import logger, logging_handler, enable_terminal_log
    logger.info("Connected to LM Studio")
    logger.warning("Discord token not found in .env")
    logger.error("Failed to send message", exc=True)
"""

import logging
import os
import sys
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
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


class _TeeStream:
    """
    A file-like stream that writes to both the original stream and a log file.
    
    This ensures that every print() statement and every logging output goes to both
    the terminal and the terminal.log file, making them identical.
    """
    
    def __init__(self, logfile_path: str, original_stream, header_line: str, truncate: bool = True):
        """
        Initialize the tee stream.
        
        Args:
            logfile_path: Path to the log file
            original_stream: The original sys.stdout or sys.stderr
            header_line: Initial header line to write to the log file (only if truncate=True)
            truncate: If True, truncate the file and write header. If False, append to existing file.
        """
        self._logfile_path = logfile_path
        self._original_stream = original_stream
        self._file = None
        try:
            log_dir = Path(logfile_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            mode = "w" if truncate else "a"
            with open(logfile_path, mode, encoding="utf-8") as f:
                if truncate:
                    f.write(header_line + "\n")
            # Open in append mode for continuous writing
            self._file = open(logfile_path, "a", encoding="utf-8")
        except (OSError, PermissionError):
            self._file = None
        
    def write(self, text: str):
        """Write to both the log file and original stream."""
        # Write to log file
        if self._file:
            try:
                self._file.write(text)
                self._file.flush()
            except (OSError, ValueError):
                pass
        # Write to original stream
        try:
            self._original_stream.write(text)
            self._original_stream.flush()
        except Exception:
            pass
    
    def flush(self):
        """Flush both streams."""
        if self._file:
            try:
                self._file.flush()
            except (OSError, ValueError):
                pass
        try:
            self._original_stream.flush()
        except Exception:
            pass
    
    def isatty(self) -> bool:
        """Delegate isatty to original stream."""
        try:
            return self._original_stream.isatty()
        except (AttributeError, OSError):
            return False


# Default module-level log filter configuration.
# Maps module name prefixes to minimum log level for user-facing logs.
# Modules not listed default to INFO level.
# Set to WARNING to suppress noisy modules from user-facing display.
DEFAULT_MODULE_FILTER: Dict[str, str] = {
    # Suppress typing indicator noise in user-facing logs
    "src.discord_bot.typing_indicator": "WARNING",
    # Suppress token tracker noise in user-facing logs
    "src.discord_bot.token_tracker": "WARNING",
    # Suppress channel filter debug traces (already visible in terminal)
    "src.discord_bot.bot_core": "INFO",
}


class LoggingHandler(logging.Handler):
    """
    A logging.Handler that bridges Python's standard logging module
    into our custom Logger in-memory buffer.

    Applies module-level filtering for user-facing logs:
    - Noisy modules (typing_indicator, token_tracker) default to WARNING+
    - All other modules default to INFO+
    - Debug page shows all logs (no filtering applied there)

    Usage:
        handler = LoggingHandler(logger_instance)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, logger_instance: "Logger", module_filter: Optional[Dict[str, str]] = None):
        """
        Initialize the logging handler.

        The LoggingHandler bridges Python's standard logging into the custom Logger's
        in-memory buffer. Terminal output is handled separately by logging.basicConfig()
        in setup_logging().

        Args:
            logger_instance: The Logger instance to add entries to
            module_filter: Dict mapping module prefixes to minimum log level strings
        """
        super().__init__()
        self._logger = logger_instance
        self._module_filter = module_filter or DEFAULT_MODULE_FILTER

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record from Python's logging system.

        This method is called by Python's logging system for each log record.
        The handler applies module-level filtering before adding to the buffer.
        Terminal output is handled by logging.basicConfig() in setup_logging().

        Args:
            record: The log record to convert
        """
        try:
            # Map Python logging level to our LogLevel
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL,
            }

            our_level = level_map.get(record.levelno, LogLevel.INFO)

            # Apply module-level filtering (same as Logger._log)
            effective_level = _get_effective_level_for_module(record.name, self._module_filter)
            if our_level.value < effective_level.value:
                return  # Module is suppressed at this level

            # Convert to our LogEntry format
            entry = LogEntry(
                level=our_level,
                message=self.format(record) if self.formatter else record.getMessage(),
                module=record.name,
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc),
            )

            # Add to in-memory buffer (terminal output is handled by basicConfig)
            self._logger._add_log(entry)

        except Exception:
            # Don't break the logging system if our handler fails
            pass


def _is_module_suppressed(module_name: str, module_filter: Optional[Dict[str, str]] = None) -> bool:
    """
    Check if a module is suppressed (should not appear in terminal or main web UI).
    
    Args:
        module_name: Full dotted module name
        module_filter: Dict mapping module prefixes to minimum log level strings
        
    Returns:
        True if the module is suppressed (below its minimum level threshold)
    """
    if module_filter is None:
        module_filter = DEFAULT_MODULE_FILTER
    
    for prefix, level_str in module_filter.items():
        if module_name.startswith(prefix):
            try:
                threshold_level = LogLevel[level_str.upper()]
                return True  # Module is in the filter — it's suppressed from default display
            except KeyError:
                pass
    return False  # Module not in filter — not suppressed


def _get_effective_level_for_module(module_name: str, module_filter: Optional[Dict[str, str]] = None) -> LogLevel:
    """
    Get the effective minimum log level for a module.
    
    Args:
        module_name: Full dotted module name
        module_filter: Dict mapping module prefixes to minimum log level strings
        
    Returns:
        Minimum LogLevel for this module
    """
    if module_filter is None:
        module_filter = DEFAULT_MODULE_FILTER
    
    for prefix, level_str in module_filter.items():
        if module_name.startswith(prefix):
            try:
                return LogLevel[level_str.upper()]
            except KeyError:
                pass
    return LogLevel.INFO  # Default for unlisted modules


class Logger:
    """
    Centralized logger with in-memory buffer and optional file output.

    This logger is designed for the web application and provides:
    - In-memory ring buffer of log entries (max 1000 by default)
    - Optional file logging to app.log
    - Optional terminal log file (terminal.log) - mirrors print output for debugging
    - Thread-safe operations
    - Log level filtering
    - Timestamp and module tracking
    - Integration with Python's standard logging via LoggingHandler
    - Terminal output via print() — guaranteed for non-suppressed logs

    Logging priority:
    1. Check level filter — if below, silently skip
    2. Check module suppression — if suppressed, silently skip
    3. Print to terminal (stdout) — guaranteed, no GUI code
    4. Add to in-memory buffer
    5. Write to app.log file

    terminal.log:
    - Contains the EXACT same output as printed to terminal (via stdout redirection)
    - Auto-cleared (truncated) whenever the application starts
    - Useful for sharing logs when asking for help debugging
    - Located in the project root directory
    - Git-ignored via .gitignore

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
        module_filter: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the logger.

        Args:
            max_entries: Maximum number of log entries to keep in memory
            log_to_file: Whether to also write to a log file
            log_file: Path to the log file (defaults to app.log in project root)
            module_filter: Dict mapping module prefixes to minimum log level strings
        """
        self.max_entries = max_entries
        self.log_to_file = log_to_file
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()
        self._level_filter = LogLevel.DEBUG  # Accept all levels by default
        self._module_filter = module_filter or DEFAULT_MODULE_FILTER

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

        Logging priority:
        1. Check level filter — if below, silently skip
        2. Check module suppression — if suppressed, silently skip
        3. Print to terminal (stdout) — guaranteed, no GUI code
        4. Add to in-memory buffer
        5. Write to app.log file

        Args:
            level: Log level
            message: Log message
            module: Module name for source tracking
            exc: Whether to include exception info
        """
        # Step 1: Check level filter FIRST
        if level.value < self._level_filter.value:
            return

        # Step 2: Check module suppression
        resolved_module = module or self._get_caller_module()
        effective_level = _get_effective_level_for_module(resolved_module, self._module_filter)
        if level.value < effective_level.value:
            return  # Module is suppressed at this level

        # Extract exception info if requested
        if exc:
            import traceback
            message = f"{message}\n{traceback.format_exc()}"

        entry = LogEntry(
            level=level,
            message=message,
            module=resolved_module,
        )

        # Step 3: Print to terminal FIRST (before any GUI code)
        # This goes through sys.stdout which may be redirected to _TeeStream
        print(f"[{entry.timestamp.strftime('%H:%M:%S')}] {level.icon} [{resolved_module or 'App'}] {message}")

        # Step 4: Add to in-memory buffer
        self._add_log(entry)

        # Step 5: Write to file
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
        module_name_filter: Optional[str] = None,
    ) -> List[dict]:
        """
        Retrieve log entries with optional filtering.

        Args:
            limit: Maximum number of entries to return
            level_filter: Filter by log level (None = all levels)
            module_name_filter: Filter by module name (None = all modules)

        Returns:
            List of log entry dictionaries (newest first)
        """
        with self._lock:
            logs = list(self._logs)

        # Apply filters
        if level_filter:
            logs = [l for l in logs if l.level == level_filter]
        if module_name_filter:
            logs = [l for l in logs if l.module == module_name_filter]

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

# Global logging handler that bridges Python's standard logging → custom Logger
# This is initialized lazily when registered with the root logger
_logging_handler: Optional[LoggingHandler] = None

# Terminal log redirect state
_terminal_stdout_redirect: Optional[_TeeStream] = None
_terminal_stderr_redirect: Optional[_TeeStream] = None


def enable_terminal_log(logfile_path: Optional[str] = None) -> bool:
    """
    Enable terminal log redirection for both stdout and stderr.
    
    Redirects sys.stdout and sys.stderr so that ALL terminal output goes to both
    the terminal and the terminal.log file. This ensures terminal.log contains
    exactly what you see in the terminal.
    
    - print() writes to stdout → redirected to terminal.log
    - logging.info/error/debug() writes to stderr → redirected to terminal.log
    - Any other output to sys.stderr → redirected to terminal.log
    
    The terminal.log file is truncated (cleared) when this function is called,
    which happens automatically on application startup.

    Args:
        logfile_path: Path to the log file (defaults to terminal.log in project root)
    
    Returns:
        True if redirection was enabled successfully, False otherwise
    """
    global _terminal_stdout_redirect, _terminal_stderr_redirect
    
    if _terminal_stdout_redirect is not None:
        return True  # Already enabled
    
    if logfile_path is None:
        project_root = Path(__file__).parent.parent
        logfile_path = str(project_root / "terminal.log")
    
    try:
        header_line = f"--- Terminal log started at {datetime.now(timezone.utc).isoformat()} ---"
        
        # Redirect stdout (print statements) - truncates file and writes header
        original_stdout = sys.stdout
        _terminal_stdout_redirect = _TeeStream(logfile_path, original_stdout, header_line, truncate=True)
        sys.stdout = _terminal_stdout_redirect
        
        # Redirect stderr (logging module, print(file=sys.stderr), etc.) - appends to same file
        original_stderr = sys.stderr
        _terminal_stderr_redirect = _TeeStream(logfile_path, original_stderr, header_line, truncate=False)
        sys.stderr = _terminal_stderr_redirect
        
        return True
    except Exception:
        return False


def get_logging_handler() -> LoggingHandler:
    """
    Get or create the global LoggingHandler instance.

    Returns:
        LoggingHandler instance ready to be added to the root logger
    """
    global _logging_handler
    if _logging_handler is None:
        _logging_handler = LoggingHandler(logger, DEFAULT_MODULE_FILTER)
    return _logging_handler


def setup_logging(module_filter: Optional[Dict[str, str]] = None) -> LoggingHandler:
    """
    Set up the bridge from Python's standard logging to our custom Logger.

    This function configures:
    1. Python's standard logging with logging.basicConfig() — terminal output for ALL logs
    2. LoggingHandler added to root logger — bridges to custom Logger's in-memory buffer
    3. Terminal log redirection — enables terminal.log mirroring of stdout

    Terminal output:
    - logging.basicConfig(level=logging.DEBUG) ensures ALL logs go to terminal
    - No filtering at terminal level — user sees everything in the console
    - sys.stdout is redirected to _TeeStream so terminal.log mirrors stdout exactly

    Web UI buffer output:
    - LoggingHandler applies module-level filtering
    - Suppressed modules (typing_indicator, token_tracker) only show at WARNING+
    - Debug page can still see all logs via raw buffer access

    Call this function in app.py during startup to ensure all Python logging
    entries appear in the web UI's log buffer and terminal.log is created.

    Args:
        module_filter: Optional custom module filter dict (uses DEFAULT_MODULE_FILTER if None)

    Returns:
        The configured LoggingHandler instance
    """
    # Enable terminal log redirection (stdout → terminal.log + terminal)
    enable_terminal_log()
    
    # Configure Python's standard logging for terminal output (ALL logs, no filtering)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        stream=sys.stderr,
    )
    
    handler = LoggingHandler(logger, module_filter or DEFAULT_MODULE_FILTER)
    # Add to root logger so ALL Python logging is captured in the buffer
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    # Store globally for subsequent calls
    global _logging_handler
    _logging_handler = handler
    return handler