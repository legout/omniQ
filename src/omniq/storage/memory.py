import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

from omniq.models import Task, TaskResult, TaskEvent
from omniq.storage import BaseResultStorage, BaseScheduleStorage, BaseTaskQueue


class MemoryTaskQueue(BaseTaskQueue):
    """An in-memory task queue for simple, single-process use cases."""

    def __init__(self) -> None:
        self._queues: Dict[str, Deque[Task]] = defaultdict(deque)
        self._tasks: Dict[str, Task] = {}
        self._queue_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()  # For tasks and dependency data
        self._reverse_deps: Dict[str, set[str]] = defaultdict(set)

    async def enqueue(self, task: Task) -> str:
        async with self._global_lock:
            if task.dependencies:
                task.status = "waiting"
                task.dependencies_left = len(task.dependencies)
                for dep_id in task.dependencies:
                    self._reverse_deps[dep_id].add(task.id)
            else:
                task.status = "pending"

            self._tasks[task.id] = task

            if task.status == "pending":
                async with self._queue_locks[task.queue]:
                    self._queues[task.queue].append(task)
        return task.id

    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        start_time = time.monotonic()
        while True:
            for queue_name in queues:
                async with self._queue_locks[queue_name]:
                    if self._queues[queue_name]:
                        task = self._queues[queue_name].popleft()
                        return task
            if timeout == 0 or (time.monotonic() - start_time) >= timeout:
                return None
            await asyncio.sleep(0.01)  # Prevent busy-waiting

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with self._global_lock:
            return self._tasks.get(task_id)

    async def ack(self, task: Task) -> None:
        tasks_to_queue = []
        async with self._global_lock:
            # Remove the completed task
            self._tasks.pop(task.id, None)

            # Check for dependents and update their counters
            dependents = self._reverse_deps.pop(task.id, set())
            for dependent_id in dependents:
                if dependent_task := self._tasks.get(dependent_id):
                    dependent_task.dependencies_left -= 1
                    if dependent_task.dependencies_left <= 0:
                        dependent_task.status = "pending"
                        tasks_to_queue.append(dependent_task)

        # Enqueue newly pending tasks outside the global lock to avoid deadlocks
        for t in tasks_to_queue:
            async with self._queue_locks[t.queue]:
                self._queues[t.queue].append(t)

    async def nack(self, task: Task, requeue: bool = True) -> None:
        if requeue:
            await self.enqueue(task)

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        async with self._global_lock:
            tasks = [
                t for t in self._tasks.values() if t.status in ("pending", "waiting")
            ]
            if queue:
                tasks = [t for t in tasks if t.queue == queue]
            return sorted(tasks, key=lambda t: t.created_at)[:limit]

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        async with self._global_lock:
            tasks = [t for t in self._tasks.values() if t.status == "failed"]
            if queue:
                tasks = [t for t in tasks if t.queue == queue]
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]


class MemoryResultStorage(BaseResultStorage):
    """An in-memory result store."""

    def __init__(self) -> None:
        self._results: Dict[str, TaskResult] = {}

    async def store(self, result: TaskResult) -> None:
        self._results[result.task_id] = result

    async def get(self, task_id: str) -> Optional[TaskResult]:
        return self._results.get(task_id)

    async def delete(self, task_id: str) -> None:
        self._results.pop(task_id, None)


class MemoryEventStorage():  # type: ignore
    """An in-memory event store (non-persistent)."""

    def __init__(self) -> None:
        self._events: List[TaskEvent] = []

    async def log(self, event: TaskEvent) -> None:
        self._events.append(event)

    async def get_events(self, task_id: str) -> List[TaskEvent]:
        return [e for e in self._events if e.task_id == task_id]


class MemoryScheduleStorage(BaseScheduleStorage):
    """An in-memory schedule store."""

    def __init__(self) -> None:
        self._schedules: Dict[str, Schedule] = {}

    async def add_schedule(self, schedule: Schedule) -> str:
        self._schedules[schedule.id] = schedule
        return schedule.id

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return self._schedules.get(schedule_id)

    async def list_schedules(self) -> List[Schedule]:
        return list(self._schedules.values())

    async def delete_schedule(self, schedule_id: str) -> None:
        self._schedules.pop(schedule_id, None)

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        if schedule := self._schedules.get(schedule_id):
            schedule.is_paused = True
            return schedule
        return None

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        if schedule := self._schedules.get(schedule_id):
            schedule.is_paused = False
            return schedule
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass