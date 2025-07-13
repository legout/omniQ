"""GeventWorker - Gevent-based task execution (optional)."""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Optional

try:
    import gevent
    import gevent.pool
    from gevent import Timeout
    GEVENT_AVAILABLE = True
except ImportError:
    GEVENT_AVAILABLE = False
    gevent = None

from .base import BaseWorker, resolve_function
from ..models.result import TaskResult
from ..models.task import Task


class GeventWorker(BaseWorker):
    """Worker that executes tasks using gevent green threads."""
    
    def __init__(
        self,
        *args,
        pool_size: int = 100,
        **kwargs
    ):
        """
        Initialize gevent worker.
        
        Args:
            pool_size: Size of gevent pool
        """
        if not GEVENT_AVAILABLE:
            raise ImportError(
                "gevent is not available. Install with: pip install gevent"
            )
        
        super().__init__(*args, **kwargs)
        self.pool_size = pool_size
        self._pool: Optional[gevent.pool.Pool] = None
    
    @property
    def worker_type(self) -> str:
        """Get worker type identifier."""
        return "gevent"
    
    async def start(self) -> None:
        """Start the worker and gevent pool."""
        if not GEVENT_AVAILABLE:
            raise RuntimeError("gevent is not available")
        
        self._pool = gevent.pool.Pool(self.pool_size)
        await super().start()
    
    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker and gevent pool."""
        await super().stop(timeout)
        
        if self._pool:
            self._pool.kill(timeout=timeout)
            self._pool = None
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task using gevent."""
        if not self._pool:
            raise RuntimeError("GeventWorker not started")
        
        start_time = time.time()
        
        try:
            # Resolve function
            if isinstance(task.func, str):
                func = resolve_function(task.func)
            else:
                func = task.func
            
            # Gevent doesn't handle async functions well, 
            # so we'll convert them to sync using asyncio
            if inspect.iscoroutinefunction(func):
                func = self._wrap_async_func(func)
            
            # Execute in gevent pool with timeout
            timeout = task.timeout or None
            
            if timeout:
                with Timeout(timeout):
                    greenlet = self._pool.spawn(func, *task.args, **task.kwargs)
                    result = greenlet.get()
            else:
                greenlet = self._pool.spawn(func, *task.args, **task.kwargs)
                result = greenlet.get()
            
            return TaskResult.success(
                task_id=task.id,
                result=result,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
            
        except Timeout:
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
    
    def _wrap_async_func(self, async_func: Callable) -> Callable:
        """Wrap async function to run in sync context."""
        def sync_wrapper(*args, **kwargs):
            import asyncio
            
            # Try to get current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we need to run in new thread
                    import concurrent.futures
                    
                    def run_in_new_loop():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                async_func(*args, **kwargs)
                            )
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result()
                else:
                    # Loop exists but not running
                    return loop.run_until_complete(async_func(*args, **kwargs))
            except RuntimeError:
                # No event loop, create new one
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    loop.close()
        
        return sync_wrapper
    
    async def health_check(self) -> dict:
        """Get health check including gevent pool status."""
        base_health = await super().health_check()
        
        if self._pool:
            base_health.update({
                "pool_size": self.pool_size,
                "greenlets_active": len(self._pool),
                "pool_free_count": self._pool.free_count(),
            })
        
        return base_health


# Make GeventWorker available only if gevent is installed
__all__ = ["GeventWorker"] if GEVENT_AVAILABLE else []