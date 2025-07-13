"""AsyncWorker - Native async task execution."""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any, Callable

from .base import BaseWorker, resolve_function
from ..models.result import TaskResult
from ..models.task import Task


class AsyncWorker(BaseWorker):
    """Worker that executes tasks natively in async context."""
    
    @property
    def worker_type(self) -> str:
        """Get worker type identifier."""
        return "async"
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task asynchronously."""
        start_time = time.time()
        
        try:
            # Resolve function
            if isinstance(task.func, str):
                func = resolve_function(task.func)
            else:
                func = task.func
            
            # Handle timeout
            timeout = task.timeout or None
            
            # Execute function
            if inspect.iscoroutinefunction(func):
                # Async function
                result = await self._execute_async_func(func, task, timeout)
            else:
                # Sync function - run in thread pool
                result = await self._execute_sync_func(func, task, timeout)
            
            return TaskResult.success(
                task_id=task.id,
                result=result,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
            
        except asyncio.TimeoutError:
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
    
    async def _execute_async_func(
        self,
        func: Callable,
        task: Task,
        timeout: float = None
    ) -> Any:
        """Execute async function with timeout."""
        coro = func(*task.args, **task.kwargs)
        
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        else:
            return await coro
    
    async def _execute_sync_func(
        self,
        func: Callable,
        task: Task,
        timeout: float = None
    ) -> Any:
        """Execute sync function in thread pool with timeout."""
        loop = asyncio.get_event_loop()
        
        # Run in thread pool
        future = loop.run_in_executor(
            None,  # Use default executor
            lambda: func(*task.args, **task.kwargs)
        )
        
        if timeout:
            return await asyncio.wait_for(future, timeout=timeout)
        else:
            return await future