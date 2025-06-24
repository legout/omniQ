"""TaskResult: Data model for task execution results in OmniQ."""

from typing import Any, Optional
from datetime import datetime

from msgspec import Struct

class TaskResult(Struct):
    """Task execution result data model."""
    
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    completed_at: datetime = datetime.utcnow()
    ttl: Optional[float] = None
