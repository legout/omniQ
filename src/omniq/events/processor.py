"""AsyncEventProcessor and EventProcessor for real-time event processing."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

import anyio

from ..config.loader import LoggingConfig
from ..models.event import TaskEvent, TaskEventType
from ..storage.base import BaseEventStorage


EventHandler = Callable[[TaskEvent], None]
AsyncEventHandler = Callable[[TaskEvent], None]


class AsyncEventProcessor:
    """Async event processor for real-time event handling and monitoring."""
    
    def __init__(
        self,
        storage: BaseEventStorage,
        enabled: bool = True,
        poll_interval: float = 1.0
    ):
        """
        Initialize async event processor.
        
        Args:
            storage: Event storage backend for streaming events
            enabled: Whether event processing is enabled
            poll_interval: Polling interval for event streaming
        """
        self.storage = storage
        self.enabled = enabled
        self.poll_interval = poll_interval
        
        self._handlers: Dict[TaskEventType, List[AsyncEventHandler]] = {}
        self._global_handlers: List[AsyncEventHandler] = []
        self._processing_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._logger = LoggingConfig.get_logger("events.processor")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self) -> None:
        """Start the event processor."""
        if not self.enabled:
            return
        
        self._stop_event.clear()
        self._processing_task = asyncio.create_task(self._process_events())
        self._logger.debug("Event processor started")
    
    async def stop(self) -> None:
        """Stop the event processor."""
        if not self.enabled:
            return
        
        self._stop_event.set()
        
        if self._processing_task:
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self._logger.debug("Event processor stopped")
    
    def add_handler(
        self,
        event_type: TaskEventType,
        handler: AsyncEventHandler
    ) -> None:
        """Add an event handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        self._logger.debug(f"Added handler for {event_type}")
    
    def add_global_handler(self, handler: AsyncEventHandler) -> None:
        """Add a global event handler that receives all events."""
        self._global_handlers.append(handler)
        self._logger.debug("Added global event handler")
    
    def remove_handler(
        self,
        event_type: TaskEventType,
        handler: AsyncEventHandler
    ) -> bool:
        """Remove a specific event handler."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
                self._logger.debug(f"Removed handler for {event_type}")
                return True
            except ValueError:
                pass
        return False
    
    def remove_global_handler(self, handler: AsyncEventHandler) -> bool:
        """Remove a global event handler."""
        try:
            self._global_handlers.remove(handler)
            self._logger.debug("Removed global event handler")
            return True
        except ValueError:
            return False
    
    def clear_handlers(self, event_type: Optional[TaskEventType] = None) -> None:
        """Clear handlers for a specific event type or all handlers."""
        if event_type is None:
            self._handlers.clear()
            self._global_handlers.clear()
            self._logger.debug("Cleared all event handlers")
        elif event_type in self._handlers:
            del self._handlers[event_type]
            self._logger.debug(f"Cleared handlers for {event_type}")
    
    async def process_event(self, event: TaskEvent) -> None:
        """Process a single event through all relevant handlers."""
        if not self.enabled:
            return
        
        handlers_to_call = []
        
        # Add specific handlers for this event type
        if event.event_type in self._handlers:
            handlers_to_call.extend(self._handlers[event.event_type])
        
        # Add global handlers
        handlers_to_call.extend(self._global_handlers)
        
        # Call all handlers
        for handler in handlers_to_call:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self._logger.error(f"Error in event handler: {e}")
    
    async def process_events_batch(self, events: List[TaskEvent]) -> None:
        """Process a batch of events."""
        for event in events:
            await self.process_event(event)
    
    async def get_recent_events(
        self,
        task_id: Optional[str] = None,
        event_types: Optional[List[TaskEventType]] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get recent events from storage."""
        filters = {}
        
        if task_id:
            filters["task_id"] = task_id
        
        if event_types:
            filters["event_type"] = [et.value for et in event_types]
        
        return await self.storage.list_events(limit=limit, filters=filters)
    
    async def monitor_task(
        self,
        task_id: str,
        handler: AsyncEventHandler,
        event_types: Optional[List[TaskEventType]] = None
    ) -> None:
        """Monitor events for a specific task."""
        async def task_handler(event: TaskEvent) -> None:
            if event.task_id == task_id:
                if event_types is None or event.event_type in event_types:
                    await handler(event)
        
        self.add_global_handler(task_handler)
    
    async def wait_for_event(
        self,
        task_id: str,
        event_type: TaskEventType,
        timeout: Optional[float] = None
    ) -> Optional[TaskEvent]:
        """Wait for a specific event to occur."""
        event_received = asyncio.Event()
        received_event = None
        
        async def wait_handler(event: TaskEvent) -> None:
            nonlocal received_event
            if event.task_id == task_id and event.event_type == event_type:
                received_event = event
                event_received.set()
        
        self.add_global_handler(wait_handler)
        
        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return received_event
        except asyncio.TimeoutError:
            return None
        finally:
            self.remove_global_handler(wait_handler)
    
    async def _process_events(self) -> None:
        """Background task to process events from storage stream."""
        while not self._stop_event.is_set():
            try:
                # Stream events from storage
                async for event in self.storage.stream_events():
                    if self._stop_event.is_set():
                        break
                    
                    await self.process_event(event)
                
                # If stream ends, wait before retrying
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                self._logger.error(f"Error processing events: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def get_handler_count(self) -> Dict[str, int]:
        """Get count of handlers by event type."""
        counts = {}
        
        for event_type, handlers in self._handlers.items():
            counts[event_type.value] = len(handlers)
        
        counts["global"] = len(self._global_handlers)
        return counts


class EventProcessor:
    """Synchronous wrapper for AsyncEventProcessor."""
    
    def __init__(self, async_processor: AsyncEventProcessor):
        """Initialize sync wrapper."""
        self._async_processor = async_processor
    
    def __enter__(self):
        """Sync context manager entry."""
        anyio.from_thread.run(self._async_processor.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        anyio.from_thread.run(self._async_processor.__aexit__, exc_type, exc_val, exc_tb)
    
    def add_handler(
        self,
        event_type: TaskEventType,
        handler: EventHandler
    ) -> None:
        """Add an event handler for a specific event type."""
        # Wrap sync handler for async processor
        async def async_handler(event: TaskEvent) -> None:
            handler(event)
        
        self._async_processor.add_handler(event_type, async_handler)
    
    def add_global_handler(self, handler: EventHandler) -> None:
        """Add a global event handler that receives all events."""
        # Wrap sync handler for async processor
        async def async_handler(event: TaskEvent) -> None:
            handler(event)
        
        self._async_processor.add_global_handler(async_handler)
    
    def process_event(self, event: TaskEvent) -> None:
        """Process a single event through all relevant handlers."""
        anyio.from_thread.run(self._async_processor.process_event, event)
    
    def get_recent_events(
        self,
        task_id: Optional[str] = None,
        event_types: Optional[List[TaskEventType]] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get recent events from storage."""
        return anyio.from_thread.run(
            self._async_processor.get_recent_events,
            task_id, event_types, limit
        )