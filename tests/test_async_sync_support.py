"""
Tests for sync and async task support across all worker types.

This module comprehensively tests that all worker types can correctly
execute both synchronous and asynchronous functions with proper
task type detection and routing.
"""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock

from omniq.workers import AsyncWorker, ThreadPoolWorker, ProcessPoolWorker, GeventPoolWorker
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.storage.memory import AsyncMemoryQueue, MemoryResultStorage, MemoryEventStorage


# Test functions for sync/async testing
def sync_add(a: int, b: int) -> int:
    """Simple sync function for testing."""
    return a + b


async def async_multiply(a: int, b: int) -> int:
    """Simple async function for testing."""
    await asyncio.sleep(0.01)  # Small delay to simulate async work
    return a * b


def sync_io_task(duration: float) -> str:
    """Sync I/O-bound task for testing."""
    import time
    time.sleep(duration)
    return f"Sync I/O task completed after {duration}s"


async def async_io_task(duration: float) -> str:
    """Async I/O-bound task for testing."""
    await asyncio.sleep(duration)
    return f"Async I/O task completed after {duration}s"


def cpu_intensive_sync(n: int) -> int:
    """CPU-intensive sync task for testing."""
    result = 0
    for i in range(n * 1000):
        result += i % 7
    return result


async def cpu_intensive_async(n: int) -> int:
    """CPU-intensive async task for testing."""
    result = 0
    for i in range(n * 1000):
        result += i % 7
        if i % 100 == 0:
            await asyncio.sleep(0)  # Yield control
    return result


@pytest_asyncio.fixture
async def storage_components():
    """Create storage components for testing."""
    task_queue = AsyncMemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    # Connect storage components
    await task_queue.connect()
    await result_storage.connect()
    await event_storage.connect()
    
    yield task_queue, result_storage, event_storage
    
    # Cleanup
    await task_queue.disconnect()
    await result_storage.disconnect()
    await event_storage.disconnect()


@pytest.fixture
def function_registry():
    """Create function registry for testing."""
    return {
        "sync_add": sync_add,
        "async_multiply": async_multiply,
        "sync_io_task": sync_io_task,
        "async_io_task": async_io_task,
        "cpu_intensive_sync": cpu_intensive_sync,
        "cpu_intensive_async": cpu_intensive_async,
    }


class TestAsyncWorkerSyncAsyncSupport:
    """Test AsyncWorker's sync and async task support."""
    
    @pytest.mark.asyncio
    async def test_sync_task_execution(self, function_registry):
        """Test that AsyncWorker can execute sync tasks."""
        worker = AsyncWorker(
            worker_id="async-worker",
            function_registry=function_registry,
        )
        
        # Test sync function
        task = Task(func="sync_add", args=(10, 20))
        result = await worker.execute_task(task)
        
        assert result.is_successful()
        assert result.result == 30
        assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self, function_registry):
        """Test that AsyncWorker can execute async tasks."""
        worker = AsyncWorker(
            worker_id="async-worker",
            function_registry=function_registry,
        )
        
        # Test async function
        task = Task(func="async_multiply", args=(5, 6))
        result = await worker.execute_task(task)
        
        assert result.is_successful()
        assert result.result == 30
        assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_tasks(self, function_registry):
        """Test that AsyncWorker can handle mixed sync and async tasks."""
        worker = AsyncWorker(
            worker_id="async-worker",
            function_registry=function_registry,
        )
        
        # Execute multiple tasks of different types
        tasks = [
            Task(func="sync_add", args=(1, 2)),
            Task(func="async_multiply", args=(3, 4)),
            Task(func="sync_add", args=(5, 6)),
            Task(func="async_multiply", args=(7, 8)),
        ]
        
        results = await asyncio.gather(*[
            worker.execute_task(task) for task in tasks
        ])
        
        # Verify all results
        assert all(result.is_successful() for result in results)
        assert results[0].result == 3  # sync_add(1, 2)
        assert results[1].result == 12  # async_multiply(3, 4)
        assert results[2].result == 11  # sync_add(5, 6)
        assert results[3].result == 56  # async_multiply(7, 8)


class TestThreadPoolWorkerSyncAsyncSupport:
    """Test ThreadPoolWorker's sync and async task support."""
    
    @pytest.mark.asyncio
    async def test_sync_task_execution(self, storage_components, function_registry):
        """Test that ThreadPoolWorker can execute sync tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Test sync function
            task = Task(func="sync_add", args=(15, 25))
            result = await worker.execute_task(task)
            
            assert result.is_successful()
            assert result.result == 40
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self, storage_components, function_registry):
        """Test that ThreadPoolWorker can execute async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Test async function
            task = Task(func="async_multiply", args=(6, 7))
            result = await worker.execute_task(task)
            
            assert result.is_successful()
            assert result.result == 42
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_tasks(self, storage_components, function_registry):
        """Test that ThreadPoolWorker can handle mixed sync and async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=3,
        ) as worker:
            # Execute multiple tasks of different types
            tasks = [
                Task(func="sync_add", args=(2, 3)),
                Task(func="async_multiply", args=(4, 5)),
                Task(func="sync_io_task", args=(0.01,)),
                Task(func="async_io_task", args=(0.01,)),
            ]
            
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
            
            # Verify all results
            assert all(result.is_successful() for result in results)
            assert results[0].result == 5  # sync_add(2, 3)
            assert results[1].result == 20  # async_multiply(4, 5)
            assert results[2].result and "Sync I/O task completed" in results[2].result
            assert results[3].result and "Async I/O task completed" in results[3].result


class TestProcessPoolWorkerSyncAsyncSupport:
    """Test ProcessPoolWorker's sync and async task support."""
    
    @pytest.mark.asyncio
    async def test_sync_task_execution(self, storage_components, function_registry):
        """Test that ProcessPoolWorker can execute sync tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Test sync function
            task = Task(func="sync_add", args=(100, 200))
            result = await worker.execute_task(task)
            
            assert result.is_successful()
            assert result.result == 300
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self, storage_components, function_registry):
        """Test that ProcessPoolWorker can execute async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Test async function
            task = Task(func="async_multiply", args=(8, 9))
            result = await worker.execute_task(task)
            
            assert result.is_successful()
            assert result.result == 72
            assert result.task_id == task.id
    
    @pytest.mark.asyncio
    async def test_cpu_intensive_tasks(self, storage_components, function_registry):
        """Test that ProcessPoolWorker can handle CPU-intensive sync and async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
        ) as worker:
            # Execute CPU-intensive tasks
            tasks = [
                Task(func="cpu_intensive_sync", args=(10,)),
                Task(func="cpu_intensive_async", args=(10,)),
            ]
            
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
            
            # Verify all results
            assert all(result.is_successful() for result in results)
            assert isinstance(results[0].result, int)
            assert isinstance(results[1].result, int)
            # Both should produce the same result
            assert results[0].result == results[1].result


class TestGeventPoolWorkerSyncAsyncSupport:
    """Test GeventPoolWorker's sync and async task support."""
    
    @pytest.mark.asyncio
    async def test_sync_task_execution(self, storage_components, function_registry):
        """Test that GeventPoolWorker can execute sync tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        try:
            async with GeventPoolWorker(
                worker_id="gevent-pool-worker",
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                function_registry=function_registry,
                max_workers=2,
            ) as worker:
                # Test sync function
                task = Task(func="sync_add", args=(50, 75))
                result = await worker.execute_task(task)
                
                assert result.is_successful()
                assert result.result == 125
                assert result.task_id == task.id
        except RuntimeError as e:
            if "Gevent is not available" in str(e):
                pytest.skip("Gevent not available")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self, storage_components, function_registry):
        """Test that GeventPoolWorker can execute async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        try:
            async with GeventPoolWorker(
                worker_id="gevent-pool-worker",
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                function_registry=function_registry,
                max_workers=2,
            ) as worker:
                # Test async function
                task = Task(func="async_multiply", args=(9, 11))
                result = await worker.execute_task(task)
                
                assert result.is_successful()
                assert result.result == 99
                assert result.task_id == task.id
        except RuntimeError as e:
            if "Gevent is not available" in str(e):
                pytest.skip("Gevent not available")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_tasks(self, storage_components, function_registry):
        """Test that GeventPoolWorker can handle mixed sync and async tasks."""
        task_queue, result_storage, event_storage = storage_components
        
        try:
            async with GeventPoolWorker(
                worker_id="gevent-pool-worker",
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                function_registry=function_registry,
                max_workers=3,
            ) as worker:
                # Execute multiple tasks of different types
                tasks = [
                    Task(func="sync_add", args=(3, 4)),
                    Task(func="async_multiply", args=(5, 6)),
                    Task(func="sync_add", args=(7, 8)),
                ]
                
                results = await asyncio.gather(*[
                    worker.execute_task(task) for task in tasks
                ])
                
                # Verify all results
                assert all(result.is_successful() for result in results)
                assert results[0].result == 7   # sync_add(3, 4)
                assert results[1].result == 30  # async_multiply(5, 6)
                assert results[2].result == 15  # sync_add(7, 8)
        except RuntimeError as e:
            if "Gevent is not available" in str(e):
                pytest.skip("Gevent not available")
            else:
                raise


class TestUnifiedWorkerInterface:
    """Test that all worker types provide a unified interface for sync/async tasks."""
    
    @pytest.mark.asyncio
    async def test_all_workers_sync_task(self, storage_components, function_registry):
        """Test that all worker types can execute the same sync task."""
        task_queue, result_storage, event_storage = storage_components
        
        # Test task
        task = Task(func="sync_add", args=(12, 13))
        expected_result = 25
        
        # Test AsyncWorker
        async_worker = AsyncWorker(
            worker_id="async-worker",
            function_registry=function_registry,
        )
        result = await async_worker.execute_task(task)
        assert result.is_successful()
        assert result.result == expected_result
        
        # Test ThreadPoolWorker
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            function_registry=function_registry,
            max_workers=1,
        ) as thread_worker:
            result = await thread_worker.execute_task(task)
            assert result.is_successful()
            assert result.result == expected_result
        
        # Test ProcessPoolWorker
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            function_registry=function_registry,
            max_workers=1,
        ) as process_worker:
            result = await process_worker.execute_task(task)
            assert result.is_successful()
            assert result.result == expected_result
        
        # Test GeventPoolWorker (if available)
        try:
            async with GeventPoolWorker(
                worker_id="gevent-pool-worker",
                function_registry=function_registry,
                max_workers=1,
            ) as gevent_worker:
                result = await gevent_worker.execute_task(task)
                assert result.is_successful()
                assert result.result == expected_result
        except RuntimeError as e:
            if "Gevent is not available" in str(e):
                pass  # Skip if gevent not available
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_all_workers_async_task(self, storage_components, function_registry):
        """Test that all worker types can execute the same async task."""
        task_queue, result_storage, event_storage = storage_components
        
        # Test task
        task = Task(func="async_multiply", args=(6, 7))
        expected_result = 42
        
        # Test AsyncWorker
        async_worker = AsyncWorker(
            worker_id="async-worker",
            function_registry=function_registry,
        )
        result = await async_worker.execute_task(task)
        assert result.is_successful()
        assert result.result == expected_result
        
        # Test ThreadPoolWorker
        async with ThreadPoolWorker(
            worker_id="thread-pool-worker",
            function_registry=function_registry,
            max_workers=1,
        ) as thread_worker:
            result = await thread_worker.execute_task(task)
            assert result.is_successful()
            assert result.result == expected_result
        
        # Test ProcessPoolWorker
        async with ProcessPoolWorker(
            worker_id="process-pool-worker",
            function_registry=function_registry,
            max_workers=1,
        ) as process_worker:
            result = await process_worker.execute_task(task)
            assert result.is_successful()
            assert result.result == expected_result
        
        # Test GeventPoolWorker (if available)
        try:
            async with GeventPoolWorker(
                worker_id="gevent-pool-worker",
                function_registry=function_registry,
                max_workers=1,
            ) as gevent_worker:
                result = await gevent_worker.execute_task(task)
                assert result.is_successful()
                assert result.result == expected_result
        except RuntimeError as e:
            if "Gevent is not available" in str(e):
                pass  # Skip if gevent not available
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__])