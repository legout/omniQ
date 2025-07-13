"""OmniQ Models - Core data structures for task queue operations."""

from .task import Task, TaskDependency, TaskCallback
from .schedule import Schedule, ScheduleConfig
from .result import TaskResult, TaskError
from .event import TaskEvent, TaskEventType
from .config import (
    QueueConfig,
    WorkerConfig,
    StorageConfig,
    SerializationConfig,
    EventConfig,
    OmniQConfig
)

__all__ = [
    "Task",
    "TaskDependency", 
    "TaskCallback",
    "Schedule",
    "ScheduleConfig",
    "TaskResult",
    "TaskError",
    "TaskEvent",
    "TaskEventType",
    "QueueConfig",
    "WorkerConfig",
    "StorageConfig",
    "SerializationConfig",
    "EventConfig",
    "OmniQConfig",
]