"""
Task model for OmniQ.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

import msgspec
from msgspec import Struct


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Task(Struct):
    """
    Represents a task to be executed by OmniQ.
    
    This class uses msgspec.Struct for high-performance serialization
    and includes all necessary metadata for task execution, scheduling,
    and dependency management.
    """
    
    # Function and arguments (required fields first)
    func: str
    
    # Core task identification
    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    args: tuple = msgspec.field(default_factory=tuple)
    kwargs: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Queue and priority
    queue_name: str = "default"
    priority: int = 0  # Higher numbers = higher priority
    
    # Timing and TTL
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    run_at: Optional[datetime] = None
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    
    # Task metadata
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: timedelta = timedelta(seconds=1)
    
    # Dependencies and callbacks
    dependencies: List[str] = msgspec.field(default_factory=list)
    callbacks: Dict[str, str] = msgspec.field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Set expires_at based on TTL if not already set
        if self.ttl is not None and self.expires_at is None:
            self.expires_at = self.created_at + self.ttl
    
    def is_expired(self) -> bool:
        """Check if the task has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_ready_to_run(self) -> bool:
        """Check if the task is ready to be executed."""
        if self.status != TaskStatus.PENDING:
            return False
        
        if self.is_expired():
            return False
            
        if self.run_at is not None and datetime.utcnow() < self.run_at:
            return False
            
        return True
    
    def should_retry(self) -> bool:
        """Check if the task should be retried after failure."""
        return (
            self.status == TaskStatus.FAILED and 
            self.retry_count < self.max_retries and
            not self.is_expired()
        )
    
    def get_next_retry_time(self) -> datetime:
        """Calculate the next retry time with exponential backoff."""
        delay_seconds = self.retry_delay.total_seconds() * (2 ** self.retry_count)
        return datetime.utcnow() + timedelta(seconds=delay_seconds)
    
    def __hash__(self) -> int:
        """Make Task hashable for dependency tracking."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Task equality based on ID."""
        if not isinstance(other, Task):
            return False
        return self.id == other.id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return msgspec.to_builtins(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary representation."""
        return msgspec.convert(data, cls)