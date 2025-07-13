"""ProcessWorker - Process pool-based task execution."""

from __future__ import annotations

import asyncio
import inspect
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Optional

from .base import BaseWorker, resolve_function
from ..models.result import TaskResult
from ..models.task import Task


def _execute_task_in_process(task_data: dict) -> Any:
    """
    Execute task in separate process.
    
    This function must be at module level to be pickeable.
    """
    import asyncio
    
    # Extract task data
    func_path = task_data["func"]
    args = task_data["args"]
    kwargs = task_data["kwargs"]
    timeout = task_data.get("timeout")
    
    # Resolve function
    if isinstance(func_path, str):
        func = resolve_function(func_path)
    else:
        # For callable objects, we need special handling
        func = func_path
    
    # Execute based on function type
    if inspect.iscoroutinefunction(func):
        # Async function - run in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            coro = func(*args, **kwargs)
            if timeout:
                return loop.run_until_complete(
                    asyncio.wait_for(coro, timeout=timeout)
                )
            else:
                return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # Sync function - execute directly
        return func(*args, **kwargs)


class ProcessWorker(BaseWorker):
    """Worker that executes tasks using a process pool."""
    
    def __init__(
        self,
        *args,
        max_workers: int = 4,
        initializer: Optional[Callable] = None,
        initargs: tuple = (),
        **kwargs
    ):
        """
        Initialize process worker.
        
        Args:
            max_workers: Maximum number of worker processes
            initializer: Optional function to run in each worker process on startup
            initargs: Arguments for initializer function
        """
        super().__init__(*args, **kwargs)
        self.max_workers = max_workers
        self.initializer = initializer
        self.initargs = initargs
        self._executor: Optional[ProcessPoolExecutor] = None
    
    @property
    def worker_type(self) -> str:
        """Get worker type identifier."""
        return "process"
    
    async def start(self) -> None:
        """Start the worker and process pool."""
        self._executor = ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=self.initializer,
            initargs=self.initargs
        )
        await super().start()
    
    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker and shutdown process pool."""
        await super().stop(timeout)
        
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task in process pool."""
        if not self._executor:
            raise RuntimeError("ProcessWorker not started")
        
        start_time = time.time()
        
        try:
            # Prepare task data for process execution
            task_data = {
                "func": task.func,
                "args": task.args,
                "kwargs": task.kwargs,
                "timeout": task.timeout,
            }
            
            # Validate that function is serializable
            if not isinstance(task.func, str) and not self._is_serializable(task.func):
                raise ValueError(
                    f"Function {task.func} is not serializable for process execution. "
                    "Use string function path instead."
                )
            
            # Submit to process pool
            loop = asyncio.get_event_loop()
            future = self._executor.submit(_execute_task_in_process, task_data)
            
            # Handle timeout at process level
            timeout = task.timeout or None
            if timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, future.result, timeout),
                    timeout=timeout
                )
            else:
                result = await loop.run_in_executor(None, future.result)
            
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
    
    def _is_serializable(self, obj: Any) -> bool:
        """Check if object is serializable (pickle-able)."""
        import pickle
        
        try:
            pickle.dumps(obj)
            return True
        except (pickle.PicklingError, TypeError):
            return False
    
    async def health_check(self) -> dict:
        """Get health check including process pool status."""
        base_health = await super().health_check()
        
        if self._executor:
            # Get process pool statistics
            base_health.update({
                "max_workers": self.max_workers,
                "executor_shutdown": self._executor._shutdown,
                "initializer": str(self.initializer) if self.initializer else None,
            })
        
        return base_health