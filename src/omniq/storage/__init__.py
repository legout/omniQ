from abc import ABC, abstractmethod
from types import TracebackType
from typing import AsyncGenerator, List, Optional, Type

from omniq.models import Schedule, Task, TaskEvent, TaskResult


class BaseTaskQueue(ABC):
    """Abstract base class for a task queue."""

    @abstractmethod
    async def enqueue(self, task: Task) -> str:
        """Enqueue a task."""
        raise NotImplementedError

    @abstractmethod
    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        """Dequeue a task from one of the specified queues."""
        raise NotImplementedError

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def ack(self, task: Task) -> None:
        """Acknowledge a task has been processed."""
        raise NotImplementedError

    @abstractmethod
    async def nack(self, task: Task, requeue: bool = True) -> None:
        """Negatively acknowledge a task."""
        raise NotImplementedError

    @abstractmethod
    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """List tasks that are pending (or waiting for dependencies)."""
        raise NotImplementedError

    @abstractmethod
    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """List tasks that have failed."""
        raise NotImplementedError

    async def __aenter__(self) -> "BaseTaskQueue":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def __enter__(self) -> "BaseTaskQueue":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass


class BaseResultStorage(ABC):
    """Abstract base class for result storage."""

    @abstractmethod
    async def store(self, result: TaskResult) -> None:
        """Store a task result."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, task_id: str) -> None:
        """Delete a task result."""
        raise NotImplementedError

    @abstractmethod
    async def list_recent_results(self, limit: int) -> List[TaskResult]:
        """List the most recent task results."""
        raise NotImplementedError


class BaseEventStorage(ABC):
    """Abstract base class for event storage."""

    @abstractmethod
    async def log(self, event: TaskEvent) -> None:
        """Log a task event."""
        raise NotImplementedError

    @abstractmethod
    async def get_events(self, task_id: str) -> AsyncGenerator[TaskEvent, None]:
        """Get all events for a specific task."""
        raise NotImplementedError

class BaseScheduleStorage(ABC):
    """Abstract base class for schedule storage."""

    @abstractmethod
    async def add_schedule(self, schedule: Schedule) -> str:
        """Add a new schedule."""
        raise NotImplementedError

    @abstractmethod
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def list_schedules(self) -> List[Schedule]:
        """List all schedules."""
        raise NotImplementedError

    @abstractmethod
    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Pause a schedule by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Resume a schedule by its ID."""
        raise NotImplementedError