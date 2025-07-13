"""Core OmniQ and AsyncOmniQ implementations - Main orchestrator."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Union

import anyio

from .config.loader import ConfigProvider, LoggingConfig
from .events.logger import AsyncEventLogger, EventLogger
from .events.processor import AsyncEventProcessor, EventProcessor
from .models.config import OmniQConfig
from .models.result import TaskResult
from .models.schedule import Schedule
from .models.task import Task
from .serialization import SerializationManager, MsgspecSerializer, DillSerializer
from .storage.base import (
    BaseTaskQueue, BaseResultStorage, BaseEventStorage,
    TaskQueue, ResultStorage, EventStorage
)
from .workers.base import BaseWorker
from .workers.async_ import AsyncWorker


class AsyncOmniQ:
    """Main async OmniQ implementation - coordinates all components."""
    
    def __init__(
        self,
        config: Optional[OmniQConfig] = None,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        workers: Optional[List[BaseWorker]] = None
    ):
        """
        Initialize AsyncOmniQ.
        
        Args:
            config: Configuration object (auto-loaded if None)
            task_queue: Task queue implementation
            result_storage: Result storage implementation
            event_storage: Event storage implementation
            workers: List of worker instances
        """
        # Load configuration
        if config is None:
            config_provider = ConfigProvider()
            config = config_provider.load_auto()
        self.config = config
        
        # Setup logging
        LoggingConfig.setup_logging(level=config.log_level, disable_existing=False)
        self._logger = LoggingConfig.get_logger("core")
        
        # Initialize serialization
        self._serialization_manager = SerializationManager()
        self._serialization_manager.register_serializer(MsgspecSerializer())
        self._serialization_manager.register_serializer(DillSerializer())
        
        # Storage components (will be initialized in __aenter__)
        self._task_queue = task_queue
        self._result_storage = result_storage  
        self._event_storage = event_storage
        
        # Event system components
        self._event_logger: Optional[AsyncEventLogger] = None
        self._event_processor: Optional[AsyncEventProcessor] = None
        
        # Workers
        self._workers = workers or []
        self._worker_tasks: List[asyncio.Task] = []
        
        # Scheduler
        self._schedules: Dict[str, Schedule] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._scheduler_stop_event = asyncio.Event()
        
        # State
        self._started = False
        self._stopping = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self) -> None:
        """Start OmniQ and all components."""
        if self._started:
            return
        
        self._logger.info("Starting OmniQ")
        
        # Initialize storage backends if not provided
        if self._task_queue is None:
            self._task_queue = await self._create_task_queue()
        
        if self._result_storage is None:
            self._result_storage = await self._create_result_storage()
        
        if self._event_storage is None:
            self._event_storage = await self._create_event_storage()
        
        # Initialize event system
        self._event_logger = AsyncEventLogger(
            storage=self._event_storage,
            enabled=self.config.events.enabled,
            batch_size=self.config.events.batch_size,
            flush_interval=self.config.events.flush_interval,
            max_buffer_size=self.config.events.max_buffer_size
        )
        
        self._event_processor = AsyncEventProcessor(
            storage=self._event_storage,
            enabled=self.config.events.enabled
        )
        
        # Start components
        await self._task_queue.__aenter__()
        await self._result_storage.__aenter__()
        await self._event_storage.__aenter__()
        await self._event_logger.start()
        await self._event_processor.start()
        
        # Create default worker if none provided
        if not self._workers:
            default_worker = AsyncWorker(
                queue=self._task_queue,
                event_logger=self._event_logger,
                queues=self.config.worker.queues,
                polling_interval=self.config.worker.polling_interval
            )
            self._workers = [default_worker]
        
        # Start workers
        for worker in self._workers:
            worker_task = asyncio.create_task(worker.start())
            self._worker_tasks.append(worker_task)
        
        # Start scheduler
        self._scheduler_stop_event.clear()
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self._started = True
        self._logger.info("OmniQ started successfully")
    
    async def stop(self) -> None:
        """Stop OmniQ and all components gracefully."""
        if not self._started or self._stopping:
            return
        
        self._stopping = True
        self._logger.info("Stopping OmniQ")
        
        # Stop scheduler
        if self._scheduler_task:
            self._scheduler_stop_event.set()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Stop workers
        for worker in self._workers:
            await worker.stop(timeout=self.config.worker.shutdown_timeout)
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Stop event system
        if self._event_processor:
            await self._event_processor.stop()
        
        if self._event_logger:
            await self._event_logger.stop()
        
        # Stop storage
        if self._event_storage:
            await self._event_storage.__aexit__(None, None, None)
        
        if self._result_storage:
            await self._result_storage.__aexit__(None, None, None)
        
        if self._task_queue:
            await self._task_queue.__aexit__(None, None, None)
        
        self._started = False
        self._stopping = False
        self._logger.info("OmniQ stopped")
    
    async def enqueue(
        self,
        func: Union[str, Callable],
        *args,
        queue: str = "default",
        priority: int = 0,
        delay: Optional[float] = None,
        timeout: Optional[int] = None,
        ttl: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Task:
        """
        Enqueue a task for execution.
        
        Args:
            func: Function to execute (callable or string path)
            *args: Positional arguments for function
            queue: Queue name
            priority: Task priority (higher = more priority)
            delay: Delay execution by seconds
            timeout: Task execution timeout
            ttl: Task time-to-live
            max_retries: Maximum retry attempts
            **kwargs: Keyword arguments for function
        
        Returns:
            Created task object
        """
        # Create task
        task = Task(
            name=str(func),
            func=func,
            args=list(args),
            kwargs=kwargs,
            queue=queue,
            priority=priority,
            scheduled_at=time.time() + delay if delay else None,
            timeout=timeout,
            ttl=ttl or self.config.default_task_timeout,
            max_retries=max_retries if max_retries is not None else self.config.worker.pool_size
        )
        
        # Enqueue task
        await self._task_queue.enqueue(task)
        
        # Log event
        if self._event_logger:
            await self._event_logger.log_task_enqueued(
                task_id=task.id,
                queue_name=queue,
                priority=priority
            )
        
        self._logger.debug(f"Enqueued task {task.id} to queue '{queue}'")
        return task
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Get task result, optionally waiting for completion.
        
        Args:
            task_id: Task ID to get result for
            timeout: Maximum time to wait for result
        
        Returns:
            Task result or None if not found/timeout
        """
        if timeout is None:
            return await self._result_storage.get_result(task_id)
        
        # Wait for result with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = await self._result_storage.get_result(task_id)
            if result is not None:
                return result
            await asyncio.sleep(0.1)
        
        return None
    
    async def wait_for_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """
        Wait for task completion and return result.
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait
        
        Returns:
            Task result
        
        Raises:
            asyncio.TimeoutError: If timeout exceeded
            ValueError: If task result indicates failure
        """
        if self._event_processor:
            # Use event processor for real-time waiting
            from .models.event import TaskEventType
            
            completion_event = await self._event_processor.wait_for_event(
                task_id=task_id,
                event_type=TaskEventType.COMPLETED,
                timeout=timeout
            )
            
            if completion_event is None:
                # Check for failure events
                failure_event = await self._event_processor.wait_for_event(
                    task_id=task_id,
                    event_type=TaskEventType.FAILED,
                    timeout=0.1  # Quick check
                )
                
                if failure_event:
                    result = await self.get_result(task_id)
                    if result and result.error:
                        raise ValueError(f"Task failed: {result.error.error_message}")
                
                raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout}s")
        
        # Fallback to polling
        result = await self.get_result(task_id, timeout=timeout)
        if result is None:
            raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout}s")
        
        if result.is_failure():
            error_msg = result.error.error_message if result.error else "Unknown error"
            raise ValueError(f"Task failed: {error_msg}")
        
        return result
    
    async def add_schedule(self, schedule: Schedule) -> None:
        """Add a schedule for periodic task execution."""
        self._schedules[schedule.name] = schedule
        self._logger.info(f"Added schedule '{schedule.name}'")
    
    async def remove_schedule(self, name: str) -> bool:
        """Remove a schedule by name."""
        if name in self._schedules:
            del self._schedules[name]
            self._logger.info(f"Removed schedule '{name}'")
            return True
        return False
    
    async def pause_schedule(self, name: str) -> bool:
        """Pause a schedule."""
        if name in self._schedules:
            self._schedules[name].pause()
            self._logger.info(f"Paused schedule '{name}'")
            return True
        return False
    
    async def resume_schedule(self, name: str) -> bool:
        """Resume a schedule."""
        if name in self._schedules:
            self._schedules[name].resume()
            self._logger.info(f"Resumed schedule '{name}'")
            return True
        return False
    
    async def get_queue_size(self, queue_name: str = "default") -> int:
        """Get number of tasks in queue."""
        return await self._task_queue.size(queue_name)
    
    async def get_worker_status(self) -> List[Dict[str, Any]]:
        """Get status of all workers."""
        statuses = []
        for worker in self._workers:
            status = await worker.health_check()
            statuses.append(status)
        return statuses
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        worker_statuses = await self.get_worker_status()
        
        return {
            "omniq_started": self._started,
            "config": {
                "log_level": self.config.log_level,
                "debug": self.config.debug,
                "environment": self.config.environment,
            },
            "components": {
                "task_queue": await self._task_queue.health_check() if self._task_queue else None,
                "result_storage": await self._result_storage.health_check() if self._result_storage else None,
                "event_storage": await self._event_storage.health_check() if self._event_storage else None,
            },
            "workers": worker_statuses,
            "schedules": {
                name: {
                    "active": schedule.is_active,
                    "paused": schedule.is_paused,
                    "run_count": schedule.run_count,
                    "next_run": schedule.next_run_at,
                }
                for name, schedule in self._schedules.items()
            },
            "events": {
                "logger_buffer_size": self._event_logger.get_buffer_size() if self._event_logger else 0,
                "processor_handlers": self._event_processor.get_handler_count() if self._event_processor else {},
            }
        }
    
    async def _create_task_queue(self) -> BaseTaskQueue:
        """Create task queue based on configuration."""
        queue_config = self.config.get_task_storage_config()
        
        if queue_config.backend_type == "sqlite":
            from .storage.sqlite import SQLiteTaskQueue
            connection_string = queue_config.connection_string or ":memory:"
            return SQLiteTaskQueue(
                database_path=connection_string,
                table_prefix=queue_config.table_prefix,
                serialization_manager=self._serialization_manager
            )
        else:
            raise ValueError(f"Unsupported task queue backend: {queue_config.backend_type}")
    
    async def _create_result_storage(self) -> BaseResultStorage:
        """Create result storage based on configuration."""
        storage_config = self.config.get_result_storage_config()
        
        if storage_config.backend_type == "sqlite":
            from .storage.sqlite import SQLiteResultStorage
            connection_string = storage_config.connection_string or ":memory:"
            return SQLiteResultStorage(
                database_path=connection_string,
                table_prefix=storage_config.table_prefix,
                serialization_manager=self._serialization_manager
            )
        else:
            raise ValueError(f"Unsupported result storage backend: {storage_config.backend_type}")
    
    async def _create_event_storage(self) -> BaseEventStorage:
        """Create event storage based on configuration."""
        storage_config = self.config.get_event_storage_config()
        
        if storage_config.backend_type == "sqlite":
            from .storage.sqlite_event import SQLiteEventStorage
            connection_string = storage_config.connection_string or ":memory:"
            return SQLiteEventStorage(
                database_path=connection_string,
                table_prefix=storage_config.table_prefix
            )
        else:
            raise ValueError(f"Unsupported event storage backend: {storage_config.backend_type}")
    
    async def _scheduler_loop(self) -> None:
        """Background scheduler loop for periodic tasks."""
        while not self._scheduler_stop_event.is_set():
            try:
                current_time = time.time()
                
                for schedule in list(self._schedules.values()):
                    if schedule.is_due() and schedule.should_continue():
                        # Create and enqueue task for this schedule
                        # This would need schedule-to-task mapping logic
                        # For now, just mark as executed
                        schedule.mark_executed()
                        
                        if self._event_logger:
                            from .models.event import TaskEventType
                            await self._event_logger.log_schedule_event(
                                task_id=f"schedule-{schedule.name}",
                                event_type=TaskEventType.SCHEDULE_TRIGGERED,
                                schedule_name=schedule.name,
                                next_run=schedule.next_run_at
                            )
                
                # Wait before next check
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self._logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5.0)


class OmniQ:
    """Synchronous wrapper for AsyncOmniQ."""
    
    def __init__(self, *args, **kwargs):
        """Initialize sync wrapper."""
        self._async_omniq = AsyncOmniQ(*args, **kwargs)
    
    def __enter__(self):
        """Sync context manager entry."""
        anyio.from_thread.run(self._async_omniq.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        anyio.from_thread.run(self._async_omniq.__aexit__, exc_type, exc_val, exc_tb)
    
    def start(self) -> None:
        """Start OmniQ."""
        anyio.from_thread.run(self._async_omniq.start)
    
    def stop(self) -> None:
        """Stop OmniQ."""
        anyio.from_thread.run(self._async_omniq.stop)
    
    def enqueue(
        self,
        func: Union[str, Callable],
        *args,
        queue: str = "default",
        priority: int = 0,
        delay: Optional[float] = None,
        timeout: Optional[int] = None,
        ttl: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Task:
        """Enqueue a task for execution."""
        return anyio.from_thread.run(
            self._async_omniq.enqueue,
            func, *args,
            queue=queue, priority=priority, delay=delay,
            timeout=timeout, ttl=ttl, max_retries=max_retries,
            **kwargs
        )
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Get task result."""
        return anyio.from_thread.run(self._async_omniq.get_result, task_id, timeout)
    
    def wait_for_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """Wait for task completion and return result."""
        return anyio.from_thread.run(self._async_omniq.wait_for_result, task_id, timeout)
    
    def get_queue_size(self, queue_name: str = "default") -> int:
        """Get number of tasks in queue."""
        return anyio.from_thread.run(self._async_omniq.get_queue_size, queue_name)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return anyio.from_thread.run(self._async_omniq.health_check)