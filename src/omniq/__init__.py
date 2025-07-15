"""
OmniQ: A Flexible Task Queue Library for Python

OmniQ is a modular Python task queue library designed for both local and distributed 
task processing. It provides a flexible architecture that supports multiple storage 
backends, worker types, and configuration methods.
"""

from .core import OmniQ
from .models import Task, TaskResult, Schedule, TaskEvent
from .models.schedule import ScheduleType, ScheduleStatus
from .backend import SQLiteBackend
from .queue.scheduler import AsyncScheduler, Scheduler

__version__ = "0.1.0"
__all__ = [
    "OmniQ",
    "Task",
    "TaskResult",
    "Schedule",
    "TaskEvent",
    "ScheduleType",
    "ScheduleStatus",
    "SQLiteBackend",
    "AsyncScheduler",
    "Scheduler",
]