from typing import Dict, List, Optional, Union
import asyncio
import time
from datetime import datetime
import pytz
from ..models.schedule import Schedule
from ..storage.base import BaseTaskStorage
from .async_task_queue import AsyncTaskQueue
from .sync_task_queue import SyncTaskQueue

class Scheduler:
    """
    Manages the processing of schedules and enqueues tasks when they are due.
    Provides both async and sync interfaces for integration with OmniQ task queues.
    """
    def __init__(self, task_queue: Union[AsyncTaskQueue, SyncTaskQueue], poll_interval: float = 60.0):
        """
        Initialize the Scheduler with a task queue and polling interval.
        
        Args:
            task_queue: The task queue to enqueue tasks into when schedules are due.
            poll_interval: The interval (in seconds) to check for due schedules.
        """
        self.task_queue = task_queue
        self.poll_interval = poll_interval
        self.schedules: Dict[str, Schedule] = {}
        self.running = False

    def add_schedule(self, schedule: Schedule) -> None:
        """Add a schedule to be managed by the scheduler (sync)."""
        self.schedules[schedule.id] = schedule

    async def add_schedule_async(self, schedule: Schedule) -> None:
        """Add a schedule to be managed by the scheduler (async)."""
        self.schedules[schedule.id] = schedule

    def remove_schedule(self, schedule_id: str) -> None:
        """Remove a schedule from the scheduler (sync)."""
        self.schedules.pop(schedule_id, None)

    async def remove_schedule_async(self, schedule_id: str) -> None:
        """Remove a schedule from the scheduler (async)."""
        self.schedules.pop(schedule_id, None)

    def get_due_schedules(self) -> List[Schedule]:
        """Check and return a list of schedules that are due for execution (sync)."""
        due_schedules = []
        for schedule in self.schedules.values():
            if schedule.is_due():
                due_schedules.append(schedule)
        return due_schedules

    async def get_due_schedules_async(self) -> List[Schedule]:
        """Check and return a list of schedules that are due for execution (async)."""
        due_schedules = []
        for schedule in self.schedules.values():
            if schedule.is_due():
                due_schedules.append(schedule)
        return due_schedules

    async def process_schedules_async(self) -> None:
        """Process due schedules and enqueue tasks (async)."""
        due_schedules = await self.get_due_schedules_async()
        for schedule in due_schedules:
            # Create task from schedule data
            task_data = schedule.task_data
            # Enqueue task using the async task queue
            if isinstance(self.task_queue, AsyncTaskQueue):
                task_id = await self.task_queue.enqueue(**task_data)
                # Update schedule's last execution time
                tz = pytz.timezone(schedule.timezone)
                schedule.last_execution = datetime.now(tz).timestamp()
                # TODO: Calculate next execution time based on timing type and value
                schedule.next_execution = None  # Placeholder
                print(f"Task {task_id} enqueued for schedule {schedule.id}")
            else:
                # Fallback for sync task queue in async context
                task_id = self.task_queue.enqueue(**task_data)
                tz = pytz.timezone(schedule.timezone)
                schedule.last_execution = datetime.now(tz).timestamp()
                schedule.next_execution = None
                print(f"Task {task_id} enqueued for schedule {schedule.id}")

    def process_schedules(self) -> None:
        """Process due schedules and enqueue tasks (sync)."""
        due_schedules = self.get_due_schedules()
        for schedule in due_schedules:
            # Create task from schedule data
            task_data = schedule.task_data
            # Enqueue task using the sync task queue
            task_id = self.task_queue.enqueue(**task_data)
            # Update schedule's last execution time
            tz = pytz.timezone(schedule.timezone)
            schedule.last_execution = datetime.now(tz).timestamp()
            # TODO: Calculate next execution time based on timing type and value
            schedule.next_execution = None  # Placeholder
            print(f"Task {task_id} enqueued for schedule {schedule.id}")

    async def run_async(self) -> None:
        """Run the scheduler loop to continuously check for due schedules (async)."""
        self.running = True
        while self.running:
            await self.process_schedules_async()
            await asyncio.sleep(self.poll_interval)

    def run(self) -> None:
        """Run the scheduler loop to continuously check for due schedules (sync)."""
        self.running = True
        while self.running:
            self.process_schedules()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the scheduler loop (sync)."""
        self.running = False

    async def stop_async(self) -> None:
        """Stop the scheduler loop (async)."""
        self.running = False

class AsyncScheduler(Scheduler):
    """Async-specific scheduler implementation."""
    def __init__(self, task_queue: AsyncTaskQueue, poll_interval: float = 60.0):
        super().__init__(task_queue, poll_interval)

class SyncScheduler(Scheduler):
    """Sync-specific scheduler implementation."""
    def __init__(self, task_queue: SyncTaskQueue, poll_interval: float = 60.0):
        super().__init__(task_queue, poll_interval)
