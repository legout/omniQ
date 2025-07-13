"""TaskResult model for execution outcomes."""

from __future__ import annotations

import time
import traceback
from typing import Any, Dict, Optional

import msgspec


class TaskError(msgspec.Struct):
    """Task execution error details."""
    
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    retry_count: int = 0
    timestamp: float = msgspec.field(default_factory=time.time)


class TaskResult(msgspec.Struct):
    """Task execution result with comprehensive outcome tracking."""
    
    # Required fields first
    task_id: str
    status: str  # "success", "failure", "timeout", "cancelled"
    started_at: float
    
    # Optional fields with defaults
    worker_id: Optional[str] = None
    result: Any = None
    error: Optional[TaskError] = None
    completed_at: float = msgspec.field(default_factory=time.time)
    duration: Optional[float] = None
    worker_type: Optional[str] = None
    execution_attempts: int = 1
    memory_peak_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None
    tags: Dict[str, str] = msgspec.field(default_factory=dict)
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Calculate duration after initialization."""
        if self.duration is None:
            self.duration = self.completed_at - self.started_at
    
    @classmethod
    def success(
        cls,
        task_id: str,
        result: Any,
        started_at: float,
        worker_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        execution_attempts: int = 1,
        **kwargs
    ) -> TaskResult:
        """Create a successful task result."""
        return cls(
            task_id=task_id,
            worker_id=worker_id,
            status="success",
            result=result,
            started_at=started_at,
            worker_type=worker_type,
            execution_attempts=execution_attempts,
            **kwargs
        )
    
    @classmethod
    def failure(
        cls,
        task_id: str,
        error: Exception,
        started_at: float,
        worker_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        execution_attempts: int = 1,
        retry_count: int = 0,
        **kwargs
    ) -> TaskResult:
        """Create a failed task result."""
        task_error = TaskError(
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback.format_exc(),
            retry_count=retry_count
        )
        
        return cls(
            task_id=task_id,
            worker_id=worker_id,
            status="failure",
            error=task_error,
            started_at=started_at,
            worker_type=worker_type,
            execution_attempts=execution_attempts,
            **kwargs
        )
    
    @classmethod
    def timeout(
        cls,
        task_id: str,
        started_at: float,
        worker_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        execution_attempts: int = 1,
        **kwargs
    ) -> TaskResult:
        """Create a timeout task result."""
        task_error = TaskError(
            error_type="TimeoutError",
            error_message="Task execution exceeded timeout limit"
        )
        
        return cls(
            task_id=task_id,
            worker_id=worker_id,
            status="timeout",
            error=task_error,
            started_at=started_at,
            worker_type=worker_type,
            execution_attempts=execution_attempts,
            **kwargs
        )
    
    @classmethod
    def cancelled(
        cls,
        task_id: str,
        started_at: float,
        worker_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        **kwargs
    ) -> TaskResult:
        """Create a cancelled task result."""
        return cls(
            task_id=task_id,
            worker_id=worker_id,
            status="cancelled",
            started_at=started_at,
            worker_type=worker_type,
            **kwargs
        )
    
    def is_success(self) -> bool:
        """Check if result represents success."""
        return self.status == "success"
    
    def is_failure(self) -> bool:
        """Check if result represents failure."""
        return self.status in ("failure", "timeout", "cancelled")
    
    def get_duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return (self.duration or 0.0) * 1000
    
    def with_tags(self, **tags: str) -> TaskResult:
        """Return new result with additional tags."""
        new_tags = {**self.tags, **tags}
        return msgspec.structs.replace(self, tags=new_tags)
    
    def with_metadata(self, **metadata: Any) -> TaskResult:
        """Return new result with additional metadata."""
        new_metadata = {**self.metadata, **metadata}
        return msgspec.structs.replace(self, metadata=new_metadata)