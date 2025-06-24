"""AsyncTaskQueue: Asynchronous task queue implementation for OmniQ."""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Callable
from collections import deque
from datetime import datetime

from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.serialization.manager import SerializationManager
from omniq.storage.base import BaseTaskStorage, BaseResultStorage
from omniq.workers.factory import WorkerFactory
from omniq.events.logger import EventLogger
from omniq.events.types import EventType

logger = logging.getLogger(__name__)

class AsyncTaskQueue:
    """Asynchronous task queue implementation for OmniQ."""
    
    def __init__(
        self,
        task_storage: BaseTaskStorage,
        result_storage: BaseResultStorage,
        worker_type: str = "async",
        max_workers: int = 10,
        task_timeout: Optional[float] = None,
        task_ttl: Optional[float] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize the async task queue.
        
        Args:
            task_storage (BaseTaskStorage): Storage backend for tasks.
            result_storage (BaseResultStorage): Storage backend for results.
            worker_type (str): Type of worker to use (async, thread, process, gevent).
            max_workers (int): Maximum number of workers.
            task_timeout (Optional[float]): Default task execution timeout in seconds.
            task_ttl (Optional[float]): Default time-to-live for tasks in seconds.
            retry_attempts (int): Default number of retry attempts for failed tasks.
            retry_delay (float): Default delay between retries in seconds.
        """
        self.task_storage = task_storage
        self.result_storage = result_storage
        self.worker_pool = WorkerFactory.create_worker(worker_type, max_tasks=max_workers)
        self.task_timeout = task_timeout
        self.task_ttl = task_ttl
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.serialization_manager = SerializationManager()
        self.event_logger = EventLogger()
        self.running = False
        self.pending_tasks: deque[Task] = deque()
        self.processing_tasks: Dict[str, Task] = {}
        
    async def start(self) -> None:
        """Start the task queue and worker pool."""
        if self.running:
            logger.warning("Task queue is already running.")
            return
            
        self.running = True
        await self.worker_pool.start()
        asyncio.create_task(self._process_tasks())
        logger.info("Task queue started with %d workers.", self.worker_pool.max_workers)
        
    async def stop(self) -> None:
        """Stop the task queue and perform graceful shutdown."""
        if not self.running:
            logger.warning("Task queue is not running.")
            return
            
        self.running = False
        await self.worker_pool.shutdown()
        logger.info("Task queue stopped.")
        
    async def enqueue(
        self,
        func: Callable,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        callbacks: Optional[List[Callable]] = None,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ) -> str:
        """Enqueue a task for execution.
        
        Args:
            func (callable): The function to execute.
            args (Optional[Tuple]): Positional arguments for the function.
            kwargs (Optional[Dict[str, Any]]): Keyword arguments for the function.
            dependencies (Optional[List[str]]): List of task IDs this task depends on.
            callbacks (Optional[List[callable]]): List of callback functions to execute after task completion.
            task_id (Optional[str]): Custom task ID. If not provided, a UUID will be generated.
            timeout (Optional[float]): Task-specific timeout in seconds.
            ttl (Optional[float]): Task-specific time-to-live in seconds.
            
        Returns:
            str: The ID of the enqueued task.
        """
        args = args or ()
        kwargs = kwargs or {}
        dependencies = dependencies or []
        callbacks = callbacks or []
        timeout = timeout if timeout is not None else self.task_timeout
        ttl = ttl if ttl is not None else self.task_ttl
        
        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            dependencies=dependencies,
            callbacks=callbacks,
            id=task_id if task_id is not None else str(uuid.uuid4()),
            timeout=timeout,
            ttl=ttl,
            created_at=datetime.now(),
            status="pending"
        )
        
        await self.task_storage.store_task_async(task)
        self.pending_tasks.append(task)
        await self.event_logger.log_event(EventType.ENQUEUED, task.id, {"created_at": task.created_at.isoformat()})
        logger.debug("Task %s enqueued.", task.id)
        return task.id
        
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Retrieve the result of a task.
        
        Args:
            task_id (str): The ID of the task.
            timeout (Optional[float]): Maximum time to wait for the result in seconds.
            
        Returns:
            Optional[TaskResult]: The result of the task if available, None otherwise.
        """
        result = await self.result_storage.get_result_async(task_id)
        return result
        
    async def _process_tasks(self) -> None:
        """Process tasks from the pending queue."""
        while self.running:
            if not self.pending_tasks:
                await asyncio.sleep(0.1)
                continue
                
            task = await self._get_next_eligible_task()
            if task is None:
                await asyncio.sleep(0.1)
                continue
                
            self.pending_tasks.remove(task)
            self.processing_tasks[task.id] = task
            task.status = "running"
            task.started_at = datetime.now()
            await self.event_logger.log_event(EventType.EXECUTING, task.id, {"started_at": task.started_at.isoformat()})
            asyncio.create_task(self._execute_task(task))
            
    async def _get_next_eligible_task(self) -> Optional[Task]:
        """Get the next task that is eligible for execution based on dependencies.
        
        Returns:
            Optional[Task]: The next eligible task, or None if no tasks are eligible.
        """
        for task in self.pending_tasks:
            if await self._are_dependencies_met(task):
                return task
        return None
        
    async def _are_dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies of a task are completed.
        
        Args:
            task (Task): The task to check.
            
        Returns:
            bool: True if all dependencies are met, False otherwise.
        """
        for dep_id in task.dependencies:
            if dep_id not in self.processing_tasks and not await self._is_task_completed(dep_id):
                return False
        return True
        
    async def _is_task_completed(self, task_id: str) -> bool:
        """Check if a task is completed by checking result storage.
        
        Args:
            task_id (str): The ID of the task.
            
        Returns:
            bool: True if the task is completed, False otherwise.
        """
        result = await self.result_storage.get_result_async(task_id)
        return result is not None
        
    async def _execute_task(self, task: Task) -> None:
        """Execute a task using the worker pool.
        
        Args:
            task (Task): The task to execute.
        """
        try:
            logger.debug("Executing task %s", task.id)
            result_value = await self.worker_pool.execute_task(task)
            result = TaskResult(
                task_id=task.id,
                status="success",
                result=result_value,
                completed_at=datetime.now()
            )
            await self._handle_task_completion(task, result)
        except Exception as e:
            logger.error("Task %s failed with error: %s", task.id, str(e))
            await self._handle_task_failure(task, e)
            
    async def _handle_task_completion(self, task: Task, result: TaskResult) -> None:
        """Handle task completion, store result, and execute callbacks.
        
        Args:
            task (Task): The completed task.
            result (TaskResult): The result of the task.
        """
        await self.result_storage.store_result_async(result)
        await self.event_logger.log_event(EventType.COMPLETE, task.id, {"completed_at": result.completed_at.isoformat()})
        task.status = "completed"
        task.completed_at = datetime.now()
        
        for callback in task.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error("Callback for task %s failed: %s", task.id, str(e))
                
        del self.processing_tasks[task.id]
        logger.debug("Task %s completed successfully.", task.id)
        
    async def _handle_task_failure(self, task: Task, error: Exception) -> None:
        """Handle task failure, implement retry logic.
        
        Args:
            task (Task): The failed task.
            error (Exception): The exception raised during execution.
        """
        task.retry_count = getattr(task, 'retry_count', 0) + 1
        if task.retry_count <= self.retry_attempts:
            delay = self.retry_delay * (2 ** (task.retry_count - 1))
            logger.info("Retrying task %s (attempt %d/%d) after delay of %.2f seconds.", 
                       task.id, task.retry_count, self.retry_attempts, delay)
            await self.event_logger.log_event(EventType.RETRY, task.id, {"attempt": task.retry_count, "max_attempts": self.retry_attempts})
            await asyncio.sleep(delay)
            task.status = "pending"
            self.pending_tasks.append(task)
        else:
            result = TaskResult(
                task_id=task.id,
                status="error",
                error=str(error),
                completed_at=datetime.now()
            )
            await self.result_storage.store_result_async(result)
            await self.event_logger.log_event(EventType.ERROR, task.id, {"error": str(error)})
            task.status = "failed"
            task.completed_at = datetime.now()
            logger.error("Task %s failed after %d attempts: %s", task.id, task.retry_count, str(error))
            
        del self.processing_tasks[task.id]
