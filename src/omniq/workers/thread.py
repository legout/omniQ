"""ThreadWorker - Thread pool-based task execution."""

from __future__ import annotations

import asyncio
import inspect
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Optional

from .base import BaseWorker, resolve_function
from ..models.result import TaskResult
from ..models.task import Task


class ThreadWorker(BaseWorker):
    """Worker that executes tasks using a thread pool."""
    
    def __init__(
        self,
        *args,
        max_workers: int = 4,
        thread_name_prefix: str = "omniq-thread",
        **kwargs
    ):
        """
        Initialize thread worker.
        
        Args:
            max_workers: Maximum number of worker threads
            thread_name_prefix: Prefix for thread names
        """
        super().__init__(*args, **kwargs)
        self.max_workers = max_workers
        self.thread_name_prefix = thread_name_prefix
        self._executor: Optional[ThreadPoolExecutor] = None
    
    @property
    def worker_type(self) -> str:
        """Get worker type identifier."""
        return "thread"
    
    async def start(self) -> None:
        """Start the worker and thread pool."""
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.thread_name_prefix
        )
        await super().start()
    
    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker and shutdown thread pool."""
        await super().stop(timeout)
        
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task in thread pool."""
        if not self._executor:
            raise RuntimeError("ThreadWorker not started")
        
        start_time = time.time()
        
        try:
            # Resolve function
            if isinstance(task.func, str):
                func = resolve_function(task.func)
            else:
                func = task.func
            
            # Handle timeout
            timeout = task.timeout or None
            
            # Execute function based on type
            if inspect.iscoroutinefunction(func):
                # Async function - run in new event loop in thread
                result = await self._execute_async_func_in_thread(func, task, timeout)
            else:
                # Sync function - run directly in thread
                result = await self._execute_sync_func_in_thread(func, task, timeout)
            
            return TaskResult.success(
                task_id=task.id,
                result=result,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
            
        except (asyncio.TimeoutError, FutureTimeoutError):
            return TaskResult.timeout(
                task_id=task.id,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
        except Exception as e:
            return TaskResult.failure(
                task_id=task.id,
                error=e,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
    
    async def _execute_sync_func_in_thread(
        self,
        func: Callable,
        task: Task,
        timeout: Optional[float] = None
    ) -> Any:
        """Execute sync function in thread pool."""
        loop = asyncio.get_event_loop()
        
        future = self._executor.submit(func, *task.args, **task.kwargs)
        
        if timeout:
            return await asyncio.wait_for(
                loop.run_in_executor(None, future.result, timeout),
                timeout=timeout
            )
        else:
            return await loop.run_in_executor(self._executor, future.result)
    
    async def _execute_async_func_in_thread(
        self,
        func: Callable,
        task: Task,
        timeout: Optional[float] = None
    ) -> Any:
        """Execute async function in new event loop in thread."""
        def run_async_in_thread():
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                coro = func(*task.args, **task.kwargs)
                if timeout:
                    return loop.run_until_complete(
                        asyncio.wait_for(coro, timeout=timeout)
                    )
                else:
                    return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        # Run the async function in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, run_async_in_thread)
    
    async def health_check(self) -> dict:
        """Get health check including thread pool status."""
        base_health = await super().health_check()
        
        if self._executor:
            # Get thread pool statistics
            base_health.update({
                "max_workers": self.max_workers,
                "thread_name_prefix": self.thread_name_prefix,
                "executor_shutdown": self._executor._shutdown,
            })
        
        return base_health