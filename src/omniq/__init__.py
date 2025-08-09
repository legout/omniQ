"""OmniQ: A Flexible Task Queue Library for Python."""

from .core import OmniQ, AsyncOmniQ
from .models.config import OmniQConfig
from .models.task import Task
from .models.result import TaskResult, TaskStatus
from .models.event import TaskEvent, TaskEventType
from .queue.base import BaseQueue
from .results.base import BaseResultStorage
from .events.base import BaseEventStorage
from .workers.base import BaseWorker

__all__ = [
    # Core API
    "OmniQ",
    "AsyncOmniQ",
    "OmniQConfig",

    # Data Models
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskEvent",
    "TaskEventType",

    # Base Interfaces
    "BaseQueue",
    "BaseResultStorage",
    "BaseEventStorage",
    "BaseWorker",
]