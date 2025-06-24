"""Task: Data model for tasks in OmniQ."""

from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
import uuid

from msgspec import Struct

class Task(Struct):
    """Task data model with metadata, dependencies, callbacks, and TTL."""
    
    func: Callable
    args: Tuple[Any, ...] = ()
    kwargs: Dict[str, Any] = {}
    dependencies: List[str] = []
    callbacks: List[Callable] = []
    id: str = str(uuid.uuid4())
    timeout: Optional[float] = None
    ttl: Optional[float] = None
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    retry_count: int = 0
    
    def __hash__(self) -> int:
        """Hash the task based on its ID."""
        return hash(self.id)
        
    def __eq__(self, other: Any) -> bool:
        """Compare tasks based on their IDs."""
        if not isinstance(other, Task):
            return False
        return self.id == other.id
