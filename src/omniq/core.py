"""Core OmniQ implementation.

This module provides the main entry points for the OmniQ library:
- AsyncOmniQ: Async-first implementation for high-performance applications
- OmniQ: Synchronous wrapper for traditional blocking applications

Both classes orchestrate task queues, result storage, event storage, and workers.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path

# Remove anyio import since we'll use asyncio.run instead

from .models.task import Task
from .models.result import TaskResult, TaskStatus
from .models.event import TaskEvent, TaskEventType
from .models.config import OmniQConfig
from .results.base import BaseResultStorage
from .queue.base import BaseQueue
from .queue.scheduler import AsyncScheduler
from .queue.dependency import DependencyResolver
from .events.base import BaseEventStorage
from .config import env, loader
from .cleanup import CleanupManager


class AsyncOmniQ:
    """Async-first OmniQ implementation.
    
    This class provides the main asynchronous interface for OmniQ, orchestrating
    task queues, result storage, event storage, and workers. It supports:
    - Task enqueuing and scheduling
    - Result retrieval
    - Worker management
    - Context manager support
    """
    
    def __init__(
        self,
        task_queue: Optional[BaseQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        worker: Optional[Any] = None,
        project_name: str = "omniq",
        config: Optional[OmniQConfig] = None
    ):
        """Initialize AsyncOmniQ.
        
        Args:
            task_queue: Task queue implementation
            result_storage: Result storage implementation
            event_storage: Event storage implementation (optional)
            worker: Worker implementation (optional)
            project_name: Name of the project
            config: Configuration object
        """
        self.project_name = project_name
        self.config = config or OmniQConfig(project_name=project_name)
        
        # Store components
        self.task_queue = task_queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.worker = worker
        
        # Initialize scheduler if task queue is available
        self.scheduler: Optional[AsyncScheduler] = None
        if self.task_queue is not None:
            self.scheduler = AsyncScheduler(self.task_queue)
        
        # Initialize dependency resolver if result storage is available
        self.dependency_resolver: Optional[DependencyResolver] = None
        if self.result_storage is not None:
            self.dependency_resolver = DependencyResolver(
                result_storage=self.result_storage,
                event_storage=self.event_storage
            )
        
        # Initialize cleanup manager
        self.cleanup_manager: Optional[CleanupManager] = None
        if self.task_queue is not None or self.result_storage is not None or self.event_storage is not None:
            if self.config.cleanup is not None:
                cleanup_config = self.config.cleanup
                self.cleanup_manager = CleanupManager(
                    queue=self.task_queue,
                    result_storage=self.result_storage,
                    event_storage=self.event_storage,
                    cleanup_interval=cleanup_config.interval,
                    task_cleanup_enabled=cleanup_config.task_cleanup_enabled,
                    result_cleanup_enabled=cleanup_config.result_cleanup_enabled,
                    event_cleanup_enabled=cleanup_config.event_cleanup_enabled
                )
            else:
                # Use default cleanup configuration
                self.cleanup_manager = CleanupManager(
                    queue=self.task_queue,
                    result_storage=self.result_storage,
                    event_storage=self.event_storage
                )
        
        # Worker management
        self._worker_task: Optional[asyncio.Task] = None
        self._worker_running = False
    
    @classmethod
    async def from_config(cls, config: OmniQConfig) -> "AsyncOmniQ":
        """Create AsyncOmniQ instance from configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Configured AsyncOmniQ instance
        """
        # This would create components based on config
        # For now, return basic instance
        return cls(config=config, project_name=config.project_name)
    
    @classmethod
    async def from_dict(cls, config_dict: Dict[str, Any]) -> "AsyncOmniQ":
        """Create AsyncOmniQ instance from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configured AsyncOmniQ instance
        """
        config_dict = loader.from_dict(config_dict)
        config = OmniQConfig(**config_dict)
        return await cls.from_config(config)
    
    @classmethod
    async def from_yaml(cls, config_path: Union[str, Path]) -> "AsyncOmniQ":
        """Create AsyncOmniQ instance from YAML configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configured AsyncOmniQ instance
        """
        config_dict = loader.from_yaml(config_path)
        config = OmniQConfig(**config_dict)
        return await cls.from_config(config)
    
    async def enqueue(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        task_id: Optional[uuid.UUID] = None,
        ttl: Optional[timedelta] = None,
        run_at: Optional[datetime] = None,
        run_in: Optional[timedelta] = None
    ) -> uuid.UUID:
        """Enqueue a task for execution.
        
        Args:
            func: Function to execute (callable or string name)
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add the task to
            task_id: Optional task ID (generated if not provided)
            ttl: Time-to-live for the task
            run_at: Specific time to run the task
            run_in: Delay before running the task
            
        Returns:
            Task ID
            
        Raises:
            ValueError: If task queue is not configured
        """
        if self.task_queue is None:
            raise ValueError("Task queue not configured")
        
        # Generate task ID if not provided
        if task_id is None:
            task_id = uuid.uuid4()
        
        # Determine function name
        if callable(func):
            func_name = f"{func.__module__}.{func.__name__}"
        else:
            func_name = str(func)
        
        # Calculate run time
        created_at = datetime.utcnow()
        if run_at is not None:
            # Use specific time
            pass
        elif run_in is not None:
            # Calculate from delay
            run_at = created_at + run_in
        else:
            # Run immediately
            run_at = created_at
        
        # Use default TTL from config if not provided
        if ttl is None and self.config.task_ttl > 0:
            ttl = timedelta(seconds=self.config.task_ttl)
        
        # Create task
        task = Task(
            id=task_id,
            func_name=func_name,
            args=func_args or (),
            kwargs=func_kwargs or {},
            created_at=created_at,
            ttl=ttl
        )
        
        # Handle task dependencies if dependency resolver is available
        if self.dependency_resolver is not None and task.dependencies:
            enqueued_immediately = await self.dependency_resolver.add_task_with_dependencies(
                task, self.task_queue, queue_name
            )
            if not enqueued_immediately:
                # Task is waiting for dependencies
                return task_id
        else:
            # Enqueue the task directly
            await self.task_queue.enqueue_async(task, queue_name)
        
        # Log enqueue event if event storage is available
        if self.event_storage is not None:
            event = TaskEvent(
                task_id=task_id,
                event_type=TaskEventType.ENQUEUED,
                timestamp=created_at
            )
            await self.event_storage.log_event_async(event)
        
        return task_id
    
    async def get_result(
        self,
        task_id: uuid.UUID,
        timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0
    ) -> Optional[TaskResult]:
        """Get the result of a task.
        
        Args:
            task_id: ID of the task
            timeout: Maximum time to wait for result
            poll_interval: Interval between result checks
            
        Returns:
            Task result or None if not found/timeout
            
        Raises:
            ValueError: If result storage is not configured
        """
        if self.result_storage is None:
            raise ValueError("Result storage not configured")
        
        start_time = datetime.utcnow()
        
        while True:
            result = await self.result_storage.get_result_async(task_id)
            
            if result is not None:
                return result
            
            # Check timeout
            if timeout is not None:
                elapsed = datetime.utcnow() - start_time
                if elapsed >= timeout:
                    return None
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def schedule(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        interval: Optional[timedelta] = None,
        cron: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None
    ) -> uuid.UUID:
        """Schedule a recurring task.
        
        Args:
            func: Function to execute
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add tasks to
            interval: Interval between executions
            cron: Cron expression for scheduling
            start_at: When to start the schedule
            end_at: When to end the schedule (optional)
            
        Returns:
            Schedule ID
            
        Raises:
            ValueError: If scheduler is not configured
        """
        if self.scheduler is None:
            raise ValueError("Scheduler not configured - task queue must be provided")
        
        return await self.scheduler.add_schedule(
            func=func,
            func_args=func_args,
            func_kwargs=func_kwargs,
            queue_name=queue_name,
            interval=interval,
            cron=cron,
            start_at=start_at,
            end_at=end_at
        )
    
    async def start_worker(self) -> None:
        """Start the worker to process tasks.
        
        Raises:
            ValueError: If worker is not configured
            RuntimeError: If worker is already running
        """
        if self.worker is None:
            raise ValueError("Worker not configured")
        
        if self._worker_running:
            raise RuntimeError("Worker is already running")
        
        self._worker_running = True
        # Check if worker.start is a coroutine function
        if asyncio.iscoroutinefunction(self.worker.start):
            self._worker_task = asyncio.create_task(self.worker.start())
        else:
            # For synchronous workers, run start in a separate thread to avoid blocking
            self._worker_task = asyncio.create_task(
                asyncio.to_thread(self.worker.start)
            )
    
    async def stop_worker(self) -> None:
        """Stop the worker gracefully."""
        if not self._worker_running or self.worker is None:
            return
        
        self._worker_running = False
        await self.worker.stop()
        
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
    
    async def get_queue_size(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue.
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Number of pending tasks
            
        Raises:
            ValueError: If task queue is not configured
        """
        if self.task_queue is None:
            raise ValueError("Task queue not configured")
        
        return await self.task_queue.get_queue_size_async(queue_name)
    
    async def list_queues(self) -> List[str]:
        """List all available queue names.
        
        Returns:
            List of queue names
            
        Raises:
            ValueError: If task queue is not configured
        """
        if self.task_queue is None:
            raise ValueError("Task queue not configured")
        
        return await self.task_queue.list_queues_async()
    
    async def start_scheduler(self) -> None:
        """Start the scheduler to process recurring tasks.
        
        Raises:
            ValueError: If scheduler is not configured
            RuntimeError: If scheduler is already running
        """
        if self.scheduler is None:
            raise ValueError("Scheduler not configured")
        
        await self.scheduler.start()
    
    async def stop_scheduler(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler is not None:
            await self.scheduler.stop()
    
    async def start_cleanup(self) -> None:
        """Start the cleanup manager to periodically clean up expired tasks and results.
        
        Raises:
            ValueError: If cleanup manager is not configured
        """
        if self.cleanup_manager is None:
            raise ValueError("Cleanup manager not configured")
        
        await self.cleanup_manager.start()
    
    async def stop_cleanup(self) -> None:
        """Stop the cleanup manager gracefully."""
        if self.cleanup_manager is not None:
            await self.cleanup_manager.stop()
    
    async def run_cleanup_now(self) -> Dict[str, int]:
        """Run cleanup immediately without waiting for the next scheduled cycle.
        
        Returns:
            Dictionary with cleanup counts for each component
            
        Raises:
            ValueError: If cleanup manager is not configured
        """
        if self.cleanup_manager is None:
            raise ValueError("Cleanup manager not configured")
        
        return await self.cleanup_manager.run_cleanup_now()
    
    async def __aenter__(self) -> "AsyncOmniQ":
        """Async context manager entry."""
        # Initialize components if needed
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # Stop worker if running
        await self.stop_worker()
        
        # Stop scheduler if running
        await self.stop_scheduler()
        
        # Stop cleanup manager if running
        await self.stop_cleanup()
        
        # Clean up resources
        # Components should handle their own cleanup


class OmniQ:
    """Synchronous wrapper around AsyncOmniQ.
    
    This class provides a blocking interface for OmniQ, wrapping the async
    implementation to provide a traditional synchronous API.
    """
    
    def __init__(
        self,
        task_queue: Optional[BaseQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        worker: Optional[Any] = None,
        project_name: str = "omniq",
        config: Optional[OmniQConfig] = None
    ):
        """Initialize OmniQ.
        
        Args:
            task_queue: Task queue implementation
            result_storage: Result storage implementation
            event_storage: Event storage implementation (optional)
            worker: Worker implementation (optional)
            project_name: Name of the project
            config: Configuration object
        """
        self._async_omniq = AsyncOmniQ(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            worker=worker,
            project_name=project_name,
            config=config
        )
    
    @classmethod
    def from_config(cls, config: OmniQConfig) -> "OmniQ":
        """Create OmniQ instance from configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Configured OmniQ instance
        """
        async_omniq = asyncio.run(AsyncOmniQ.from_config(config))
        instance = cls.__new__(cls)
        instance._async_omniq = async_omniq
        return instance
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "OmniQ":
        """Create OmniQ instance from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configured OmniQ instance
        """
        async_omniq = asyncio.run(AsyncOmniQ.from_dict(config_dict))
        instance = cls.__new__(cls)
        instance._async_omniq = async_omniq
        return instance
    
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "OmniQ":
        """Create OmniQ instance from YAML configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configured OmniQ instance
        """
        async_omniq = asyncio.run(AsyncOmniQ.from_yaml(config_path))
        instance = cls.__new__(cls)
        instance._async_omniq = async_omniq
        return instance
    
    def enqueue(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        task_id: Optional[uuid.UUID] = None,
        ttl: Optional[timedelta] = None,
        run_at: Optional[datetime] = None,
        run_in: Optional[timedelta] = None
    ) -> uuid.UUID:
        """Enqueue a task for execution (synchronous).
        
        Args:
            func: Function to execute (callable or string name)
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add the task to
            task_id: Optional task ID (generated if not provided)
            ttl: Time-to-live for the task
            run_at: Specific time to run the task
            run_in: Delay before running the task
            
        Returns:
            Task ID
        """
        return asyncio.run(
            self._async_omniq.enqueue(
                func, func_args, func_kwargs, queue_name, task_id, ttl, run_at, run_in
            )
        )
    
    def get_result(
        self,
        task_id: uuid.UUID,
        timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0
    ) -> Optional[TaskResult]:
        """Get the result of a task (synchronous).
        
        Args:
            task_id: ID of the task
            timeout: Maximum time to wait for result
            poll_interval: Interval between result checks
            
        Returns:
            Task result or None if not found/timeout
        """
        return asyncio.run(
            self._async_omniq.get_result(task_id, timeout, poll_interval)
        )
    
    def schedule(
        self,
        func: Union[Callable, str],
        func_args: Optional[tuple] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        interval: Optional[timedelta] = None,
        cron: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None
    ) -> uuid.UUID:
        """Schedule a recurring task (synchronous).
        
        Args:
            func: Function to execute
            func_args: Positional arguments for the function
            func_kwargs: Keyword arguments for the function
            queue_name: Name of the queue to add tasks to
            interval: Interval between executions
            cron: Cron expression for scheduling
            start_at: When to start the schedule
            end_at: When to end the schedule (optional)
            
        Returns:
            Schedule ID
        """
        return asyncio.run(
            self._async_omniq.schedule(
                func, func_args, func_kwargs, queue_name, interval, cron, start_at, end_at
            )
        )
    
    def start_scheduler(self) -> None:
        """Start the scheduler to process recurring tasks (synchronous)."""
        asyncio.run(self._async_omniq.start_scheduler())
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler gracefully (synchronous)."""
        asyncio.run(self._async_omniq.stop_scheduler())
    
    def start_cleanup(self) -> None:
        """Start the cleanup manager to periodically clean up expired tasks and results (synchronous)."""
        asyncio.run(self._async_omniq.start_cleanup())
    
    def stop_cleanup(self) -> None:
        """Stop the cleanup manager gracefully (synchronous)."""
        asyncio.run(self._async_omniq.stop_cleanup())
    
    def run_cleanup_now(self) -> Dict[str, int]:
        """Run cleanup immediately without waiting for the next scheduled cycle (synchronous).
        
        Returns:
            Dictionary with cleanup counts for each component
        """
        return asyncio.run(self._async_omniq.run_cleanup_now())
    
    def start_worker(self) -> None:
        """Start the worker to process tasks (synchronous)."""
        asyncio.run(self._async_omniq.start_worker())
    
    def stop_worker(self) -> None:
        """Stop the worker gracefully (synchronous)."""
        asyncio.run(self._async_omniq.stop_worker())
    
    def get_queue_size(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue (synchronous).
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Number of pending tasks
        """
        return asyncio.run(self._async_omniq.get_queue_size(queue_name))
    
    def list_queues(self) -> List[str]:
        """List all available queue names (synchronous).
        
        Returns:
            List of queue names
        """
        return asyncio.run(self._async_omniq.list_queues())
    
    def __enter__(self) -> "OmniQ":
        """Synchronous context manager entry."""
        asyncio.run(self._async_omniq.__aenter__())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Synchronous context manager exit."""
        asyncio.run(self._async_omniq.__aexit__(exc_type, exc_val, exc_tb))