import asyncio
from types import TracebackType
from typing import Any, Callable, Coroutine, List, Optional, Type, TypeVar, AsyncGenerator

from .config import OmniQConfig, get_config
from .models import Schedule, Task, TaskResult, TaskEvent
from .storage import BaseResultStorage, BaseScheduleStorage, BaseTaskQueue, BaseEventStorage
from .storage.fsspec import FsspecResultStorage, FsspecTaskQueue
from .storage.memory import MemoryResultStorage, MemoryTaskQueue

try:
    from .storage.memory import MemoryScheduleStorage
except ImportError:
    MemoryScheduleStorage = None  # type: ignore

try:
    from .storage.sqlite import SqliteResultStorage, SqliteScheduleStorage, SqliteTaskQueue
except ImportError:
    SqliteResultStorage = SqliteTaskQueue = SqliteScheduleStorage = None  # type: ignore

try:
    from .storage.redis import RedisResultStorage, RedisScheduleStorage, RedisTaskQueue # type: ignore
except ImportError:
    RedisResultStorage = RedisTaskQueue = RedisScheduleStorage = None  # type: ignore

try:
    from .storage.postgres import PostgresResultStorage, PostgresScheduleStorage, PostgresTaskQueue, PostgresEventStorage
except ImportError:
    PostgresResultStorage = PostgresTaskQueue = PostgresScheduleStorage = None  # type: ignore

T = TypeVar("T")


def to_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Runs a coroutine in a new event loop."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # This is a simplification. A robust solution for sync-over-async
            # in an async context would involve a worker thread with its own loop.
            # For a simple sync entrypoint, creating a new loop is acceptable.
            return asyncio.run(coro)
    except RuntimeError:  # No running loop
        pass
    return asyncio.run(coro)


class OmniQ:
    """
    The main interface for OmniQ. Provides both synchronous and asynchronous methods.
    """

    def __init__(self, config: Optional[OmniQConfig] = None, **kwargs: Any):
        self.config = config or get_config(**kwargs)
        self.task_queue: BaseTaskQueue = self._init_storage(
            self.config.task_queue_url, "task_queue"
        )
        self.result_storage: BaseResultStorage = self._init_storage(
            self.config.result_storage_url, "result_storage"
        )
        self.schedule_storage: BaseScheduleStorage = self._init_storage(
            self.config.schedule_storage_url, "schedule_storage"
        )
        self.event_storage: Optional[BaseEventStorage] = self._init_storage(
            self.config.event_storage_url, "event_storage"
        ) if self.config.event_storage_url else None

    def _init_storage(self, url: str, storage_type: str) -> Any:
        """Factory function to initialize storage backends from a URL."""
        if url.startswith("memory://"):
            if storage_type == "task_queue":
                return MemoryTaskQueue()
            if storage_type == "result_storage":
                return MemoryResultStorage()
            if storage_type == "schedule_storage":
                return MemoryScheduleStorage()
            if storage_type == "event_storage":
                return MemoryEventStorage()

        if url.startswith("sqlite://"):
            if SqliteTaskQueue is None:
                raise ImportError("Please install 'omniq[sqlite]' to use the SQLite backend")
            if storage_type == "task_queue":
                return SqliteTaskQueue(url)
            if storage_type == "result_storage":
                return SqliteResultStorage(url)
            if storage_type == "schedule_storage":
                return SqliteScheduleStorage(url)

        if url.startswith("redis://"):
            if RedisTaskQueue is None:
                raise ImportError("Please install 'omniq[redis]' to use the Redis backend")
            if storage_type == "task_queue":
                return RedisTaskQueue(url)
            if storage_type == "result_storage":
                return RedisResultStorage(url)
            if storage_type == "schedule_storage":
                return RedisScheduleStorage(url)

        if url.startswith("postgresql://"):
            if PostgresTaskQueue is None:
                raise ImportError("Please install 'omniq[postgres]' to use the PostgreSQL backend")
            if storage_type == "task_queue":
                return PostgresTaskQueue(url)
            if storage_type == "result_storage":
                return PostgresResultStorage(url)
            if storage_type == "schedule_storage":
                return PostgresScheduleStorage(url)
            if storage_type == "event_storage":
                return PostgresEventStorage(url)

        protocol_part = url.split("://")[0]
        if protocol_part == "file" or "fsspec+" in protocol_part:
            if storage_type == "schedule_storage":
                raise NotImplementedError("fsspec schedule storage is not supported.")
            actual_url = url
            if "fsspec+" in protocol_part:
                actual_url = url.split("+", 1)[1]

            storage_opts = self.config.storage_options.get(protocol_part, {})
            if storage_type == "task_queue":
                return FsspecTaskQueue(actual_url, **storage_opts)
            if storage_type == "result_storage":
                return FsspecResultStorage(actual_url, **storage_opts)

        raise ValueError(f"Unsupported storage URL scheme for {storage_type}: {url}")

    # --- Async API ---

    async def enqueue(
        self, func: Callable[..., Any], *args: Any, queue: str = "default", **kwargs: Any
    ) -> str:
        """Asynchronously enqueue a task."""
        if self.event_storage:
            await self.event_storage.log(TaskEvent(task_id=task.id, event_type="ENQUEUED"))
        task = Task(func=func, args=args, kwargs=kwargs, queue=queue)
        return await self.task_queue.enqueue(task)

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Asynchronously get the result of a task."""
        return await self.result_storage.get(task_id)

    async def add_schedule(self, schedule: Schedule) -> str:
        """Asynchronously add a new task schedule."""
        return await self.schedule_storage.add_schedule(schedule)

    async def remove_schedule(self, schedule_id: str) -> None:
        """Asynchronously remove a task schedule by its ID."""
        await self.schedule_storage.delete_schedule(schedule_id)

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Asynchronously get a task schedule by its ID."""
        return await self.schedule_storage.get_schedule(schedule_id)

    async def list_schedules(self) -> List[Schedule]:
        """Asynchronously list all task schedules."""
        return await self.schedule_storage.list_schedules()

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Asynchronously pause a task schedule by its ID."""
        return await self.schedule_storage.pause_schedule(schedule_id)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Asynchronously resume a task schedule by its ID."""
        return await self.schedule_storage.resume_schedule(schedule_id)

    async def run_schedule(self, schedule_id: str) -> Optional[str]:
        """Asynchronously run a schedule's task immediately."""
        schedule = await self.get_schedule(schedule_id)
        if schedule:
            return await self.enqueue(schedule.task.func, *schedule.task.args, **schedule.task.kwargs)
        return None

    async def get_events(self, task_id: str) -> AsyncGenerator[TaskEvent, None]:
        """Asynchronously get the event history for a task."""
        if self.event_storage:
            async for event in self.event_storage.get_events(task_id):
                yield event


    async def list_recent_results(self, limit: int = 20) -> List[TaskResult]:
        """Asynchronously list recent task results."""
        return await self.result_storage.list_recent_results(limit)

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """Asynchronously list pending tasks."""
        return await self.task_queue.list_pending_tasks(queue=queue, limit=limit)

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """Asynchronously list failed tasks."""
        return await self.task_queue.list_failed_tasks(queue=queue, limit=limit)

    def list_pending_tasks_sync(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """Synchronously list pending tasks."""
        return to_sync(self.list_pending_tasks(queue=queue, limit=limit))

    def list_failed_tasks_sync(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        """Synchronously list failed tasks."""
        return to_sync(self.list_failed_tasks(queue=queue, limit=limit))

    def list_recent_results_sync(self, limit: int = 20) -> List[TaskResult]:
        """Synchronously list recent task results."""
        return to_sync(self.list_recent_results(limit))

    def get_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Synchronously get a task schedule by its ID."""
        return to_sync(self.get_schedule(schedule_id))

    def list_schedules_sync(self) -> List[Schedule]:
        """Synchronously list all task schedules."""
        return to_sync(self.list_schedules())

    def pause_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Synchronously pause a task schedule by its ID."""
        return to_sync(self.pause_schedule(schedule_id))

    def resume_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Synchronously resume a task schedule by its ID."""
        return to_sync(self.resume_schedule(schedule_id))

    def run_schedule_sync(self, schedule_id: str) -> Optional[str]:
        """Synchronously run a schedule's task immediately."""
        return to_sync(self.run_schedule(schedule_id))

    async def __aenter__(self) -> "OmniQ":
        await self.task_queue.__aenter__()
        await self.result_storage.__aenter__()
        if self.event_storage:
            await self.event_storage.__aenter__()
        if self.schedule_storage:
            await self.schedule_storage.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.event_storage:
            await self.event_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self.schedule_storage:
            await self.schedule_storage.__aexit__(exc_type, exc_val, exc_tb)
        await self.task_queue.__aexit__(exc_type, exc_val, exc_tb)
        await self.result_storage.__aexit__(exc_type, exc_val, exc_tb)

    # --- Sync API ---

    def enqueue_sync(
        self, func: Callable[..., Any], *args: Any, queue: str = "default", **kwargs: Any
    ) -> str:
        """Synchronously enqueue a task."""
        return to_sync(self.enqueue(func, *args, queue=queue, **kwargs))

    def get_result_sync(self, task_id: str) -> Optional[TaskResult]:
        """Synchronously get the result of a task."""
        return to_sync(self.get_result(task_id))

    def add_schedule_sync(self, schedule: Schedule) -> str:
        """Synchronously add a new task schedule."""
        return to_sync(self.add_schedule(schedule))

    def remove_schedule_sync(self, schedule_id: str) -> None:
        """Synchronously remove a task schedule by its ID."""
        return to_sync(self.remove_schedule(schedule_id))

    def __enter__(self) -> "OmniQ":
        self.task_queue.__enter__()
        self.result_storage.__enter__()
        if self.event_storage:
            self.event_storage.__enter__()
        if self.schedule_storage:
            self.schedule_storage.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.event_storage:
            self.event_storage.__exit__(exc_type, exc_val, exc_tb)
        if self.schedule_storage:
            self.schedule_storage.__exit__(exc_type, exc_val, exc_tb)
        self.task_queue.__exit__(exc_type, exc_val, exc_tb)
        self.result_storage.__exit__(exc_type, exc_val, exc_tb)