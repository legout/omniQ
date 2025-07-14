"""
OmniQ Event System

This module provides event logging and processing capabilities for task lifecycle tracking.
Following the "Async First, Sync Wrapped" pattern, all core functionality is implemented
asynchronously with synchronous wrappers using anyio.from_thread.run().
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID

import anyio
import anyio.from_thread

from .models import TaskEvent, EventType
from .storage.base import BaseEventStorage


logger = logging.getLogger(__name__)


class AsyncEventLogger:
    """
    Asynchronous event logger for task lifecycle tracking.
    
    This class provides async methods for logging task events to storage backends.
    It supports disabling event logging for performance-sensitive scenarios.
    """
    
    def __init__(self, event_storage: BaseEventStorage):
        """
        Initialize the async event logger.
        
        Args:
            event_storage: Event storage backend instance
        """
        self._event_storage = event_storage
        self._enabled = True
        self._connected = False
    
    async def connect(self) -> None:
        """Establish connection to the event storage backend."""
        if not self._connected:
            await self._event_storage.connect()
            self._connected = True
    
    async def close(self) -> None:
        """Close the event storage connection."""
        if self._connected:
            await self._event_storage.close()
            self._connected = False
    
    async def __aenter__(self) -> "AsyncEventLogger":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def log(self, event_type: EventType, task_id: UUID, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a task event.
        
        Args:
            event_type: Type of event to log
            task_id: ID of the task this event relates to
            details: Additional event details and metadata
        """
        if not self._enabled:
            return
        
        if not self._connected:
            await self.connect()
        
        # Extract common details
        details = details or {}
        message = details.get("message", "")
        data = details.get("data", {})
        worker_id = details.get("worker_id")
        queue = details.get("queue", "default")
        metadata = details.get("metadata", {})
        
        # Create the event
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            data=data,
            worker_id=worker_id,
            queue=queue,
            metadata=metadata
        )
        
        try:
            await self._event_storage.log_event(event)
            logger.debug(f"Logged event {event_type.value} for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to log event {event_type.value} for task {task_id}: {e}")
            # Don't raise exception to avoid breaking task processing
    
    async def log_enqueued(self, task_id: UUID, queue: str = "default", **kwargs) -> None:
        """Log an ENQUEUED event."""
        details = {
            "message": f"Task enqueued in queue '{queue}'",
            "queue": queue,
            **kwargs
        }
        await self.log(EventType.ENQUEUED, task_id, details)
    
    async def log_dequeued(self, task_id: UUID, worker_id: str, queue: str = "default", **kwargs) -> None:
        """Log a DEQUEUED event."""
        details = {
            "message": f"Task dequeued by worker '{worker_id}' from queue '{queue}'",
            "worker_id": worker_id,
            "queue": queue,
            **kwargs
        }
        await self.log(EventType.DEQUEUED, task_id, details)
    
    async def log_executing(self, task_id: UUID, worker_id: str, **kwargs) -> None:
        """Log an EXECUTING event."""
        details = {
            "message": f"Task execution started by worker '{worker_id}'",
            "worker_id": worker_id,
            **kwargs
        }
        await self.log(EventType.EXECUTING, task_id, details)
    
    async def log_complete(self, task_id: UUID, worker_id: str, execution_time: float, **kwargs) -> None:
        """Log a COMPLETE event."""
        details = {
            "message": f"Task completed successfully by worker '{worker_id}' in {execution_time:.2f}s",
            "worker_id": worker_id,
            "data": {"execution_time": execution_time},
            **kwargs
        }
        await self.log(EventType.COMPLETE, task_id, details)
    
    async def log_error(self, task_id: UUID, worker_id: str, error: str, **kwargs) -> None:
        """Log an ERROR event."""
        details = {
            "message": f"Task failed with error: {error}",
            "worker_id": worker_id,
            "data": {"error": error},
            **kwargs
        }
        await self.log(EventType.ERROR, task_id, details)
    
    async def log_retry(self, task_id: UUID, retry_count: int, **kwargs) -> None:
        """Log a RETRY event."""
        details = {
            "message": f"Task scheduled for retry #{retry_count}",
            "data": {"retry_count": retry_count},
            **kwargs
        }
        await self.log(EventType.RETRY, task_id, details)
    
    async def log_cancelled(self, task_id: UUID, reason: str = "User requested", **kwargs) -> None:
        """Log a CANCELLED event."""
        details = {
            "message": f"Task cancelled: {reason}",
            "data": {"reason": reason},
            **kwargs
        }
        await self.log(EventType.CANCELLED, task_id, details)
    
    async def log_expired(self, task_id: UUID, ttl: int, **kwargs) -> None:
        """Log an EXPIRED event."""
        details = {
            "message": f"Task expired after {ttl} seconds",
            "data": {"ttl": ttl},
            **kwargs
        }
        await self.log(EventType.EXPIRED, task_id, details)
    
    def disable(self) -> None:
        """Disable event logging for performance-sensitive scenarios."""
        self._enabled = False
        logger.info("Event logging disabled")
    
    def enable(self) -> None:
        """Re-enable event logging."""
        self._enabled = True
        logger.info("Event logging enabled")
    
    @property
    def enabled(self) -> bool:
        """Check if event logging is enabled."""
        return self._enabled


class EventLogger:
    """
    Synchronous wrapper for AsyncEventLogger.
    
    Provides synchronous methods for logging task events using anyio.from_thread.run()
    to call the async methods.
    """
    
    def __init__(self, event_storage: BaseEventStorage):
        """
        Initialize the sync event logger.
        
        Args:
            event_storage: Event storage backend instance
        """
        self._async_logger = AsyncEventLogger(event_storage)
    
    def connect(self) -> None:
        """Establish connection to the event storage backend."""
        return anyio.from_thread.run(self._async_logger.connect)
    
    def close(self) -> None:
        """Close the event storage connection."""
        return anyio.from_thread.run(self._async_logger.close)
    
    def __enter__(self) -> "EventLogger":
        """Sync context manager entry."""
        anyio.from_thread.run(self._async_logger.connect)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        anyio.from_thread.run(self._async_logger.close)
    
    def log(self, event_type: EventType, task_id: UUID, details: Optional[Dict[str, Any]] = None) -> None:
        """Synchronous wrapper for log."""
        return anyio.from_thread.run(self._async_logger.log, event_type, task_id, details)
    
    def log_enqueued(self, task_id: UUID, queue: str = "default", **kwargs) -> None:
        """Synchronous wrapper for log_enqueued."""
        return anyio.from_thread.run(self._async_logger.log_enqueued, task_id, queue, **kwargs)
    
    def log_dequeued(self, task_id: UUID, worker_id: str, queue: str = "default", **kwargs) -> None:
        """Synchronous wrapper for log_dequeued."""
        return anyio.from_thread.run(self._async_logger.log_dequeued, task_id, worker_id, queue, **kwargs)
    
    def log_executing(self, task_id: UUID, worker_id: str, **kwargs) -> None:
        """Synchronous wrapper for log_executing."""
        return anyio.from_thread.run(self._async_logger.log_executing, task_id, worker_id, **kwargs)
    
    def log_complete(self, task_id: UUID, worker_id: str, execution_time: float, **kwargs) -> None:
        """Synchronous wrapper for log_complete."""
        return anyio.from_thread.run(self._async_logger.log_complete, task_id, worker_id, execution_time, **kwargs)
    
    def log_error(self, task_id: UUID, worker_id: str, error: str, **kwargs) -> None:
        """Synchronous wrapper for log_error."""
        return anyio.from_thread.run(self._async_logger.log_error, task_id, worker_id, error, **kwargs)
    
    def log_retry(self, task_id: UUID, retry_count: int, **kwargs) -> None:
        """Synchronous wrapper for log_retry."""
        return anyio.from_thread.run(self._async_logger.log_retry, task_id, retry_count, **kwargs)
    
    def log_cancelled(self, task_id: UUID, reason: str = "User requested", **kwargs) -> None:
        """Synchronous wrapper for log_cancelled."""
        return anyio.from_thread.run(self._async_logger.log_cancelled, task_id, reason, **kwargs)
    
    def log_expired(self, task_id: UUID, ttl: int, **kwargs) -> None:
        """Synchronous wrapper for log_expired."""
        return anyio.from_thread.run(self._async_logger.log_expired, task_id, ttl, **kwargs)
    
    def disable(self) -> None:
        """Disable event logging for performance-sensitive scenarios."""
        self._async_logger.disable()
    
    def enable(self) -> None:
        """Re-enable event logging."""
        self._async_logger.enable()
    
    @property
    def enabled(self) -> bool:
        """Check if event logging is enabled."""
        return self._async_logger.enabled


class AsyncEventProcessor:
    """
    Asynchronous event processor for handling and reacting to task events.
    
    This class provides async methods for processing events, including background
    processing loops and event handling mechanisms.
    """
    
    def __init__(self, event_storage: BaseEventStorage, process_interval: float = 1.0):
        """
        Initialize the async event processor.
        
        Args:
            event_storage: Event storage backend instance
            process_interval: Interval in seconds between processing loops
        """
        self._event_storage = event_storage
        self._process_interval = process_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._connected = False
        self._event_handlers: Dict[EventType, list] = {}
    
    async def connect(self) -> None:
        """Establish connection to the event storage backend."""
        if not self._connected:
            await self._event_storage.connect()
            self._connected = True
    
    async def close(self) -> None:
        """Close the event storage connection."""
        if self._connected:
            await self._event_storage.close()
            self._connected = False
    
    async def __aenter__(self) -> "AsyncEventProcessor":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
        await self.close()
    
    def add_event_handler(self, event_type: EventType, handler) -> None:
        """
        Add an event handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Async callable that takes a TaskEvent parameter
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: EventType, handler) -> None:
        """
        Remove an event handler for a specific event type.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found
    
    async def process_event(self, event: TaskEvent) -> None:
        """
        Process a single event by calling registered handlers.
        
        Args:
            event: The task event to process
        """
        try:
            # Call all handlers for this event type
            handlers = self._event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed for event {event.id}: {e}")
            
            logger.debug(f"Processed event {event.event_type.value} for task {event.task_id}")
        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
    
    async def _processing_loop(self) -> None:
        """Background processing loop for handling events."""
        while self._running:
            try:
                # This is a simplified processing loop
                # In a real implementation, you might want to:
                # 1. Poll for new events from storage
                # 2. Process them in batches
                # 3. Handle event-driven reactions
                
                # For now, we just sleep and continue
                await asyncio.sleep(self._process_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(self._process_interval)
    
    async def start(self) -> None:
        """Start the background event processing loop."""
        if self._running:
            return
        
        if not self._connected:
            await self.connect()
        
        self._running = True
        self._task = asyncio.create_task(self._processing_loop())
        logger.info("Event processor started")
    
    async def stop(self) -> None:
        """Stop the background event processing loop."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Event processor stopped")
    
    @property
    def running(self) -> bool:
        """Check if the processor is running."""
        return self._running


class EventProcessor:
    """
    Synchronous wrapper for AsyncEventProcessor.
    
    Provides synchronous methods for event processing using anyio.from_thread.run()
    to call the async methods.
    """
    
    def __init__(self, event_storage: BaseEventStorage, process_interval: float = 1.0):
        """
        Initialize the sync event processor.
        
        Args:
            event_storage: Event storage backend instance
            process_interval: Interval in seconds between processing loops
        """
        self._async_processor = AsyncEventProcessor(event_storage, process_interval)
    
    def connect(self) -> None:
        """Establish connection to the event storage backend."""
        return anyio.from_thread.run(self._async_processor.connect)
    
    def close(self) -> None:
        """Close the event storage connection."""
        return anyio.from_thread.run(self._async_processor.close)
    
    def __enter__(self) -> "EventProcessor":
        """Sync context manager entry."""
        anyio.from_thread.run(self._async_processor.connect)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        anyio.from_thread.run(self._async_processor.stop)
        anyio.from_thread.run(self._async_processor.close)
    
    def add_event_handler(self, event_type: EventType, handler) -> None:
        """Add an event handler for a specific event type."""
        self._async_processor.add_event_handler(event_type, handler)
    
    def remove_event_handler(self, event_type: EventType, handler) -> None:
        """Remove an event handler for a specific event type."""
        self._async_processor.remove_event_handler(event_type, handler)
    
    def process_event(self, event: TaskEvent) -> None:
        """Synchronous wrapper for process_event."""
        return anyio.from_thread.run(self._async_processor.process_event, event)
    
    def start(self) -> None:
        """Synchronous wrapper for start."""
        return anyio.from_thread.run(self._async_processor.start)
    
    def stop(self) -> None:
        """Synchronous wrapper for stop."""
        return anyio.from_thread.run(self._async_processor.stop)
    
    @property
    def running(self) -> bool:
        """Check if the processor is running."""
        return self._async_processor.running