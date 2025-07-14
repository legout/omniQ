from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Generator

from omniq.models.event import TaskEvent
from omniq.models.result import TaskResult
from omniq.models.task import Task


class BaseTaskQueue(ABC):
    """Abstract base class for a task queue."""

    @abstractmethod
    def enqueue(self, task: Task) -> None:
        """Enqueue a task."""
        pass

    @abstractmethod
    async def aenqueue(self, task: Task) -> None:
        """Enqueue a task asynchronously."""
        pass

    @abstractmethod
    def dequeue(self, queue_name: str) -> Task | None:
        """Dequeue a task from a specific queue."""
        pass

    @abstractmethod
    async def adequeue(self, queue_name: str) -> Task | None:
        """Dequeue a task from a specific queue asynchronously."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task | None:
        """Get a task by its ID."""
        pass

    @abstractmethod
    async def aget_task(self, task_id: str) -> Task | None:
        """Get a task by its ID asynchronously."""
        pass


class BaseResultStorage(ABC):
    """Abstract base class for a result storage."""

    @abstractmethod
    def set(self, result: TaskResult) -> None:
        """Set a task result."""
        pass

    @abstractmethod
    async def aset(self, result: TaskResult) -> None:
        """Set a task result asynchronously."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> TaskResult | None:
        """Get a task result by task ID."""
        pass

    @abstractmethod
    async def aget(self, task_id: str) -> TaskResult | None:
        """Get a task result by task ID asynchronously."""
        pass


class BaseEventStorage(ABC):
    """Abstract base class for an event storage."""

    @abstractmethod
    def log(self, event: TaskEvent) -> None:
        """Log a task event."""
        pass

    @abstractmethod
    async def alog(self, event: TaskEvent) -> None:
        """Log a task event asynchronously."""
        pass

    @abstractmethod
    def get_events(self, task_id: str) -> Generator[TaskEvent, None, None]:
        """Get all events for a specific task."""
        pass

    @abstractmethod
    async def aget_events(self, task_id: str) -> AsyncGenerator[TaskEvent, None]:
        """Get all events for a specific task asynchronously."""
        pass
