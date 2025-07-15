"""
Core OmniQ class and orchestration logic.

This module provides the main OmniQ class that serves as the primary interface
for task queue operations, coordinating between storage backends, workers,
and serialization components.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager, contextmanager

from .models import Task, TaskResult, TaskEvent, Schedule
from .models.config import OmniQConfig, SQLiteConfig, QueueConfig
from .models.schedule import ScheduleType, ScheduleStatus
from .backend.sqlite import SQLiteBackend
from .storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from .storage.factory import StorageBackendFactory
from .queue.scheduler import AsyncScheduler, Scheduler
from .queue_manager import QueueManager
from .config import AdvancedConfigManager, load_config_from_yaml, load_config_from_dict


logger = logging.getLogger(__name__)


class OmniQ:
    """
    Main OmniQ task queue orchestrator.
    
    This class provides the primary interface for task queue operations,
    managing task submission, execution, result retrieval, and event handling.
    """
    
    def __init__(
        self,
        backend: Optional[Union[SQLiteBackend, str]] = None,
        config: Optional[OmniQConfig] = None,
        **kwargs
    ):
        """
        Initialize OmniQ instance.
        
        Args:
            backend: Backend instance or connection string (legacy support)
            config: OmniQ configuration
            **kwargs: Additional configuration options
        """
        self.config = config or OmniQConfig.from_env()
        
        # Legacy backend support (for backward compatibility)
        self.backend = None
        if backend is not None:
            if isinstance(backend, str):
                # Parse connection string
                if backend.startswith("sqlite://"):
                    self.backend = SQLiteBackend.from_url(backend)
                else:
                    raise ValueError(f"Unsupported backend URL: {backend}")
            else:
                self.backend = backend
        
        # Storage components (will be initialized from config)
        self._task_queue: Optional[BaseTaskQueue] = None
        self._result_storage: Optional[BaseResultStorage] = None
        self._event_storage: Optional[BaseEventStorage] = None
        self._schedule_storage: Optional[BaseScheduleStorage] = None
        
        # Scheduler components
        self._async_scheduler: Optional[AsyncScheduler] = None
        self._sync_scheduler: Optional[Scheduler] = None
        
        # Worker management
        self._workers: Dict[str, Any] = {}
        self._running = False
        
        # Task registry for function decorators
        self._task_registry: Dict[str, Callable] = {}
        
        # Queue manager for advanced queue operations
        self._queue_manager: Optional[QueueManager] = None
    
    async def connect(self) -> None:
        """Connect to the backend and initialize storage components."""
        if self.backend:
            # Legacy backend mode - use single backend for all components
            self._task_queue = self.backend.get_task_queue(async_mode=True)
            self._result_storage = self.backend.get_result_storage(async_mode=True)
            self._event_storage = self.backend.get_event_storage(async_mode=True)
            self._schedule_storage = self.backend.get_schedule_storage(async_mode=True)
            
            # Connect all components
            await self.backend.connect_all()
        else:
            # New independent storage backend mode
            self._task_queue = StorageBackendFactory.create_task_queue(
                self.config.get_task_queue_backend_config(), async_mode=True
            )
            self._result_storage = StorageBackendFactory.create_result_storage(
                self.config.get_result_storage_backend_config(), async_mode=True
            )
            self._event_storage = StorageBackendFactory.create_event_storage(
                self.config.get_event_storage_backend_config(), async_mode=True
            )
            self._schedule_storage = StorageBackendFactory.create_schedule_storage(
                self.config.get_schedule_storage_backend_config(), async_mode=True
            )
            
            # Connect individual storage components
            if hasattr(self._task_queue, 'connect'):
                connect_method = getattr(self._task_queue, 'connect')
                if asyncio.iscoroutinefunction(connect_method):
                    await connect_method()
                else:
                    connect_method()
            if hasattr(self._result_storage, 'connect'):
                connect_method = getattr(self._result_storage, 'connect')
                if asyncio.iscoroutinefunction(connect_method):
                    await connect_method()
                else:
                    connect_method()
            if hasattr(self._event_storage, 'connect'):
                connect_method = getattr(self._event_storage, 'connect')
                if asyncio.iscoroutinefunction(connect_method):
                    await connect_method()
                else:
                    connect_method()
            if hasattr(self._schedule_storage, 'connect'):
                connect_method = getattr(self._schedule_storage, 'connect')
                if asyncio.iscoroutinefunction(connect_method):
                    await connect_method()
                else:
                    connect_method()
        
        # Initialize scheduler
        self._async_scheduler = AsyncScheduler(
            task_queue=self._task_queue,
            schedule_storage=self._schedule_storage,
            event_storage=self._event_storage,
        )
        
        # Initialize queue manager
        self._queue_manager = QueueManager(self.config, self._task_queue)
        
        logger.info("OmniQ connected to storage backends")
    
    async def disconnect(self) -> None:
        """Disconnect from the backend."""
        if self.backend:
            # Legacy backend mode
            await self.backend.disconnect_all()
        else:
            # Independent storage backend mode
            if hasattr(self._task_queue, 'disconnect'):
                disconnect_method = getattr(self._task_queue, 'disconnect')
                if asyncio.iscoroutinefunction(disconnect_method):
                    await disconnect_method()
                else:
                    disconnect_method()
            if hasattr(self._result_storage, 'disconnect'):
                disconnect_method = getattr(self._result_storage, 'disconnect')
                if asyncio.iscoroutinefunction(disconnect_method):
                    await disconnect_method()
                else:
                    disconnect_method()
            if hasattr(self._event_storage, 'disconnect'):
                disconnect_method = getattr(self._event_storage, 'disconnect')
                if asyncio.iscoroutinefunction(disconnect_method):
                    await disconnect_method()
                else:
                    disconnect_method()
            if hasattr(self._schedule_storage, 'disconnect'):
                disconnect_method = getattr(self._schedule_storage, 'disconnect')
                if asyncio.iscoroutinefunction(disconnect_method):
                    await disconnect_method()
                else:
                    disconnect_method()
        
        logger.info("OmniQ disconnected from storage backends")
    
    def connect_sync(self) -> None:
        """Connect to the backend synchronously."""
        if self.backend:
            # Legacy backend mode - use single backend for all components
            self._task_queue = self.backend.get_task_queue(async_mode=False)
            self._result_storage = self.backend.get_result_storage(async_mode=False)
            self._event_storage = self.backend.get_event_storage(async_mode=False)
            self._schedule_storage = self.backend.get_schedule_storage(async_mode=False)
            
            # Connect all components
            self.backend.connect_all_sync()
        else:
            # New independent storage backend mode
            self._task_queue = StorageBackendFactory.create_task_queue(
                self.config.get_task_queue_backend_config(), async_mode=False
            )
            self._result_storage = StorageBackendFactory.create_result_storage(
                self.config.get_result_storage_backend_config(), async_mode=False
            )
            self._event_storage = StorageBackendFactory.create_event_storage(
                self.config.get_event_storage_backend_config(), async_mode=False
            )
            self._schedule_storage = StorageBackendFactory.create_schedule_storage(
                self.config.get_schedule_storage_backend_config(), async_mode=False
            )
            
            # Connect individual storage components
            if hasattr(self._task_queue, 'connect'):
                connect_method = getattr(self._task_queue, 'connect')
                if not asyncio.iscoroutinefunction(connect_method):
                    connect_method()
                else:
                    # For sync mode, we can't call async methods directly
                    # Most storage implementations should have sync connect methods
                    logger.warning("Storage component has async connect method in sync mode")
            if hasattr(self._result_storage, 'connect'):
                connect_method = getattr(self._result_storage, 'connect')
                if not asyncio.iscoroutinefunction(connect_method):
                    connect_method()
                else:
                    logger.warning("Storage component has async connect method in sync mode")
            if hasattr(self._event_storage, 'connect'):
                connect_method = getattr(self._event_storage, 'connect')
                if not asyncio.iscoroutinefunction(connect_method):
                    connect_method()
                else:
                    logger.warning("Storage component has async connect method in sync mode")
            if hasattr(self._schedule_storage, 'connect'):
                connect_method = getattr(self._schedule_storage, 'connect')
                if not asyncio.iscoroutinefunction(connect_method):
                    connect_method()
                else:
                    logger.warning("Storage component has async connect method in sync mode")
        
        # Initialize scheduler
        self._sync_scheduler = Scheduler(
            task_queue=self._task_queue,
            schedule_storage=self._schedule_storage,
            event_storage=self._event_storage,
        )
        
        # Initialize queue manager
        self._queue_manager = QueueManager(self.config, self._task_queue)
        
        logger.info("OmniQ connected to storage backends (sync)")
    
    def disconnect_sync(self) -> None:
        """Disconnect from the backend synchronously."""
        if self.backend:
            # Legacy backend mode
            self.backend.disconnect_all_sync()
        else:
            # Independent storage backend mode
            if hasattr(self._task_queue, 'disconnect'):
                disconnect_method = getattr(self._task_queue, 'disconnect')
                if not asyncio.iscoroutinefunction(disconnect_method):
                    disconnect_method()
                else:
                    logger.warning("Storage component has async disconnect method in sync mode")
            if hasattr(self._result_storage, 'disconnect'):
                disconnect_method = getattr(self._result_storage, 'disconnect')
                if not asyncio.iscoroutinefunction(disconnect_method):
                    disconnect_method()
                else:
                    logger.warning("Storage component has async disconnect method in sync mode")
            if hasattr(self._event_storage, 'disconnect'):
                disconnect_method = getattr(self._event_storage, 'disconnect')
                if not asyncio.iscoroutinefunction(disconnect_method):
                    disconnect_method()
                else:
                    logger.warning("Storage component has async disconnect method in sync mode")
            if hasattr(self._schedule_storage, 'disconnect'):
                disconnect_method = getattr(self._schedule_storage, 'disconnect')
                if not asyncio.iscoroutinefunction(disconnect_method):
                    disconnect_method()
                else:
                    logger.warning("Storage component has async disconnect method in sync mode")
        
        logger.info("OmniQ disconnected from storage backends (sync)")
    
    # Task submission methods
    async def submit_task(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue: str = "default",
        priority: int = 0,
        delay: Optional[Union[int, float, timedelta]] = None,
        ttl: Optional[Union[int, float, timedelta]] = None,
        retry_attempts: int = 3,
        retry_delay: Union[int, float, timedelta] = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a task for execution.
        
        Args:
            func_name: Name of the function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            queue: Queue name to submit to
            priority: Task priority (higher = more priority)
            delay: Delay before task becomes available
            ttl: Time-to-live for the task
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries
            metadata: Additional task metadata
            
        Returns:
            Task ID
        """
        if not self._task_queue:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        # Create task
        task = Task(
            func=func_name,
            args=args,
            kwargs=kwargs or {},
            queue_name=queue,
            priority=priority,
            max_retries=retry_attempts,
            retry_delay=timedelta(seconds=retry_delay) if isinstance(retry_delay, (int, float)) else retry_delay,
            metadata=metadata or {},
        )
        
        # Handle delay
        if delay:
            if isinstance(delay, (int, float)):
                delay = timedelta(seconds=delay)
            task.run_at = datetime.utcnow() + delay
        
        # Handle TTL
        if ttl:
            if isinstance(ttl, (int, float)):
                ttl = timedelta(seconds=ttl)
            task.ttl = ttl
            task.expires_at = datetime.utcnow() + ttl
        elif self.config.default_ttl:
            task.ttl = timedelta(seconds=self.config.default_ttl)
            task.expires_at = datetime.utcnow() + task.ttl
        
        # Submit task using queue manager if available
        if self._queue_manager:
            await self._queue_manager.enqueue_with_validation(task)
        else:
            await self._task_queue.enqueue(task)
        
        # Log event
        if self._event_storage:
            event = TaskEvent.create_enqueued(
                task_id=task.id,
                queue_name=queue,
                metadata={"priority": priority}
            )
            await self._event_storage.log_event(event)
        
        logger.info(f"Task {task.id} submitted to queue '{queue}'")
        return task.id
    
    def submit_task_sync(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue: str = "default",
        priority: int = 0,
        delay: Optional[Union[int, float, timedelta]] = None,
        ttl: Optional[Union[int, float, timedelta]] = None,
        retry_attempts: int = 3,
        retry_delay: Union[int, float, timedelta] = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Synchronous version of submit_task."""
        return asyncio.run(self.submit_task(
            func_name=func_name,
            args=args,
            kwargs=kwargs,
            queue=queue,
            priority=priority,
            delay=delay,
            ttl=ttl,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            metadata=metadata,
        ))
    
    # Task retrieval methods
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        if not self._task_queue:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._task_queue.get_task(task_id)
    
    def get_task_sync(self, task_id: str) -> Optional[Task]:
        """Synchronous version of get_task."""
        return asyncio.run(self.get_task(task_id))
    
    async def get_tasks_by_queue(self, queue: str, limit: int = 100) -> List[Task]:
        """Get tasks from a specific queue."""
        if not self._task_queue:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._task_queue.list_tasks(queue_name=queue, limit=limit)
    
    def get_tasks_by_queue_sync(self, queue: str, limit: int = 100) -> List[Task]:
        """Synchronous version of get_tasks_by_queue."""
        return asyncio.run(self.get_tasks_by_queue(queue, limit))
    
    # Result methods
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by task ID."""
        if not self._result_storage:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._result_storage.get(task_id)
    
    def get_result_sync(self, task_id: str) -> Optional[TaskResult]:
        """Synchronous version of get_result."""
        return asyncio.run(self.get_result(task_id))
    
    async def wait_for_result(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 1.0
    ) -> Optional[TaskResult]:
        """
        Wait for a task result with polling.
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait (None = no timeout)
            poll_interval: Time between polls
            
        Returns:
            Task result or None if timeout
        """
        start_time = datetime.utcnow()
        
        while True:
            result = await self.get_result(task_id)
            if result:
                return result
            
            if timeout and (datetime.utcnow() - start_time).total_seconds() > timeout:
                return None
            
            await asyncio.sleep(poll_interval)
    
    def wait_for_result_sync(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 1.0
    ) -> Optional[TaskResult]:
        """Synchronous version of wait_for_result."""
        return asyncio.run(self.wait_for_result(task_id, timeout, poll_interval))
    
    # Event methods
    async def get_task_events(self, task_id: str) -> List[TaskEvent]:
        """Get events for a specific task."""
        if not self._event_storage:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._event_storage.get_events(task_id=task_id)
    
    def get_task_events_sync(self, task_id: str) -> List[TaskEvent]:
        """Synchronous version of get_task_events."""
        return asyncio.run(self.get_task_events(task_id))
    
    # Scheduling methods
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
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.create_schedule(
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
        )
    
    def create_schedule_sync(
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
        """Synchronous version of create_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.create_schedule(
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
        )
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.get_schedule(schedule_id)
    
    def get_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Synchronous version of get_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.get_schedule(schedule_id)
    
    async def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.list_schedules(status, limit, offset)
    
    def list_schedules_sync(
        self,
        status: Optional[ScheduleStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """Synchronous version of list_schedules."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.list_schedules(status, limit, offset)
    
    async def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.pause_schedule(schedule_id)
    
    def pause_schedule_sync(self, schedule_id: str) -> bool:
        """Synchronous version of pause_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.pause_schedule(schedule_id)
    
    async def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.resume_schedule(schedule_id)
    
    def resume_schedule_sync(self, schedule_id: str) -> bool:
        """Synchronous version of resume_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.resume_schedule(schedule_id)
    
    async def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a schedule."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.cancel_schedule(schedule_id)
    
    def cancel_schedule_sync(self, schedule_id: str) -> bool:
        """Synchronous version of cancel_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.cancel_schedule(schedule_id)
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.delete_schedule(schedule_id)
    
    def delete_schedule_sync(self, schedule_id: str) -> bool:
        """Synchronous version of delete_schedule."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.delete_schedule(schedule_id)
    
    async def start_scheduler(self) -> None:
        """Start the scheduler engine."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        await self._async_scheduler.start()
    
    def start_scheduler_sync(self) -> None:
        """Synchronous version of start_scheduler."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        self._sync_scheduler.start()
    
    async def stop_scheduler(self) -> None:
        """Stop the scheduler engine."""
        if self._async_scheduler:
            await self._async_scheduler.stop()
    
    def stop_scheduler_sync(self) -> None:
        """Synchronous version of stop_scheduler."""
        if self._sync_scheduler:
            self._sync_scheduler.stop()
    
    async def recover_schedules(self) -> int:
        """Recover schedules after restart."""
        if not self._async_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._async_scheduler.recover_schedules()
    
    def recover_schedules_sync(self) -> int:
        """Synchronous version of recover_schedules."""
        if not self._sync_scheduler:
            raise RuntimeError("OmniQ not connected. Call connect_sync() first.")
        
        return self._sync_scheduler.recover_schedules()
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a function for scheduled execution."""
        if self._async_scheduler:
            self._async_scheduler.register_function(name, func)
        if self._sync_scheduler:
            self._sync_scheduler.register_function(name, func)
    
    def unregister_function(self, name: str) -> None:
        """Unregister a function."""
        if self._async_scheduler:
            self._async_scheduler.unregister_function(name)
        if self._sync_scheduler:
            self._sync_scheduler.unregister_function(name)
    
    # Task decorator
    def task(
        self,
        name: Optional[str] = None,
        queue: str = "default",
        priority: int = 0,
        retry_attempts: int = 3,
        retry_delay: Union[int, float, timedelta] = 1.0,
    ):
        """
        Decorator to register a function as a task.
        
        Args:
            name: Task name (defaults to function name)
            queue: Default queue for the task
            priority: Default priority
            retry_attempts: Default retry attempts
            retry_delay: Default retry delay
        """
        def decorator(func: Callable) -> Callable:
            task_name = name or func.__name__
            self._task_registry[task_name] = func
            
            # Add submission methods to the function
            async def submit(*args, **kwargs):
                return await self.submit_task(
                    func_name=task_name,
                    args=args,
                    kwargs=kwargs,
                    queue=queue,
                    priority=priority,
                    retry_attempts=retry_attempts,
                    retry_delay=retry_delay,
                )
            
            def submit_sync(*args, **kwargs):
                return self.submit_task_sync(
                    func_name=task_name,
                    args=args,
                    kwargs=kwargs,
                    queue=queue,
                    priority=priority,
                    retry_attempts=retry_attempts,
                    retry_delay=retry_delay,
                )
            
            # Store methods and metadata as attributes (type checker will complain but it works at runtime)
            setattr(func, 'submit', submit)
            setattr(func, 'submit_sync', submit_sync)
            setattr(func, 'task_name', task_name)
            
            return func
        
        return decorator
    
    def get_registered_task(self, name: str) -> Optional[Callable]:
        """Get a registered task function by name."""
        return self._task_registry.get(name)
    
    def list_registered_tasks(self) -> List[str]:
        """List all registered task names."""
        return list(self._task_registry.keys())
    
    # Queue management methods
    async def get_queue_statistics(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Get queue statistics."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._queue_manager.get_queue_statistics(queue_name)
    
    def get_queue_statistics_sync(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous version of get_queue_statistics."""
        return asyncio.run(self.get_queue_statistics(queue_name))
    
    async def move_task_between_queues(self, task_id: str, target_queue: str) -> bool:
        """Move a task from one queue to another."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._queue_manager.move_task_between_queues(task_id, target_queue)
    
    def move_task_between_queues_sync(self, task_id: str, target_queue: str) -> bool:
        """Synchronous version of move_task_between_queues."""
        return asyncio.run(self.move_task_between_queues(task_id, target_queue))
    
    def get_queue_config(self, queue_name: str) -> Optional['QueueConfig']:
        """Get configuration for a specific queue."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return self._queue_manager.get_queue_config(queue_name)
    
    def update_queue_config(self, queue_config: 'QueueConfig') -> None:
        """Update configuration for a queue."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        self._queue_manager.update_queue_config(queue_config)
    
    def list_queues(self) -> List[str]:
        """List all configured queue names."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return self._queue_manager.list_queues()
    
    async def cleanup_empty_queues(self) -> List[str]:
        """Clean up queues that have no tasks and haven't been active recently."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        return await self._queue_manager.cleanup_empty_queues()
    
    def cleanup_empty_queues_sync(self) -> List[str]:
        """Synchronous version of cleanup_empty_queues."""
        return asyncio.run(self.cleanup_empty_queues())
    
    def register_priority_algorithm(self, name: str, algorithm: Any) -> None:
        """Register a custom priority algorithm."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        self._queue_manager.register_priority_algorithm(name, algorithm)
    
    def register_custom_priority_function(self, name: str, func: Callable) -> None:
        """Register a custom priority function."""
        if not self._queue_manager:
            raise RuntimeError("OmniQ not connected. Call connect() first.")
        
        self._queue_manager.register_custom_priority_function(name, func)
    
    # Cleanup methods
    async def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired tasks and results."""
        if self.backend:
            # Legacy backend mode
            return await self.backend.cleanup_expired()
        else:
            # Independent storage backend mode - cleanup each component
            results = {}
            
            # Cleanup task queue
            if hasattr(self._task_queue, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._task_queue, 'cleanup_expired')
                    if asyncio.iscoroutinefunction(cleanup_method):
                        results['tasks'] = await cleanup_method()
                    else:
                        results['tasks'] = cleanup_method()
                except Exception as e:
                    logger.warning(f"Failed to cleanup task queue: {e}")
                    results['tasks'] = 0
            
            # Cleanup result storage
            if hasattr(self._result_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._result_storage, 'cleanup_expired')
                    if asyncio.iscoroutinefunction(cleanup_method):
                        results['results'] = await cleanup_method()
                    else:
                        results['results'] = cleanup_method()
                except Exception as e:
                    logger.warning(f"Failed to cleanup result storage: {e}")
                    results['results'] = 0
            
            # Cleanup event storage
            if hasattr(self._event_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._event_storage, 'cleanup_expired')
                    if asyncio.iscoroutinefunction(cleanup_method):
                        results['events'] = await cleanup_method()
                    else:
                        results['events'] = cleanup_method()
                except Exception as e:
                    logger.warning(f"Failed to cleanup event storage: {e}")
                    results['events'] = 0
            
            # Cleanup schedule storage
            if hasattr(self._schedule_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._schedule_storage, 'cleanup_expired')
                    if asyncio.iscoroutinefunction(cleanup_method):
                        results['schedules'] = await cleanup_method()
                    else:
                        results['schedules'] = cleanup_method()
                except Exception as e:
                    logger.warning(f"Failed to cleanup schedule storage: {e}")
                    results['schedules'] = 0
            
            return results
    
    def cleanup_expired_sync(self) -> Dict[str, int]:
        """Synchronous version of cleanup_expired."""
        if self.backend:
            # Legacy backend mode
            return self.backend.cleanup_expired_sync()
        else:
            # Independent storage backend mode - cleanup each component
            results = {}
            
            # Cleanup task queue
            if hasattr(self._task_queue, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._task_queue, 'cleanup_expired')
                    if not asyncio.iscoroutinefunction(cleanup_method):
                        results['tasks'] = cleanup_method()
                    else:
                        logger.warning("Storage component has async cleanup_expired method in sync mode")
                        results['tasks'] = 0
                except Exception as e:
                    logger.warning(f"Failed to cleanup task queue: {e}")
                    results['tasks'] = 0
            
            # Cleanup result storage
            if hasattr(self._result_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._result_storage, 'cleanup_expired')
                    if not asyncio.iscoroutinefunction(cleanup_method):
                        results['results'] = cleanup_method()
                    else:
                        logger.warning("Storage component has async cleanup_expired method in sync mode")
                        results['results'] = 0
                except Exception as e:
                    logger.warning(f"Failed to cleanup result storage: {e}")
                    results['results'] = 0
            
            # Cleanup event storage
            if hasattr(self._event_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._event_storage, 'cleanup_expired')
                    if not asyncio.iscoroutinefunction(cleanup_method):
                        results['events'] = cleanup_method()
                    else:
                        logger.warning("Storage component has async cleanup_expired method in sync mode")
                        results['events'] = 0
                except Exception as e:
                    logger.warning(f"Failed to cleanup event storage: {e}")
                    results['events'] = 0
            
            # Cleanup schedule storage
            if hasattr(self._schedule_storage, 'cleanup_expired'):
                try:
                    cleanup_method = getattr(self._schedule_storage, 'cleanup_expired')
                    if not asyncio.iscoroutinefunction(cleanup_method):
                        results['schedules'] = cleanup_method()
                    else:
                        logger.warning("Storage component has async cleanup_expired method in sync mode")
                        results['schedules'] = 0
                except Exception as e:
                    logger.warning(f"Failed to cleanup schedule storage: {e}")
                    results['schedules'] = 0
            
            return results
    
    # Context manager support
    @asynccontextmanager
    async def connection(self):
        """Async context manager for connection handling."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    @contextmanager
    def connection_sync(self):
        """Sync context manager for connection handling."""
        self.connect_sync()
        try:
            yield self
        finally:
            self.disconnect_sync()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()
    
    def __repr__(self) -> str:
        """String representation of OmniQ instance."""
        if self.backend:
            return f"OmniQ(backend={self.backend})"
        else:
            return f"OmniQ(independent_storage=True)"