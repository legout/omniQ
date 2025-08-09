"""OmniQ data models.

This module contains all the core data structures used by OmniQ:
- Task: Represents a task to be executed
- TaskResult: Represents the result of a task execution
- TaskEvent: Represents events in the task lifecycle
"""

from .task import Task
from .result import TaskResult, TaskStatus
from .event import TaskEvent, TaskEventType

__all__ = [
    "Task",
    "TaskResult", 
    "TaskStatus",
    "TaskEvent",
    "TaskEventType",
]