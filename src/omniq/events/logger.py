"""AsyncEventLogger and EventLogger for task lifecycle event logging."""

from __future__ import annotations

import asyncio
import time
from typing import List, Optional

import anyio

from ..config.loader import LoggingConfig
from ..models.event import TaskEvent, TaskEventType
from ..storage.base import BaseEventStorage


class AsyncEventLogger:
    """Async event logger for task lifecycle events."""
    
    def __init__(
        self,
        storage: BaseEventStorage,
        enabled: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_buffer_size: int = 10000
    ):
        """
        Initialize async event logger.
        
        Args:
            storage: Event storage backend
            enabled: Whether event logging is enabled
            batch_size: Number of events to batch before flushing
            flush_interval: Maximum time between flushes in seconds
            max_buffer_size: Maximum events in buffer before forced flush
        """
        self.storage = storage
        self.enabled = enabled
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        
        self._buffer: List[TaskEvent] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._logger = LoggingConfig.get_logger("events.logger")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self) -> None:
        """Start the event logger and background flush task."""
        if not self.enabled:
            return
        
        self._stop_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._logger.debug("Event logger started")
    
    async def stop(self) -> None:
        """Stop the event logger and flush remaining events."""
        if not self.enabled:
            return
        
        self._stop_event.set()
        
        if self._flush_task:
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush any remaining events
        await self._flush_events()
        self._logger.debug("Event logger stopped")
    
    async def log_event(self, event: TaskEvent) -> None:
        """Log a single event."""
        if not self.enabled:
            return
        
        async with self._lock:
            self._buffer.append(event)
            
            # Force flush if buffer is getting too large
            if len(self._buffer) >= self.max_buffer_size:
                await self._flush_events()
            elif len(self._buffer) >= self.batch_size:
                # Schedule immediate flush for batch size
                asyncio.create_task(self._flush_events())
    
    async def log_task_enqueued(
        self,
        task_id: str,
        queue_name: str,
        priority: int = 0,
        **kwargs
    ) -> None:
        """Log task enqueued event."""
        event = TaskEvent.enqueued(task_id, queue_name, priority, **kwargs)
        await self.log_event(event)
    
    async def log_task_started(
        self,
        task_id: str,
        worker_id: str,
        worker_type: str,
        **kwargs
    ) -> None:
        """Log task started event."""
        event = TaskEvent.started(task_id, worker_id, worker_type, **kwargs)
        await self.log_event(event)
    
    async def log_task_completed(
        self,
        task_id: str,
        worker_id: str,
        duration_ms: float,
        **kwargs
    ) -> None:
        """Log task completed event."""
        event = TaskEvent.completed(task_id, worker_id, duration_ms, **kwargs)
        await self.log_event(event)
    
    async def log_task_failed(
        self,
        task_id: str,
        worker_id: str,
        error: Exception,
        duration_ms: float,
        retry_count: int = 0,
        **kwargs
    ) -> None:
        """Log task failed event."""
        event = TaskEvent.failed(task_id, worker_id, error, duration_ms, retry_count, **kwargs)
        await self.log_event(event)
    
    async def log_retry_scheduled(
        self,
        task_id: str,
        retry_count: int,
        retry_delay: float,
        **kwargs
    ) -> None:
        """Log retry scheduled event."""
        event = TaskEvent.retry_scheduled(task_id, retry_count, retry_delay, **kwargs)
        await self.log_event(event)
    
    async def log_dependency_event(
        self,
        task_id: str,
        event_type: TaskEventType,
        dependency_task_id: str,
        **kwargs
    ) -> None:
        """Log dependency-related event."""
        event = TaskEvent.dependency_event(task_id, event_type, dependency_task_id, **kwargs)
        await self.log_event(event)
    
    async def log_schedule_event(
        self,
        task_id: str,
        event_type: TaskEventType,
        schedule_name: str,
        next_run: Optional[float] = None,
        **kwargs
    ) -> None:
        """Log schedule-related event."""
        event = TaskEvent.schedule_event(task_id, event_type, schedule_name, next_run, **kwargs)
        await self.log_event(event)
    
    async def log_custom_event(
        self,
        task_id: str,
        event_type: TaskEventType,
        message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log custom event."""
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            **kwargs
        )
        await self.log_event(event)
    
    async def _flush_loop(self) -> None:
        """Background task to periodically flush events."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.flush_interval
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                # Timeout reached, flush events
                await self._flush_events()
    
    async def _flush_events(self) -> None:
        """Flush buffered events to storage."""
        async with self._lock:
            if not self._buffer:
                return
            
            events_to_flush = self._buffer.copy()
            self._buffer.clear()
        
        try:
            # Store events in batch
            for event in events_to_flush:
                await self.storage.store_event(event)
            
            self._logger.debug(f"Flushed {len(events_to_flush)} events")
        except Exception as e:
            self._logger.error(f"Failed to flush events: {e}")
            # Re-add events to buffer for retry
            async with self._lock:
                self._buffer.extend(events_to_flush)
    
    def get_buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)


class EventLogger:
    """Synchronous wrapper for AsyncEventLogger."""
    
    def __init__(self, async_logger: AsyncEventLogger):
        """Initialize sync wrapper."""
        self._async_logger = async_logger
    
    def __enter__(self):
        """Sync context manager entry."""
        anyio.from_thread.run(self._async_logger.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        anyio.from_thread.run(self._async_logger.__aexit__, exc_type, exc_val, exc_tb)
    
    def log_event(self, event: TaskEvent) -> None:
        """Log a single event."""
        anyio.from_thread.run(self._async_logger.log_event, event)
    
    def log_task_enqueued(
        self,
        task_id: str,
        queue_name: str,
        priority: int = 0,
        **kwargs
    ) -> None:
        """Log task enqueued event."""
        anyio.from_thread.run(
            self._async_logger.log_task_enqueued,
            task_id, queue_name, priority, **kwargs
        )
    
    def log_task_started(
        self,
        task_id: str,
        worker_id: str,
        worker_type: str,
        **kwargs
    ) -> None:
        """Log task started event."""
        anyio.from_thread.run(
            self._async_logger.log_task_started,
            task_id, worker_id, worker_type, **kwargs
        )
    
    def log_task_completed(
        self,
        task_id: str,
        worker_id: str,
        duration_ms: float,
        **kwargs
    ) -> None:
        """Log task completed event."""
        anyio.from_thread.run(
            self._async_logger.log_task_completed,
            task_id, worker_id, duration_ms, **kwargs
        )
    
    def log_task_failed(
        self,
        task_id: str,
        worker_id: str,
        error: Exception,
        duration_ms: float,
        retry_count: int = 0,
        **kwargs
    ) -> None:
        """Log task failed event."""
        anyio.from_thread.run(
            self._async_logger.log_task_failed,
            task_id, worker_id, error, duration_ms, retry_count, **kwargs
        )
    
    def log_custom_event(
        self,
        task_id: str,
        event_type: TaskEventType,
        message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log custom event."""
        anyio.from_thread.run(
            self._async_logger.log_custom_event,
            task_id, event_type, message, **kwargs
        )