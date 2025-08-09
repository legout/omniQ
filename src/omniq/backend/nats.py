"""NATS backend integration for OmniQ.

This module provides the NATS backend implementation that combines
the NATS queue and result storage components.
"""

from typing import Dict, Any, Optional

from .base import BaseBackend
from ..queue.nats import AsyncNATSQueue, NATSQueue
from ..results.nats import AsyncNATSResultStorage, NATSResultStorage


class NATSBackend(BaseBackend):
    """NATS backend for OmniQ.
    
    This backend uses NATS for all storage components:
    - Task queue: NATS with queue groups for exclusive consumption
    - Result storage: NATS with request-reply pattern
    - Event storage: Not supported with NATS backend
    """
    
    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        subject_prefix: str = "omniq",
        queue_group: str = "omniq_workers",
        **connection_kwargs
    ):
        """Initialize the NATS backend.
        
        Args:
            nats_url: NATS connection URL
            subject_prefix: Prefix for all NATS subjects
            queue_group: NATS queue group for exclusive consumption
            **connection_kwargs: Additional connection arguments for NATS
        """
        config = {
            "nats_url": nats_url,
            "subject_prefix": subject_prefix,
            "queue_group": queue_group,
            "connection_kwargs": connection_kwargs
        }
        super().__init__(config)
        
        self.nats_url = nats_url
        self.subject_prefix = subject_prefix
        self.queue_group = queue_group
        self.connection_kwargs = connection_kwargs
        
        self._queue: Optional[NATSQueue] = None
        self._result_storage: Optional[NATSResultStorage] = None
    
    def create_queue(self) -> NATSQueue:
        """Create a NATS task queue instance.
        
        Returns:
            A NATSQueue instance
        """
        if not self._queue:
            self._queue = NATSQueue(
                nats_url=self.nats_url,
                subject_prefix=self.subject_prefix,
                queue_group=self.queue_group,
                **self.connection_kwargs
            )
        return self._queue
    
    def create_result_storage(self) -> NATSResultStorage:
        """Create a NATS result storage instance.
        
        Returns:
            A NATSResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = NATSResultStorage(
                nats_url=self.nats_url,
                subject_prefix=self.subject_prefix,
                **self.connection_kwargs
            )
        return self._result_storage
    
    def create_event_storage(self):
        """Create an event storage instance.
        
        Note: NATS backend does not support event storage.
        
        Returns:
            None
            
        Raises:
            NotImplementedError: Always raised as NATS doesn't support event storage
        """
        raise NotImplementedError("NATS backend does not support event storage")
    
    def close(self) -> None:
        """Close all backend components."""
        if self._queue:
            self._queue.close()
            self._queue = None
        
        if self._result_storage:
            self._result_storage.close()
            self._result_storage = None
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()