"""
Tests for ThreadPoolWorker implementation.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from omniq.workers.thread_pool_worker import ThreadPoolWorker
from omniq.workers.pool import WorkerPool, WorkerType
from omniq.models.task import Task
from omniq.models.result import TaskResult, ResultStatus
from omniq.storage.sqlite import AsyncSQLiteQueue, AsyncSQLiteResultStorage, AsyncSQLiteEventStorage


@pytest.fixture
def function_registry():
    """Create a function registry for testing."""
    def sync_add(a, b):
        return a + b
    
    def io_task(delay):
        import time
        time.sleep(delay)
        return f"IO task completed after {delay}s"
    
    def cpu_intensive_task(n):
        # Simple CPU-intensive task
        result = 0
        for i in range(n * 1000):
            result += i
        return result
    
    return {
        "sync_add": sync_add,
        "io_task": io_task,
        "cpu_intensive_task": cpu_intensive_task,
    }


@pytest_asyncio.fixture
async def temp_db():
    """Create a temporary database for testing."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest_asyncio.fixture
async def storage_components(temp_db):
    """Create storage components for testing."""
    task_queue = AsyncSQLiteQueue(temp_db)
    result_storage = AsyncSQLiteResultStorage(temp_db)
    event_storage = AsyncSQLiteEventStorage(temp_db)
    
    # Connect all components
    await task_queue.connect()
    await result_storage.connect()
    await event_storage.connect()
    
    try:
        yield task_queue, result_storage, event_storage
    finally:
        await task_queue.disconnect()
        await result_storage.disconnect()
        await event_storage.disconnect()


class TestThreadPoolWorker:
    """Test cases for ThreadPoolWorker."""
    
    def test_initialization(self, storage_components, function_registry):
        """Test ThreadPoolWorker initialization."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ThreadPoolWorker(
            worker_id="test-thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=4,
        )
        
        assert worker.worker_id == "test-thread-pool-worker"
        assert worker.max_workers == 4
        assert worker.get_thread_pool_size() == 4
        assert not worker.is_running()
        assert worker.get_active_task_count() == 0
    
    @pytest.mark.asyncio
    async def test_execute_task_sync(self, storage_components, function_registry):
        """Test executing a synchronous task in thread pool worker."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Create a task
            task = Task(func="sync_add", args=(7, 8))
            
            # Execute the task
            result = await worker.execute_task(task)
            
            # Verify result
            assert result.is_successful()
            assert result.result == 15
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_execute_io_task(self, storage_components, function_registry):
        """Test executing an I/O-bound task in thread pool worker."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Create an I/O task
            task = Task(func="io_task", args=(0.1,))
            
            # Execute the task
            result = await worker.execute_task(task)
            
            # Verify result
            assert result.is_successful()
            assert result.result == "IO task completed after 0.1s"
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, storage_components, function_registry):
        """Test concurrent execution of multiple tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=3,
        ) as worker:
            # Create multiple tasks
            tasks = [
                Task(func="sync_add", args=(i, i + 1))
                for i in range(5)
            ]
            
            # Execute tasks concurrently
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
            
            # Verify all results
            for i, result in enumerate(results):
                assert result.is_successful()
                assert result.result == i + (i + 1)  # i + (i + 1)
                assert result.task_id == tasks[i].id
    
    def test_register_function(self, storage_components, function_registry):
        """Test function registration."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        )
        
        # Register a new function
        def multiply(a, b):
            return a * b
        
        worker.register_function("multiply", multiply)
        
        # Verify function is registered
        assert "multiply" in worker._function_registry
        assert worker._function_registry["multiply"] == multiply
    
    @pytest.mark.asyncio
    async def test_context_manager(self, storage_components, function_registry):
        """Test ThreadPoolWorker as async context manager."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            assert isinstance(worker, ThreadPoolWorker)
            # Worker should be ready to use
    
    def test_repr(self, storage_components, function_registry):
        """Test string representation."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ThreadPoolWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=4,
        )
        
        repr_str = repr(worker)
        assert "ThreadPoolWorker" in repr_str
        assert "test-worker" in repr_str
        assert "max_workers=4" in repr_str


class TestThreadPoolWorkerPool:
    """Test cases for ThreadPoolWorker in WorkerPool."""
    
    @pytest.mark.asyncio
    async def test_thread_pool_worker_pool_creation(self, storage_components, function_registry):
        """Test creating a thread pool worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.THREAD_POOL,
            max_workers=3,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        assert pool.worker_type == WorkerType.THREAD_POOL
        assert pool.max_workers == 3
        assert pool.get_worker_count() == 0
        assert not pool.is_running()
    
    @pytest.mark.asyncio
    async def test_thread_pool_worker_pool_context_manager(self, storage_components, function_registry):
        """Test ThreadPoolWorker pool as context manager."""
        task_queue, result_storage, event_storage = storage_components
        
        async with WorkerPool(
            worker_type=WorkerType.THREAD_POOL,
            max_workers=2,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        ) as pool:
            assert isinstance(pool, WorkerPool)
            assert pool.worker_type == WorkerType.THREAD_POOL
            # Pool should be ready to use