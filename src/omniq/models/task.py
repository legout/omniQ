# src/omniq/models/task.py
"""Task model for OmniQ."""

import uuid
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import msgspec

class Task(msgspec.Struct):
    """Task model for OmniQ."""
    
    id: str
    func: Union[Callable, str]  # Function or function name
    func_args: Dict[str, Any]
    queue_name: str
    created_at: datetime
    scheduled_at: datetime
    expires_at: Optional[datetime] = None
    result_ttl: Optional[timedelta] = None
    status: str = "pending"
    
    @classmethod
    def create(
        cls,
        func: Union[Callable, str],
        func_args: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        run_in: Optional[timedelta] = None,
        run_at: Optional[datetime] = None,
        ttl: Optional[timedelta] = None,
        result_ttl: Optional[timedelta] = None
    ) -> "Task":
        """Create a new task."""
        now = datetime.utcnow()
        
        scheduled_at = now
        if run_in is not None:
            scheduled_at = now + run_in
        if run_at is not None:
            scheduled_at = run_at
        if scheduled_at < now:
            raise ValueError("Scheduled time cannot be in the past")

        expires_at = None
        if ttl is not None:
            expires_at = now + ttl
        
        return cls(
            id=str(uuid.uuid4()),
            func=func,
            func_args=func_args or {},
            queue_name=queue_name,
            created_at=now,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            result_ttl=result_ttl
        )
    
    def is_expired(self) -> bool:
        """Check if the task is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def is_ready(self) -> bool:
        """Check if the task is ready to be executed."""
        return datetime.now() >= self.scheduled_at and not self.is_expired()