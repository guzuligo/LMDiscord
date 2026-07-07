"""
Cancellation Module

Provides cancellation support for long-running bot operations:
- CancellationEvent: Per-channel cancellation tracking
- CancellationManager: Global manager for all cancellation events
- Cancel commands: /cancel or !stop to abort current processing
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CancellationEvent:
    """Represents a cancellable operation for a channel."""
    
    cancel_requested: asyncio.Event = field(default_factory=asyncio.Event)
    is_cancelled: bool = field(default=False)
    operation_id: Optional[str] = None
    cancel_callback: Optional[Callable] = None
    cancelled_at: Optional[float] = None
    
    def request_cancel(self, reason: str = "User cancelled") -> None:
        """Request cancellation of this operation.
        
        Args:
            reason: Reason for cancellation
        """
        logger.info(f"Cancellation requested for operation {self.operation_id}: {reason}")
        self.is_cancelled = True
        self.cancel_requested.set()
        self.cancelled_at = asyncio.get_event_loop().time()
        
        if self.cancel_callback:
            try:
                result = self.cancel_callback(reason)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Error in cancel callback: {e}")
    
    def is_active(self) -> bool:
        """Check if this operation is currently active (not cancelled)."""
        return not self.is_cancelled
    
    def reset(self) -> None:
        """Reset the cancellation event for a new operation."""
        self.is_cancelled = False
        self.cancel_requested.clear()
        self.cancelled_at = None
        self.operation_id = None


class CancellationManager:
    """Manages cancellation events for all channels."""
    
    def __init__(self):
        """Initialize the cancellation manager."""
        self._events: Dict[int, CancellationEvent] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create_event(self, channel_id: int) -> CancellationEvent:
        """Get existing cancellation event or create a new one for a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            CancellationEvent for the channel
        """
        async with self._lock:
            if channel_id not in self._events:
                self._events[channel_id] = CancellationEvent()
            return self._events[channel_id]
    
    async def request_cancel(self, channel_id: int, reason: str = "User cancelled") -> bool:
        """Request cancellation for a channel's current operation.
        
        Args:
            channel_id: Discord channel ID
            reason: Reason for cancellation
            
        Returns:
            True if cancellation was requested, False if no active operation
        """
        async with self._lock:
            event = self._events.get(channel_id)
            if event is None or event.is_cancelled:
                logger.info(f"No active operation to cancel for channel {channel_id}")
                return False
            
            event.request_cancel(reason)
            logger.info(f"Cancellation requested for channel {channel_id}")
            return True
    
    async def reset_event(self, channel_id: int, operation_id: Optional[str] = None) -> None:
        """Reset cancellation event for a channel (after operation completes).
        
        Args:
            channel_id: Discord channel ID
            operation_id: Optional operation ID to reset
        """
        async with self._lock:
            event = self._events.get(channel_id)
            if event:
                event.reset()
                if operation_id:
                    event.operation_id = operation_id
    
    async def check_and_reset(self, channel_id: int) -> bool:
        """Check if cancellation was requested, then reset the event.
        
        This is a convenience method that checks cancellation status and resets
        the event in a single atomic operation.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if cancellation was requested
        """
        async with self._lock:
            event = self._events.get(channel_id)
            if event is None:
                return False
            
            was_cancelled = event.is_cancelled
            if was_cancelled:
                event.reset()
            return was_cancelled
    
    async def is_cancelled(self, channel_id: int) -> bool:
        """Check if a channel's operation has been cancelled.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if cancelled
        """
        event = self._events.get(channel_id)
        if event is None:
            return False
        return event.is_cancelled
    
    async def check_during_execution(self, channel_id: int) -> bool:
        """Check if cancellation was requested during tool execution.
        
        Unlike check_and_reset(), this does NOT reset the event.
        It's meant to be called repeatedly during long operations
        to check cancellation at multiple checkpoints.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if cancellation was requested (but not yet consumed)
        """
        event = self._events.get(channel_id)
        if event is None:
            return False
        return event.is_cancelled
    
    async def reset_after_execution(self, channel_id: int) -> None:
        """Reset cancellation event after execution completes.
        
        Call this after handling a cancellation to clear the event
        for future operations.
        
        Args:
            channel_id: Discord channel ID
        """
        async with self._lock:
            event = self._events.get(channel_id)
            if event:
                event.reset()
    
    async def get_all_events(self) -> Dict[int, dict]:
        """Get status of all cancellation events.
        
        Returns:
            Dict mapping channel_id to event status dict
        """
        async with self._lock:
            result = {}
            for ch_id, event in self._events.items():
                result[ch_id] = {
                    "is_cancelled": event.is_cancelled,
                    "operation_id": event.operation_id,
                    "cancelled_at": event.cancelled_at
                }
            return result
    
    async def cleanup_inactive(self, active_channels: list) -> None:
        """Remove cancellation events for inactive channels.
        
        Args:
            active_channels: List of currently active channel IDs
        """
        async with self._lock:
            to_remove = [
                ch_id for ch_id in self._events 
                if ch_id not in active_channels
            ]
            for ch_id in to_remove:
                del self._events[ch_id]
                logger.info(f"Cleaned up cancellation event for channel {ch_id}")


# Global singleton instance
_cancel_manager: Optional[CancellationManager] = None


def get_cancellation_manager() -> CancellationManager:
    """Get the global cancellation manager singleton.
    
    Returns:
        CancellationManager instance
    """
    global _cancel_manager
    if _cancel_manager is None:
        _cancel_manager = CancellationManager()
    return _cancel_manager