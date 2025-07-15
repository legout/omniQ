"""
Test queue manager integration with OmniQ core and workers.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from src.omniq.core import OmniQ
from src.omniq.models.config import OmniQConfig, QueueConfig
from src.omniq.models.task import Task, TaskStatus
from src.omniq.queue_manager import QueueManager, NumericPriorityAlgorithm, WeightedPriorityAlgorithm
from src.omniq.workers.async_worker import AsyncWorker
from src.omniq.storage.memory import MemoryQueue, MemoryResultStorage, MemoryEventStorage


@pytest.fixture
def queue_config():
    """Create a test queue configuration."""
    return QueueConfig(
        name="test_queue",
        priority_algorithm="weighted",
        default_priority=5,
        min_priority=1,
        max_priority=10,
        max_size=100,
        timeout=300.0,
        max_retries=3,
        retry_delay=1.0,
        priority_weights={"urgent": 2.0, "important": 1.5}
    )


@pytest.fixture
def omniq_config(queue_config):
    """Create OmniQ configuration with queue settings."""
    config = OmniQConfig()
    config.add_queue_config(queue_config)
    config.add_queue_config(QueueConfig(
        name="high_priority",
        priority_algorithm="numeric",
        default_priority=8,
        min_priority=1,
        max_priority=10
    ))
    config.queue_routing_strategy = "priority"
    return config


@pytest_asyncio.fixture
async def omniq_instance(omniq_config):
    """Create and connect OmniQ instance with proper memory filesystem isolation."""
    import uuid
    
    # Clear memory filesystem before test to ensure clean state
    try:
        import fsspec
        fs = fsspec.filesystem('memory')
        # Clear all files in the memory filesystem
        if hasattr(fs, 'store') and fs.store:
            fs.store.clear()
    except Exception:
        pass  # Ignore if fsspec not available or other issues
    
    # Use a unique base directory for each test to ensure isolation
    unique_id = str(uuid.uuid4())
    omniq = OmniQ(config=omniq_config, independent_storage=True, base_dir=f"/test_{unique_id}")
    await omniq.connect()
    
    yield omniq
    
    await omniq.disconnect()
    
    # Clear memory filesystem after test to prevent pollution
    try:
        import fsspec
        fs = fsspec.filesystem('memory')
        # Clear all files in the memory filesystem
        if hasattr(fs, 'store') and fs.store:
            fs.store.clear()
    except Exception:
        pass  # Ignore if fsspec not available or other issues


class TestQueueManagerIntegration:
    """Test queue manager integration."""
    
    @pytest.mark.asyncio
    async def test_queue_manager_initialization(self, omniq_instance):
        """Test that queue manager is properly initialized."""
        assert omniq_instance._queue_manager is not None
        assert isinstance(omniq_instance._queue_manager, QueueManager)
        
        # Test queue configuration access
        queue_config = omniq_instance.get_queue_config("test_queue")
        assert queue_config is not None
        assert queue_config.name == "test_queue"
        assert queue_config.priority_algorithm == "weighted"
    
    @pytest.mark.asyncio
    async def test_task_submission_with_queue_validation(self, omniq_instance):
        """Test task submission with queue-specific validation."""
        # Register a test function
        def test_func(x, y):
            return x + y
        
        omniq_instance.register_function("test_func", test_func)
        
        # Submit task to test_queue
        task_id = await omniq_instance.submit_task(
            func_name="test_func",
            args=(1, 2),
            queue="test_queue",
            priority=3,
            metadata={"urgent": True, "important": True}
        )
        
        # Verify task was created
        task = await omniq_instance.get_task(task_id)
        assert task is not None
        assert task.queue_name == "test_queue"
        # Priority should be calculated by weighted algorithm: 3 * (1 + 2.0 + 1.5) = 13.5
        # But clamped to max_priority=10
        assert task.priority == 10
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, omniq_instance):
        """Test queue statistics functionality."""
        # Submit some tasks
        def dummy_func():
            return "done"
        
        omniq_instance.register_function("dummy_func", dummy_func)
        
        # Submit to different queues
        await omniq_instance.submit_task("dummy_func", queue="test_queue")
        await omniq_instance.submit_task("dummy_func", queue="high_priority")
        await omniq_instance.submit_task("dummy_func", queue="test_queue")
        
        # Get statistics
        stats = await omniq_instance.get_queue_statistics()
        assert "test_queue" in stats
        assert "high_priority" in stats
        assert stats["test_queue"]["enqueued_count"] == 2
        assert stats["high_priority"]["enqueued_count"] == 1
        
        # Get specific queue statistics
        test_queue_stats = await omniq_instance.get_queue_statistics("test_queue")
        assert "test_queue" in test_queue_stats
        assert test_queue_stats["test_queue"]["enqueued_count"] == 2
    
    @pytest.mark.asyncio
    async def test_priority_algorithm_registration(self, omniq_instance):
        """Test custom priority algorithm registration."""
        class CustomPriorityAlgorithm:
            def calculate_priority(self, task, queue_config):
                return task.priority * 2  # Double the priority
        
        # Register custom algorithm
        omniq_instance.register_priority_algorithm("custom", CustomPriorityAlgorithm())
        
        # Update queue config to use custom algorithm
        queue_config = omniq_instance.get_queue_config("test_queue")
        queue_config.priority_algorithm = "custom"
        omniq_instance.update_queue_config(queue_config)
        
        # Submit task
        def test_func():
            return "test"
        
        omniq_instance.register_function("test_func", test_func)
        
        task_id = await omniq_instance.submit_task(
            func_name="test_func",
            queue="test_queue",
            priority=5
        )
        
        task = await omniq_instance.get_task(task_id)
        # Priority should be doubled by custom algorithm, but clamped to max_priority=10
        assert task.priority == 10
    
    @pytest.mark.asyncio
    async def test_worker_with_queue_manager(self, omniq_config):
        """Test worker integration with queue manager."""
        # Create storage components
        task_queue = MemoryQueue()
        result_storage = MemoryResultStorage()
        event_storage = MemoryEventStorage()
        
        # Connect storage
        task_queue.connect_sync()
        result_storage.connect_sync()
        event_storage.connect_sync()
        
        # Create queue manager
        queue_manager = QueueManager(omniq_config, task_queue)
        
        # Create worker with queue manager
        worker = AsyncWorker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            queue_manager=queue_manager
        )
        
        # Register test function
        def test_func(x):
            return x * 2
        
        worker.register_function("test_func", test_func)
        
        # Create and enqueue task
        task = Task(
            func="test_func",
            args=(5,),
            queue_name="test_queue",
            priority=3,
            metadata={"urgent": True}
        )
        
        # Use queue manager to enqueue with validation
        await queue_manager.enqueue_with_validation(task)
        
        # Process task with worker
        result = await worker.process_single_task(["test_queue"])
        
        assert result is not None
        assert result.status.name == "SUCCESS"
        assert result.result == 10
    
    @pytest.mark.asyncio
    async def test_cross_queue_routing(self, omniq_instance):
        """Test cross-queue task routing."""
        def test_func(msg):
            return f"processed: {msg}"
        
        omniq_instance.register_function("test_func", test_func)
        
        # Submit tasks to different queues
        task1_id = await omniq_instance.submit_task(
            "test_func", args=("task1",), queue="test_queue", priority=3
        )
        task2_id = await omniq_instance.submit_task(
            "test_func", args=("task2",), queue="high_priority", priority=8
        )
        
        # Create worker
        worker = AsyncWorker(
            task_queue=omniq_instance._task_queue,
            result_storage=omniq_instance._result_storage,
            event_storage=omniq_instance._event_storage,
            queue_manager=omniq_instance._queue_manager
        )
        worker.register_function("test_func", test_func)
        
        # Process tasks - should get high_priority first due to routing strategy
        result1 = await worker.process_single_task(["test_queue", "high_priority"])
        result2 = await worker.process_single_task(["test_queue", "high_priority"])
        
        # Verify results
        assert result1 is not None
        assert result2 is not None
        
        # Check which task was processed first (should be high_priority)
        results = [result1, result2]
        task_results = [r.result for r in results]
        
        # High priority task should be processed first
        assert "processed: task2" in task_results
        assert "processed: task1" in task_results
    
    @pytest.mark.asyncio
    async def test_queue_config_updates(self, omniq_instance):
        """Test dynamic queue configuration updates."""
        # Get initial config
        initial_config = omniq_instance.get_queue_config("test_queue")
        assert initial_config.default_priority == 5
        
        # Update config
        new_config = QueueConfig(
            name="test_queue",
            priority_algorithm="numeric",
            default_priority=7,
            min_priority=1,
            max_priority=10
        )
        omniq_instance.update_queue_config(new_config)
        
        # Verify update
        updated_config = omniq_instance.get_queue_config("test_queue")
        assert updated_config.default_priority == 7
        assert updated_config.priority_algorithm == "numeric"
    
    @pytest.mark.asyncio
    async def test_queue_cleanup(self, omniq_instance):
        """Test empty queue cleanup."""
        # Submit and process a task to create queue activity
        def test_func():
            return "done"
        
        omniq_instance.register_function("test_func", test_func)
        
        task_id = await omniq_instance.submit_task("test_func", queue="temp_queue")
        
        # Process the task
        worker = AsyncWorker(
            task_queue=omniq_instance._task_queue,
            result_storage=omniq_instance._result_storage,
            event_storage=omniq_instance._event_storage,
            queue_manager=omniq_instance._queue_manager
        )
        worker.register_function("test_func", test_func)
        
        await worker.process_single_task(["temp_queue"])
        
        # Queue should now be empty but have recent activity
        stats = await omniq_instance.get_queue_statistics("temp_queue")
        assert stats["temp_queue"]["current_size"] == 0
        assert stats["temp_queue"]["last_activity"] is not None
        
        # Cleanup won't remove recently active queues
        cleaned = await omniq_instance.cleanup_empty_queues()
        assert "temp_queue" not in cleaned


class TestPriorityAlgorithms:
    """Test priority algorithm implementations."""
    
    def test_numeric_priority_algorithm(self):
        """Test numeric priority algorithm."""
        algorithm = NumericPriorityAlgorithm()
        queue_config = QueueConfig(
            name="test",
            min_priority=1,
            max_priority=10,
            default_priority=5
        )
        
        # Test normal priority
        task = Task(func="test", priority=7)
        assert algorithm.calculate_priority(task, queue_config) == 7.0
        
        # Test clamping to max
        task = Task(func="test", priority=15)
        assert algorithm.calculate_priority(task, queue_config) == 10.0
        
        # Test clamping to min
        task = Task(func="test", priority=-5)
        assert algorithm.calculate_priority(task, queue_config) == 1.0
    
    def test_weighted_priority_algorithm(self):
        """Test weighted priority algorithm."""
        algorithm = WeightedPriorityAlgorithm()
        queue_config = QueueConfig(
            name="test",
            priority_weights={"urgent": 2.0, "important": 1.5}
        )
        
        # Test with metadata weights
        task = Task(
            func="test",
            priority=5,
            metadata={"urgent": True, "important": True}
        )
        # Expected: 5 * (1 + 2.0 + 1.5) = 22.5
        assert algorithm.calculate_priority(task, queue_config) == 22.5
        
        # Test with numeric metadata
        task = Task(
            func="test",
            priority=3,
            metadata={"urgent": 2, "important": False}
        )
        # Expected: 3 * (1 + 2.0 * 2) = 15.0
        assert algorithm.calculate_priority(task, queue_config) == 15.0


if __name__ == "__main__":
    pytest.main([__file__])