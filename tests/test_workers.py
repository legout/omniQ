"""
Tests for OmniQ worker implementations.

This module tests the worker system including AsyncWorker, ThreadWorker,
ProcessWorker, and WorkerPool functionality.
"""

import asyncio
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from omniq.workers import AsyncWorker, ThreadWorker, ProcessWorker, WorkerPool, WorkerType
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.storage.sqlite import AsyncSQLiteQueue, AsyncSQLiteResultStorage, AsyncSQLiteEventStorage


# Test functions for workers
def sync_add(a: int, b: int) -> int:
    """Simple sync function for testing."""
    return a + b


async def async_multiply(a: int, b: int) -> int:
    """Simple async function for testing."""
    await asyncio.sleep(0.01)  # Small delay to simulate async work
    return a * b


def failing_function():
    """Function that always fails for testing error handling."""
    raise ValueError("This function always fails")


def cpu_intensive_task(n: int) -> int:
    """CPU-intensive task for process worker testing."""
    result = 0
    for i in range(n * 10000):
        result += i % 7
    return result


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
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


@pytest.fixture
def function_registry():
    """Create function registry for testing."""
    return {
        "sync_add": sync_add,
        "async_multiply": async_multiply,
        "failing_function": failing_function,
        "cpu_intensive_task": cpu_intensive_task,
    }


class TestAsyncWorker:
    """Test cases for AsyncWorker."""
    
    @pytest.mark.asyncio
    async def test_execute_sync_task(self, storage_components, function_registry):
        """Test executing a synchronous task."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = AsyncWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        # Create a task
        task = Task(func="sync_add", args=(5, 3))
        
        # Execute the task
        result = await worker.execute_task(task)
        
        # Verify result
        assert result.is_successful()
        assert result.result == 8
        assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_execute_async_task(self, storage_components, function_registry):
        """Test executing an asynchronous task."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = AsyncWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        # Create a task
        task = Task(func="async_multiply", args=(4, 6))
        
        # Execute the task
        result = await worker.execute_task(task)
        
        # Verify result
        assert result.is_successful()
        assert result.result == 24
        assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_execute_failing_task(self, storage_components, function_registry):
        """Test executing a task that fails."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = AsyncWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        # Create a failing task
        task = Task(func="failing_function")
        
        # Execute the task
        result = await worker.execute_task(task)
        
        # Verify result
        assert not result.is_successful()
        assert result.status == ResultStatus.ERROR
        assert "This function always fails" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_task_timeout(self, storage_components, function_registry):
        """Test task timeout functionality."""
        task_queue, result_storage, event_storage = storage_components
        
        # Create worker with short timeout
        worker = AsyncWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            task_timeout=0.001,  # Very short timeout
        )
        
        # Create a task that will timeout
        task = Task(func="async_multiply", args=(4, 6))
        
        # Execute the task
        result = await worker.execute_task(task)
        
        # Verify timeout
        assert not result.is_successful()
        assert "timed out" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_process_single_task(self, storage_components, function_registry):
        """Test processing a single task from the queue."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = AsyncWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        # Enqueue a task
        task = Task(func="sync_add", args=(10, 20))
        await task_queue.enqueue(task)
        
        # Process the task
        result = await worker.process_single_task()
        
        # Verify result
        assert result is not None
        assert result.is_successful()
        assert result.result == 30


class TestThreadWorker:
    """Test cases for ThreadWorker."""
    
    @pytest.mark.asyncio
    async def test_execute_task_sync(self, storage_components, function_registry):
        """Test executing a task synchronously in thread worker."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ThreadWorker(
            worker_id="thread-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=1,
        )
        
        # Create a task
        task = Task(func="sync_add", args=(7, 8))
        
        # Execute the task
        result = worker.execute_task(task)
        
        # Verify result
        assert result.is_successful()
        assert result.result == 15
        assert result.task_id == task.id


class TestProcessWorker:
    """Test cases for ProcessWorker."""
    
    @pytest.mark.asyncio
    async def test_execute_cpu_task(self, storage_components, function_registry):
        """Test executing a CPU-intensive task in process worker."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ProcessWorker(
            worker_id="process-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=1,
        )
        
        # Start the worker
        worker._executor = worker._executor or worker.__class__(
            worker_id="process-worker",
            max_workers=1
        )._executor
        
        # Create a CPU-intensive task
        task = Task(func="cpu_intensive_task", args=(10,))
        
        # Execute the task
        result = await worker.execute_task(task)
        
        # Verify result
        assert result.is_successful()
        assert isinstance(result.result, int)
        assert result.task_id == task.id


class TestWorkerPool:
    """Test cases for WorkerPool."""
    
    @pytest.mark.asyncio
    async def test_async_worker_pool_creation(self, storage_components, function_registry):
        """Test creating an async worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.ASYNC,
            max_workers=2,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        assert pool.worker_type == WorkerType.ASYNC
        assert pool.max_workers == 2
        assert pool.get_worker_count() == 0  # No workers created yet
        assert not pool.is_running()
    
    @pytest.mark.asyncio
    async def test_thread_worker_pool_creation(self, storage_components, function_registry):
        """Test creating a thread worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.THREAD,
            max_workers=3,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        assert pool.worker_type == WorkerType.THREAD
        assert pool.max_workers == 3
        assert pool.get_worker_count() == 0
        assert not pool.is_running()
    
    @pytest.mark.asyncio
    async def test_process_worker_pool_creation(self, storage_components, function_registry):
        """Test creating a process worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.PROCESS,
            max_workers=2,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        assert pool.worker_type == WorkerType.PROCESS
        assert pool.max_workers == 2
        assert pool.get_worker_count() == 0
        assert not pool.is_running()
    
    @pytest.mark.asyncio
    async def test_worker_pool_context_manager(self, storage_components, function_registry):
        """Test worker pool as async context manager."""
        task_queue, result_storage, event_storage = storage_components
        
        async with WorkerPool(
            worker_type=WorkerType.ASYNC,
            max_workers=1,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        ) as pool:
            assert isinstance(pool, WorkerPool)
            # Pool should be ready to use
    
    @pytest.mark.asyncio
    async def test_function_registration(self, storage_components, function_registry):
        """Test registering functions in worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.ASYNC,
            max_workers=1,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry={},
        )
        
        # Register a function
        pool.register_function("test_func", sync_add)
        
        # Verify function is registered
        assert "test_func" in pool.function_registry
        assert pool.function_registry["test_func"] == sync_add


if __name__ == "__main__":
    pytest.main([__file__])