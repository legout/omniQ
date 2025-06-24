"""EventLogger: Central event collection and logging for OmniQ."""

import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from omniq.events.types import EventType
from omniq.models.task_event import TaskEvent
from omniq.storage.base import BaseEventStorage

logger = logging.getLogger(__name__)

class EventLogger:
    """Central event collection with configurable levels for OmniQ."""
    
    def __init__(self, storage: Optional[BaseEventStorage] = None, log_level: str = "INFO"):
        """Initialize the event logger.
        
        Args:
            storage (Optional[BaseEventStorage]): Storage backend for events. If None, events are only logged to console.
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, DISABLED).
        """
        self.storage = storage
        self.log_level = self._parse_log_level(log_level)
        self.disabled = self.log_level == logging.NOTSET
        
    def _parse_log_level(self, level: str) -> int:
        """Parse log level string to logging level integer.
        
        Args:
            level (str): Log level string (DEBUG, INFO, WARNING, ERROR, DISABLED).
            
        Returns:
            int: Corresponding logging level.
        """
        level = level.upper()
        if level == "DEBUG":
            return logging.DEBUG
        elif level == "INFO":
            return logging.INFO
        elif level == "WARNING":
            return logging.WARNING
        elif level == "ERROR":
            return logging.ERROR
        elif level == "DISABLED":
            return logging.NOTSET
        return logging.INFO
        
    def set_log_level(self, level: str) -> None:
        """Set the logging level at runtime.
        
        Args:
            level (str): New logging level (DEBUG, INFO, WARNING, ERROR, DISABLED).
        """
        self.log_level = self._parse_log_level(level)
        self.disabled = self.log_level == logging.NOTSET
        logger.info("Event logger level set to %s", level)
        
    async def log_event(self, event_type: EventType, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a task lifecycle event asynchronously.
        
        Args:
            event_type (EventType): Type of event to log.
            task_id (str): ID of the task associated with the event.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the event.
        """
        metadata = metadata or {}
        event = TaskEvent(
            event_type=event_type.value,
            task_id=task_id,
            timestamp=datetime.now().timestamp(),
            metadata=metadata
        )

        if self.storage:
            await self.storage.log_event(event)

        if self.disabled:
            return
        
        if logger.isEnabledFor(self.log_level):
            logger.log(self.log_level, "Event %s for task %s: %s", event_type.value, task_id, metadata)
            
        
            
    def log_event_sync(self, event_type: EventType, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a task lifecycle event synchronously.
        
        Args:
            event_type (EventType): Type of event to log.
            task_id (str): ID of the task associated with the event.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the event.
        """
        metadata = metadata or {}
        event = TaskEvent(
            event_type=event_type.value,
            task_id=task_id,
            timestamp=datetime.now().timestamp(),
            metadata=metadata
        )

        if self.storage:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(self.storage.log_event(event), loop).result()

        if self.disabled:
            return
            
       
        
        if logger.isEnabledFor(self.log_level):
            logger.log(self.log_level, "Event %s for task %s: %s", event_type.value, task_id, metadata)
            
        
