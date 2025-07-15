"""
Scheduler engine for OmniQ.

This module provides the scheduling engine that manages recurring tasks,
cron-based scheduling, and schedule persistence and recovery.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager, contextmanager

from ..models.task import Task
from ..models.schedule import Schedule, ScheduleStatus, ScheduleType
from ..models.event import TaskEvent, EventType
from ..storage.base import BaseTaskQueue, BaseScheduleStorage, BaseEventStorage

logger = logging.getLogger(__name__)


class AsyncScheduler:
    """
    Async scheduler engine for managing scheduled tasks.
    
    This class handles cron-like scheduling, recurring task management,
    and schedule persistence and recovery.
    """
    
    def __init__(
        self,
        task_queue: BaseTaskQueue,
        schedule_storage: BaseScheduleStorage,
        event_storage: Optional[BaseEventStorage] = None,
        poll_interval: float = 1.0,
        max_concurrent_schedules: int = 100,
    ):
        """
        Initialize the async scheduler.
        
        Args:
            task_queue: Task queue for submitting scheduled tasks
            schedule_storage: Storage for schedule persistence
            event_storage: Optional event storage for logging
            poll_interval: How often to check for ready schedules (seconds)
            max_concurrent_schedules: Maximum number of schedules to process concurrently
        """
        self.task_queue = task_queue
        self.schedule_storage = schedule_storage
        self.event_storage = event_storage
        self.poll_interval = poll_interval
        self.max_concurrent_schedules = max_concurrent_schedules
        
        # Runtime state
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(max_concurrent_schedules)
        
        # Function registry for resolving function names
        self._function_registry: Dict[str, Callable] = {}
    
    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function for scheduled execution.
        
        Args:
            name: Function name
            func: Function to register
        """
        self._function_registry[name] = func
    
    def unregister_function(self, name: str) -> None:
        """
        Unregister a function.
        
        Args:
            name: Function name to unregister
        """
        self._function_registry.pop(name, None)
    
    async def create_schedule(
        self,
        func: Union[str, Callable],
        schedule_type: ScheduleType,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        cron_expression: Optional[str] = None,
        interval: Optional[timedelta] = None,
        timestamp: Optional[datetime] = None,
        max_runs: Optional[int] = None,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new schedule.
        
        Args:
            func: Function to schedule (name or callable)
            schedule_type: Type of schedule (CRON, INTERVAL, TIMESTAMP)
            args: Function arguments
            kwargs: Function keyword arguments
            queue_name: Queue to submit tasks to
            cron_expression: Cron expression (for CRON type)
            interval: Interval between runs (for INTERVAL type)
            timestamp: Specific timestamp to run (for TIMESTAMP type)
            max_runs: Maximum number of runs
            ttl: Time-to-live for the schedule
            metadata: Additional metadata
            
        Returns:
            Schedule ID
        """
        # Create schedule based on type
        if schedule_type == ScheduleType.CRON:
            if not cron_expression:
                raise ValueError("cron_expression is required for CRON schedule")
            schedule = Schedule.from_cron(
                cron_expression=cron_expression,
                func=func,
                args=args,
                kwargs=kwargs or {},
                queue_name=queue_name,
                max_runs=max_runs,
                ttl=ttl,
                metadata=metadata or {},
            )
        elif schedule_type == ScheduleType.INTERVAL:
            if not interval:
                raise ValueError("interval is required for INTERVAL schedule")
            schedule = Schedule.from_interval(
                interval=interval,
                func=func,
                args=args,
                kwargs=kwargs or {},
                queue_name=queue_name,
                max_runs=max_runs,
                ttl=ttl,
                metadata=metadata or {},
            )
        elif schedule_type == ScheduleType.TIMESTAMP:
            if not timestamp:
                raise ValueError("timestamp is required for TIMESTAMP schedule")
            schedule = Schedule.from_timestamp(
                timestamp=timestamp,
                func=func,
                args=args,
                kwargs=kwargs or {},
                queue_name=queue_name,
                max_runs=max_runs,
                ttl=ttl,
                metadata=metadata or {},
            )
        else:
            raise ValueError(f"Unsupported schedule type: {schedule_type}")
        
        # Save schedule
        await self.schedule_storage.save_schedule(schedule)
        
        # Log event
        if self.event_storage:
            event = TaskEvent(
                task_id="",  # No task ID yet
                event_type=EventType.ENQUEUED,
                schedule_id=schedule.id,
                queue_name=queue_name,
                message=f"Schedule {schedule.id} created with type {schedule_type.value}",
                metadata={"schedule_type": schedule_type.value}
            )
            await self.event_storage.log_event(event)
        
        logger.info(f"Created schedule {schedule.id} of type {schedule_type.value}")
        return schedule.id
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        return await self.schedule_storage.get_schedule(schedule_id)
    
    async def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules."""
        status_str = status.value if status else None
        return await self.schedule_storage.list_schedules(
            status=status_str,
            limit=limit,
            offset=offset
        )
    
    async def pause_schedule(self, schedule_id: str) -> bool:
        """
        Pause a schedule.
        
        Args:
            schedule_id: Schedule ID to pause
            
        Returns:
            True if schedule was paused, False if not found
        """
        schedule = await self.schedule_storage.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.pause()
        await self.schedule_storage.update_schedule(schedule)
        
        # Log event
        if self.event_storage:
            event = TaskEvent.create_schedule_paused(
                task_id="",
                schedule_id=schedule_id,
                metadata={"action": "schedule_paused"}
            )
            await self.event_storage.log_event(event)
        
        logger.info(f"Paused schedule {schedule_id}")
        return True
    
    async def resume_schedule(self, schedule_id: str) -> bool:
        """
        Resume a paused schedule.
        
        Args:
            schedule_id: Schedule ID to resume
            
        Returns:
            True if schedule was resumed, False if not found
        """
        schedule = await self.schedule_storage.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.resume()
        await self.schedule_storage.update_schedule(schedule)
        
        # Log event
        if self.event_storage:
            event = TaskEvent.create_schedule_resumed(
                task_id="",
                schedule_id=schedule_id,
                metadata={"action": "schedule_resumed"}
            )
            await self.event_storage.log_event(event)
        
        logger.info(f"Resumed schedule {schedule_id}")
        return True
    
    async def cancel_schedule(self, schedule_id: str) -> bool:
        """
        Cancel a schedule.
        
        Args:
            schedule_id: Schedule ID to cancel
            
        Returns:
            True if schedule was cancelled, False if not found
        """
        schedule = await self.schedule_storage.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.cancel()
        await self.schedule_storage.update_schedule(schedule)
        
        # Log event
        if self.event_storage:
            event = TaskEvent.create_cancelled(
                task_id="",
                reason="Schedule cancelled",
                schedule_id=schedule_id,
                metadata={"action": "schedule_cancelled"}
            )
            await self.event_storage.log_event(event)
        
        logger.info(f"Cancelled schedule {schedule_id}")
        return True
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            schedule_id: Schedule ID to delete
            
        Returns:
            True if schedule was deleted, False if not found
        """
        deleted = await self.schedule_storage.delete_schedule(schedule_id)
        if deleted:
            logger.info(f"Deleted schedule {schedule_id}")
        return deleted
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that processes ready schedules."""
        while self._running:
            try:
                # Get ready schedules
                ready_schedules = await self.schedule_storage.get_ready_schedules()
                
                # Process each ready schedule
                tasks = []
                for schedule in ready_schedules:
                    if len(tasks) >= self.max_concurrent_schedules:
                        break
                    
                    task = asyncio.create_task(self._process_schedule(schedule))
                    tasks.append(task)
                
                # Wait for all tasks to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _process_schedule(self, schedule: Schedule) -> None:
        """
        Process a single ready schedule.
        
        Args:
            schedule: Schedule to process
        """
        async with self._semaphore:
            try:
                # Create task from schedule - handle both string and callable functions
                func_name = schedule.func if isinstance(schedule.func, str) else schedule.func.__name__
                task = Task(
                    func=func_name,
                    args=schedule.args,
                    kwargs=schedule.kwargs,
                    queue_name=schedule.queue_name,
                    metadata={
                        **schedule.metadata,
                        "schedule_id": schedule.id,
                        "schedule_type": schedule.schedule_type.value,
                    }
                )
                
                # Submit task to queue
                await self.task_queue.enqueue(task)
                
                # Mark schedule as run
                schedule.mark_run()
                await self.schedule_storage.update_schedule(schedule)
                
                # Log event
                if self.event_storage:
                    event = TaskEvent.create_enqueued(
                        task_id=task.id,
                        schedule_id=schedule.id,
                        queue_name=schedule.queue_name,
                        metadata={
                            "schedule_type": schedule.schedule_type.value,
                            "run_count": schedule.run_count,
                        }
                    )
                    await self.event_storage.log_event(event)
                
                logger.debug(f"Processed schedule {schedule.id}, created task {task.id}")
                
            except Exception as e:
                logger.error(f"Error processing schedule {schedule.id}: {e}", exc_info=True)
                
                # Log error event
                if self.event_storage:
                    event = TaskEvent.create_failed(
                        task_id="",
                        worker_id="scheduler",
                        error=e,
                        metadata={"schedule_id": schedule.id, "error_type": type(e).__name__}
                    )
                    await self.event_storage.log_event(event)
    
    async def recover_schedules(self) -> int:
        """
        Recover schedules after restart.
        
        This method loads all active schedules and recalculates their next run times
        based on the current time.
        
        Returns:
            Number of schedules recovered
        """
        try:
            # Get all active schedules
            active_schedules = await self.schedule_storage.list_schedules(
                status=ScheduleStatus.ACTIVE.value
            )
            
            recovered_count = 0
            for schedule in active_schedules:
                try:
                    # Recalculate next run time
                    old_next_run = schedule.next_run
                    schedule.next_run = schedule._calculate_next_run()
                    
                    # Update if next run time changed
                    if schedule.next_run != old_next_run:
                        await self.schedule_storage.update_schedule(schedule)
                        recovered_count += 1
                        
                        logger.debug(f"Recovered schedule {schedule.id}, next run: {schedule.next_run}")
                    
                except Exception as e:
                    logger.error(f"Error recovering schedule {schedule.id}: {e}", exc_info=True)
            
            logger.info(f"Recovered {recovered_count} schedules")
            return recovered_count
            
        except Exception as e:
            logger.error(f"Error during schedule recovery: {e}", exc_info=True)
            return 0
    
    # Context manager support
    @asynccontextmanager
    async def running(self):
        """Async context manager for running the scheduler."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


class Scheduler:
    """
    Synchronous wrapper around AsyncScheduler.
    
    This class provides a synchronous interface to the async scheduler
    implementation using asyncio for thread-safe execution.
    """
    
    def __init__(
        self,
        task_queue: BaseTaskQueue,
        schedule_storage: BaseScheduleStorage,
        event_storage: Optional[BaseEventStorage] = None,
        poll_interval: float = 1.0,
        max_concurrent_schedules: int = 100,
    ):
        self._async_scheduler = AsyncScheduler(
            task_queue=task_queue,
            schedule_storage=schedule_storage,
            event_storage=event_storage,
            poll_interval=poll_interval,
            max_concurrent_schedules=max_concurrent_schedules,
        )
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a function for scheduled execution (sync)."""
        self._async_scheduler.register_function(name, func)
    
    def unregister_function(self, name: str) -> None:
        """Unregister a function (sync)."""
        self._async_scheduler.unregister_function(name)
    
    def create_schedule(
        self,
        func: Union[str, Callable],
        schedule_type: ScheduleType,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        cron_expression: Optional[str] = None,
        interval: Optional[timedelta] = None,
        timestamp: Optional[datetime] = None,
        max_runs: Optional[int] = None,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new schedule (sync)."""
        return asyncio.run(self._async_scheduler.create_schedule(
            func=func,
            schedule_type=schedule_type,
            args=args,
            kwargs=kwargs,
            queue_name=queue_name,
            cron_expression=cron_expression,
            interval=interval,
            timestamp=timestamp,
            max_runs=max_runs,
            ttl=ttl,
            metadata=metadata,
        ))
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID (sync)."""
        return asyncio.run(self._async_scheduler.get_schedule(schedule_id))
    
    def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules (sync)."""
        return asyncio.run(self._async_scheduler.list_schedules(status, limit, offset))
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule (sync)."""
        return asyncio.run(self._async_scheduler.pause_schedule(schedule_id))
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule (sync)."""
        return asyncio.run(self._async_scheduler.resume_schedule(schedule_id))
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a schedule (sync)."""
        return asyncio.run(self._async_scheduler.cancel_schedule(schedule_id))
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule (sync)."""
        return asyncio.run(self._async_scheduler.delete_schedule(schedule_id))
    
    def start(self) -> None:
        """Start the scheduler (sync)."""
        asyncio.run(self._async_scheduler.start())
    
    def stop(self) -> None:
        """Stop the scheduler (sync)."""
        asyncio.run(self._async_scheduler.stop())
    
    def recover_schedules(self) -> int:
        """Recover schedules after restart (sync)."""
        return asyncio.run(self._async_scheduler.recover_schedules())
    
    @contextmanager
    def running(self):
        """Sync context manager for running the scheduler."""
        self.start()
        try:
            yield self
        finally:
            self.stop()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.stop()