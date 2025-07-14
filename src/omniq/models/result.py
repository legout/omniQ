from __future__ import annotations
import time
from typing import Any
import msgspec

class TaskResult(msgspec.Struct, kw_only=True):
    """
    Represents the result of a task execution.
    """
    # Task identification
    task_id: str

    # Execution outcome
    status: str # e.g., 'SUCCESS', 'FAILURE'
    result: Any | None = None
    exception: str | None = None

    # Timing information
    started_at: float
    completed_at: float = msgspec.field(default_factory=time.time)

    @property
    def duration(self) -> float:
        return self.completed_at - self.started_at
