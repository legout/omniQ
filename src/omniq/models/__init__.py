"""OmniQ data models.

This module contains all the core data structures used by OmniQ:
- Task: Represents a task to be executed
- TaskResult: Represents the result of a task execution
- TaskEvent: Represents events in the task lifecycle
- Schedule: Represents a recurring task schedule
"""

from .task import Task
from .result import TaskResult, TaskStatus
from .event import TaskEvent, TaskEventType
from .schedule import Schedule

__all__ = [
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskEvent",
    "TaskEventType",
    "Schedule",
]