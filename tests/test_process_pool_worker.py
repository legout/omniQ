"""
Tests for ProcessPoolWorker implementation.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from omniq.workers.process_pool_worker import ProcessPoolWorker
from omniq.workers.pool import WorkerPool, WorkerType
from omniq.models.task import Task
from omniq.models.result import TaskResult, ResultStatus
from omniq.storage.sqlite import AsyncSQLiteQueue, AsyncSQLiteResultStorage, AsyncSQLiteEventStorage


# Module-level functions that are picklable
def sync_add(a, b):
    """Simple synchronous addition function."""
    return a + b


def cpu_intensive_task(n):
    """CPU-intensive task that benefits from process isolation."""
    result = 0
    for i in range(n * 10000):
        result += i * i
    return result


def factorial(n):
    """Calculate factorial."""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n):
    """Calculate Fibonacci number."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def multiply(a, b):
    """Simple multiplication function."""
    return a * b


@pytest.fixture
def function_registry():
    """Create a function registry for testing."""
    return {
        "sync_add": sync_add,
        "cpu_intensive_task": cpu_intensive_task,
        "factorial": factorial,
        "fibonacci": fibonacci,
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


class TestProcessPoolWorker:
    """Test cases for ProcessPoolWorker."""
    
    def test_initialization(self, storage_components, function_registry):
        """Test ProcessPoolWorker initialization."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ProcessPoolWorker(
            worker_id="test-process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        )
        
        assert worker.worker_id == "test-process-pool-worker"
        assert worker.max_workers == 2
        assert worker.get_process_pool_size() == 2
        assert not worker.is_running()
        assert worker.get_active_task_count() == 0
    
    @pytest.mark.asyncio
    async def test_execute_task_sync(self, storage_components, function_registry):
        """Test executing a synchronous task in process pool worker."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
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
    async def test_execute_cpu_intensive_task(self, storage_components, function_registry):
        """Test executing a CPU-intensive task in process pool worker."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Create a CPU-intensive task
            task = Task(func="cpu_intensive_task", args=(100,))
            
            # Execute the task
            result = await worker.execute_task(task)
            
            # Verify result
            assert result.is_successful()
            assert isinstance(result.result, int)
            assert result.result > 0
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, storage_components, function_registry):
        """Test concurrent execution of multiple CPU-intensive tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=3,
        ) as worker:
            # Create multiple CPU-intensive tasks
            tasks = [
                Task(func="factorial", args=(i + 5,))
                for i in range(5)
            ]
            
            # Execute tasks concurrently
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
            
            # Verify all results
            expected_factorials = [120, 720, 5040, 40320, 362880]  # 5!, 6!, 7!, 8!, 9!
            for i, result in enumerate(results):
                assert result.is_successful()
                assert result.result == expected_factorials[i]
                assert result.task_id == tasks[i].id
    
    @pytest.mark.asyncio
    async def test_fibonacci_task(self, storage_components, function_registry):
        """Test Fibonacci calculation in process pool."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Create Fibonacci task
            task = Task(func="fibonacci", args=(10,))
            
            # Execute the task
            result = await worker.execute_task(task)
            
            # Verify result (10th Fibonacci number is 55)
            assert result.is_successful()
            assert result.result == 55
            assert result.task_id == task.id
    
    def test_register_function(self, storage_components, function_registry):
        """Test function registration with picklability check."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        )
        
        # Register a new picklable function (module-level function)
        worker.register_function("multiply", multiply)
        
        # Verify function is registered
        assert "multiply" in worker._picklable_registry
        assert worker._picklable_registry["multiply"] == multiply
        
        # Try to register a non-picklable function (lambda)
        worker.register_function("lambda_func", lambda x: x * 2)
        
        # Lambda should not be in the registry due to pickling issues
        assert "lambda_func" not in worker._picklable_registry
    
    def test_picklable_function_filtering(self, storage_components):
        """Test that non-picklable functions are filtered out."""
        task_queue, result_storage, event_storage = storage_components
        
        # Create registry with both picklable and non-picklable functions
        mixed_registry = {
            "picklable_func": lambda x: x + 1,  # This might not be picklable
            "regular_func": max,  # Built-in functions are usually picklable
        }
        
        worker = ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=mixed_registry,
            max_workers=2,
        )
        
        # Check that only picklable functions are in the registry
        # Built-in functions like max should be picklable
        assert "regular_func" in worker._picklable_registry
    
    @pytest.mark.asyncio
    async def test_context_manager(self, storage_components, function_registry):
        """Test ProcessPoolWorker as async context manager."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            assert isinstance(worker, ProcessPoolWorker)
            # Worker should be ready to use
    
    def test_repr(self, storage_components, function_registry):
        """Test string representation."""
        task_queue, result_storage, event_storage = storage_components
        
        worker = ProcessPoolWorker(
            worker_id="test-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=4,
        )
        
        repr_str = repr(worker)
        assert "ProcessPoolWorker" in repr_str
        assert "test-worker" in repr_str
        assert "max_workers=4" in repr_str


class TestProcessPoolWorkerPool:
    """Test cases for ProcessPoolWorker in WorkerPool."""
    
    @pytest.mark.asyncio
    async def test_process_pool_worker_pool_creation(self, storage_components, function_registry):
        """Test creating a process pool worker pool."""
        task_queue, result_storage, event_storage = storage_components
        
        pool = WorkerPool(
            worker_type=WorkerType.PROCESS_POOL,
            max_workers=3,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        )
        
        assert pool.worker_type == WorkerType.PROCESS_POOL
        assert pool.max_workers == 3
        assert pool.get_worker_count() == 0
        assert not pool.is_running()
    
    @pytest.mark.asyncio
    async def test_process_pool_worker_pool_context_manager(self, storage_components, function_registry):
        """Test ProcessPoolWorker pool as context manager."""
        task_queue, result_storage, event_storage = storage_components
        
        async with WorkerPool(
            worker_type=WorkerType.PROCESS_POOL,
            max_workers=2,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        ) as pool:
            assert isinstance(pool, WorkerPool)
            assert pool.worker_type == WorkerType.PROCESS_POOL
            # Pool should be ready to use
    
    def test_worker_type_enum(self):
        """Test that PROCESS_POOL is available in WorkerType enum."""
        assert hasattr(WorkerType, 'PROCESS_POOL')
        assert WorkerType.PROCESS_POOL == "process_pool"