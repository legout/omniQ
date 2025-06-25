# src/omniq/models/result.py
"""Result model for OmniQ."""

from typing import Any, Optional
from datetime import datetime, timedelta
import msgspec

class TaskResult(msgspec.Struct):
    """Task result model for OmniQ."""
    
    task_id: str
    result: Any
    status: str  # success, error
    created_at: datetime
    expires_at: Optional[datetime] = None
    error: Optional[str] = None

    
    @classmethod
    def create(
        cls,
        task_id: str,
        result: Any,
        status: str = "success",
        error: Optional[str] = None,
        ttl: Optional[timedelta] = None
    ) -> "TaskResult":
        """Create a new task result."""
        now = datetime.now()
        
        expires_at = None
        if ttl is not None:
            expires_at = now + ttl
        
        return cls(
            task_id=task_id,
            result=result,
            status=status,
            error=error,
            created_at=now,
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if the result is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at