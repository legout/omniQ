from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.models.task_event import TaskEvent


class BaseTaskStorage(ABC):
    """Abstract base class for task storage backends with sync and async methods."""

    @abstractmethod
    def store_task(self, task: Task) -> None:
        """Synchronously store a task in the backend."""
        pass

    @abstractmethod
    async def store_task_async(self, task: Task) -> None:
        """Asynchronously store a task in the backend."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        """Synchronously retrieve a task by ID."""
        pass

    @abstractmethod
    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Asynchronously retrieve a task by ID."""
        pass

    @abstractmethod
    def get_tasks(self, limit: int = 100) -> List[Task]:
        """Synchronously retrieve a list of tasks, optionally limited."""
        pass

    @abstractmethod
    async def get_tasks_async(self, limit: int = 100) -> List[Task]:
        """Asynchronously retrieve a list of tasks, optionally limited."""
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Synchronously delete a task by ID."""
        pass

    @abstractmethod
    async def delete_task_async(self, task_id: str) -> bool:
        """Asynchronously delete a task by ID."""
        pass

    @abstractmethod
    def cleanup_expired_tasks(self, current_time: datetime) -> int:
        """Synchronously clean up expired tasks based on TTL."""
        pass

    @abstractmethod
    async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired tasks based on TTL."""
        pass

    @abstractmethod
    def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
        """Synchronously update the state of a schedule (active/paused)."""
        pass

    @abstractmethod
    async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
        """Asynchronously update the state of a schedule (active/paused)."""
        pass

    @abstractmethod
    def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
        """Synchronously retrieve the state of a schedule (active/paused)."""
        pass

    @abstractmethod
    async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
        """Asynchronously retrieve the state of a schedule (active/paused)."""
        pass


class BaseResultStorage(ABC):
    """Abstract base class for result storage backends with sync and async methods."""

    @abstractmethod
    def store_result(self, result: TaskResult) -> None:
        """Synchronously store a task result in the backend."""
        pass

    @abstractmethod
    async def store_result_async(self, result: TaskResult) -> None:
        """Asynchronously store a task result in the backend."""
        pass

    @abstractmethod
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Synchronously retrieve a task result by task ID."""
        pass

    @abstractmethod
    async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
        """Asynchronously retrieve a task result by task ID."""
        pass

    @abstractmethod
    def get_results(self, limit: int = 100) -> List[TaskResult]:
        """Synchronously retrieve a list of task results, optionally limited."""
        pass

    @abstractmethod
    async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
        """Asynchronously retrieve a list of task results, optionally limited."""
        pass

    @abstractmethod
    def delete_result(self, task_id: str) -> bool:
        """Synchronously delete a task result by task ID."""
        pass

    @abstractmethod
    async def delete_result_async(self, task_id: str) -> bool:
        """Asynchronously delete a task result by task ID."""
        pass

    @abstractmethod
    def cleanup_expired_results(self, current_time: datetime) -> int:
        """Synchronously clean up expired results based on TTL."""
        pass

    @abstractmethod
    async def cleanup_expired_results_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired results based on TTL."""
        pass


class BaseEventStorage(ABC):
    """Abstract base class for event storage backends with sync and async methods, restricted to SQL-based backends."""

    @abstractmethod
    def log_event(self, event: TaskEvent) -> None:
        """Synchronously log a task event."""
        pass

    @abstractmethod
    async def log_event_async(self, event: TaskEvent) -> None:
        """Asynchronously log a task event."""
        pass

    @abstractmethod
    def get_events(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Synchronously retrieve events, optionally filtered by task ID or event type."""
        pass

    @abstractmethod
    async def get_events_async(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Asynchronously retrieve events, optionally filtered by task ID or event type."""
        pass

    @abstractmethod
    def cleanup_old_events(self, retention_days: int) -> int:
        """Synchronously clean up old events based on retention policy."""
        pass

    @abstractmethod
    async def cleanup_old_events_async(self, retention_days: int) -> int:
        """Asynchronously clean up old events based on retention policy."""
        pass
