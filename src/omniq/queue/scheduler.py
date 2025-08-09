"""Scheduler implementation for OmniQ.

This module provides the scheduler components for managing recurring tasks:
- AsyncScheduler: Async-first scheduler implementation
- Scheduler: Synchronous wrapper around AsyncScheduler

The scheduler manages schedules, checks for due tasks, and enqueues them
appropriately based on intervals or cron expressions.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Callable, Any
import logging

from ..models.schedule import Schedule
from ..models.task import Task
from ..models.result import TaskResult, TaskStatus
from ..models.event import TaskEvent, TaskEventType
from .base import BaseQueue

logger = logging.getLogger(__name__)


class AsyncScheduler:
    """Async-first scheduler for managing recurring tasks.
    
    This scheduler periodically checks for schedules that are due to run,
    enqueues tasks based on interval or cron expressions, and updates
    the schedule state accordingly.
    """
    
    def __init__(
        self,
        task_queue: BaseQueue,
        check_interval: float = 1.0,
        max_concurrent_checks: int = 10
    ):
        """Initialize AsyncScheduler.
        
        Args:
            task_queue: Task queue to enqueue tasks to
            check_interval: Interval in seconds between schedule checks
            max_concurrent_checks: Maximum number of concurrent schedule checks
        """
        self.task_queue = task_queue
        self.check_interval = check_interval
        self.max_concurrent_checks = max_concurrent_checks
        
        # Schedule storage
        self._schedules: Dict[uuid.UUID, Schedule] = {}
        
        # Scheduler state
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._check_semaphore = asyncio.Semaphore(max_concurrent_checks)
    
    async def add_schedule(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        interval: Optional[timedelta] = None,
        cron: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        schedule_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """Add a new schedule.
        
        Args:
            func: Function to execute (callable or string name)
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add tasks to
            interval: Interval between executions
            cron: Cron expression for scheduling
            start_at: When to start the schedule (defaults to now)
            end_at: When to end the schedule (optional)
            schedule_id: Optional schedule ID (generated if not provided)
            
        Returns:
            Schedule ID
            
        Raises:
            ValueError: If neither interval nor cron is provided
        """
        if interval is None and cron is None:
            raise ValueError("Either interval or cron must be provided")
        
        if interval is not None and cron is not None:
            raise ValueError("Cannot specify both interval and cron")
        
        # Generate schedule ID if not provided
        if schedule_id is None:
            schedule_id = uuid.uuid4()
        
        # Determine function name
        if callable(func):
            func_name = f"{func.__module__}.{func.__name__}"
        else:
            func_name = str(func)
        
        # Set default start time
        if start_at is None:
            start_at = datetime.utcnow()
        
        # Create schedule
        schedule = Schedule(
            id=schedule_id,
            func_name=func_name,
            args=func_args or (),
            kwargs=func_kwargs or {},
            interval=interval,
            cron=cron,
            start_at=start_at,
            end_at=end_at,
            queue_name=queue_name
        )
        
        # Calculate initial next run time
        schedule.next_run_at = schedule.calculate_next_run(start_at)
        
        # Store schedule
        self._schedules[schedule_id] = schedule
        
        logger.info(f"Added schedule {schedule_id} for function {func_name}")
        return schedule_id
    
    async def remove_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Remove a schedule.
        
        Args:
            schedule_id: ID of the schedule to remove
            
        Returns:
            True if schedule was removed, False if not found
        """
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            logger.info(f"Removed schedule {schedule_id}")
            return True
        return False
    
    async def get_schedule(self, schedule_id: uuid.UUID) -> Optional[Schedule]:
        """Get a schedule by ID.
        
        Args:
            schedule_id: ID of the schedule to get
            
        Returns:
            Schedule or None if not found
        """
        return self._schedules.get(schedule_id)
    
    async def list_schedules(self) -> List[Schedule]:
        """List all schedules.
        
        Returns:
            List of all schedules
        """
        return list(self._schedules.values())
    
    async def pause_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Pause a schedule.
        
        Args:
            schedule_id: ID of the schedule to pause
            
        Returns:
            True if schedule was paused, False if not found
        """
        schedule = self._schedules.get(schedule_id)
        if schedule:
            schedule.pause()
            logger.info(f"Paused schedule {schedule_id}")
            return True
        return False
    
    async def resume_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Resume a schedule.
        
        Args:
            schedule_id: ID of the schedule to resume
            
        Returns:
            True if schedule was resumed, False if not found
        """
        schedule = self._schedules.get(schedule_id)
        if schedule:
            schedule.resume()
            # Recalculate next run time
            current_time = datetime.utcnow()
            schedule.next_run_at = schedule.calculate_next_run(current_time)
            logger.info(f"Resumed schedule {schedule_id}")
            return True
        return False
    
    async def start(self) -> None:
        """Start the scheduler.
        
        Raises:
            RuntimeError: If scheduler is already running
        """
        if self._running:
            raise RuntimeError("Scheduler is already running")
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_run_schedules()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_run_schedules(self) -> None:
        """Check all schedules and run those that are due."""
        current_time = datetime.utcnow()
        
        # Create tasks for concurrent schedule checking
        check_tasks = []
        for schedule in self._schedules.values():
            if schedule.should_run(current_time):
                task = asyncio.create_task(
                    self._check_semaphore.acquire()
                )
                task.add_done_callback(lambda _: self._check_semaphore.release())
                check_tasks.append(
                    self._run_schedule_task(schedule, current_time, task)
                )
        
        # Wait for all check tasks to complete
        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _run_schedule_task(
        self,
        schedule: Schedule,
        current_time: datetime,
        semaphore_task: asyncio.Task
    ) -> None:
        """Run a task for a schedule.
        
        Args:
            schedule: The schedule to run
            current_time: Current time
            semaphore_task: Semaphore task for concurrency control
        """
        try:
            # Wait for semaphore
            await semaphore_task
            
            # Double-check if schedule should still run
            if not schedule.should_run(current_time):
                return
            
            # Create task for the schedule
            task_id = uuid.uuid4()
            task = Task(
                id=task_id,
                func_name=schedule.func_name,
                args=schedule.args,
                kwargs=schedule.kwargs,
                created_at=current_time,
                dependencies=schedule.dependencies if hasattr(schedule, 'dependencies') else []
            )
            
            # Enqueue the task
            await self.task_queue.enqueue_async(task, schedule.queue_name)
            
            # Update schedule
            schedule.update_after_run(current_time)
            
            logger.info(f"Enqueued task {task_id} for schedule {schedule.id}")
            
        except Exception as e:
            logger.error(f"Error running schedule {schedule.id}: {e}")
    
    async def __aenter__(self) -> "AsyncScheduler":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


class Scheduler:
    """Synchronous wrapper around AsyncScheduler.
    
    This class provides a blocking interface for the scheduler,
    wrapping the async implementation to provide a traditional synchronous API.
    """
    
    def __init__(
        self,
        task_queue: BaseQueue,
        check_interval: float = 1.0,
        max_concurrent_checks: int = 10
    ):
        """Initialize Scheduler.
        
        Args:
            task_queue: Task queue to enqueue tasks to
            check_interval: Interval in seconds between schedule checks
            max_concurrent_checks: Maximum number of concurrent schedule checks
        """
        self._async_scheduler = AsyncScheduler(
            task_queue=task_queue,
            check_interval=check_interval,
            max_concurrent_checks=max_concurrent_checks
        )
    
    def add_schedule(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        interval: Optional[timedelta] = None,
        cron: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        schedule_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """Add a new schedule (synchronous).
        
        Args:
            func: Function to execute (callable or string name)
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add tasks to
            interval: Interval between executions
            cron: Cron expression for scheduling
            start_at: When to start the schedule (defaults to now)
            end_at: When to end the schedule (optional)
            schedule_id: Optional schedule ID (generated if not provided)
            
        Returns:
            Schedule ID
        """
        return asyncio.run(
            self._async_scheduler.add_schedule(
                func, func_args, func_kwargs, queue_name,
                interval, cron, start_at, end_at, schedule_id
            )
        )
    
    def remove_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Remove a schedule (synchronous).
        
        Args:
            schedule_id: ID of the schedule to remove
            
        Returns:
            True if schedule was removed, False if not found
        """
        return asyncio.run(self._async_scheduler.remove_schedule(schedule_id))
    
    def get_schedule(self, schedule_id: uuid.UUID) -> Optional[Schedule]:
        """Get a schedule by ID (synchronous).
        
        Args:
            schedule_id: ID of the schedule to get
            
        Returns:
            Schedule or None if not found
        """
        return asyncio.run(self._async_scheduler.get_schedule(schedule_id))
    
    def list_schedules(self) -> List[Schedule]:
        """List all schedules (synchronous).
        
        Returns:
            List of all schedules
        """
        return asyncio.run(self._async_scheduler.list_schedules())
    
    def pause_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Pause a schedule (synchronous).
        
        Args:
            schedule_id: ID of the schedule to pause
            
        Returns:
            True if schedule was paused, False if not found
        """
        return asyncio.run(self._async_scheduler.pause_schedule(schedule_id))
    
    def resume_schedule(self, schedule_id: uuid.UUID) -> bool:
        """Resume a schedule (synchronous).
        
        Args:
            schedule_id: ID of the schedule to resume
            
        Returns:
            True if schedule was resumed, False if not found
        """
        return asyncio.run(self._async_scheduler.resume_schedule(schedule_id))
    
    def start(self) -> None:
        """Start the scheduler (synchronous)."""
        asyncio.run(self._async_scheduler.start())
    
    def stop(self) -> None:
        """Stop the scheduler (synchronous)."""
        asyncio.run(self._async_scheduler.stop())
    
    def __enter__(self) -> "Scheduler":
        """Synchronous context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Synchronous context manager exit."""
        self.stop()