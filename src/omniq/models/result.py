"""
Task result model for OmniQ.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from enum import Enum

import msgspec
from msgspec import Struct


class ResultStatus(str, Enum):
    """Task result status."""
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskResult(Struct):
    """
    Represents the result of a task execution.
    
    This class stores the outcome of task execution including
    the result value, error information, and execution metadata.
    """
    
    # Core identification
    task_id: str
    
    # Result data
    status: ResultStatus = ResultStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    
    # Timing information
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # TTL and expiration
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    
    # Execution metadata
    worker_id: Optional[str] = None
    execution_time: Optional[float] = None  # in seconds
    memory_usage: Optional[int] = None  # in bytes
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Set expires_at based on TTL if not already set
        if self.ttl is not None and self.expires_at is None:
            self.expires_at = self.created_at + self.ttl
    
    def is_expired(self) -> bool:
        """Check if the result has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_completed(self) -> bool:
        """Check if the task execution is completed (success or error)."""
        return self.status in (ResultStatus.SUCCESS, ResultStatus.ERROR, ResultStatus.CANCELLED)
    
    def is_successful(self) -> bool:
        """Check if the task execution was successful."""
        return self.status == ResultStatus.SUCCESS
    
    def mark_started(self, worker_id: Optional[str] = None) -> None:
        """Mark the result as started."""
        self.started_at = datetime.utcnow()
        if worker_id:
            self.worker_id = worker_id
    
    def mark_success(self, result: Any) -> None:
        """Mark the result as successful."""
        self.status = ResultStatus.SUCCESS
        self.result = result
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def mark_error(self, error: Exception, traceback_str: Optional[str] = None) -> None:
        """Mark the result as failed."""
        self.status = ResultStatus.ERROR
        self.error = str(error)
        self.error_type = type(error).__name__
        self.traceback = traceback_str
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def mark_cancelled(self) -> None:
        """Mark the result as cancelled."""
        self.status = ResultStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return msgspec.to_builtins(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """Create result from dictionary representation."""
        return msgspec.convert(data, cls)