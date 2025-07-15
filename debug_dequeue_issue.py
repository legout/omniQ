import asyncio
from src.omniq.core import OmniQ
from src.omniq.models.config import OmniQConfig, QueueConfig
from src.omniq.workers.async_worker import AsyncWorker

async def debug_dequeue_issue():
    """Debug the dequeue issue specifically."""
    
    # Create config
    config = OmniQConfig()
    config.add_queue_config(QueueConfig(
        name="test_queue",
        priority_algorithm="numeric",
        default_priority=5,
        min_priority=1,
        max_priority=10
    ))
    config.add_queue_config(QueueConfig(
        name="high_priority",
        priority_algorithm="numeric",
        default_priority=8,
        min_priority=1,
        max_priority=10
    ))
    config.queue_routing_strategy = "priority"
    
    # Create OmniQ instance
    omniq = OmniQ(config=config)
    await omniq.connect()
    
    # Define test function
    def test_func(msg):
        print(f"Processing: {msg}")
        return f"processed: {msg}"
    
    # Register function
    omniq.register_function("test_func", test_func)
    
    # Submit tasks
    print("=== Submitting tasks ===")
    task1_id = await omniq.submit_task(
        "test_func", args=("task1",), queue="test_queue", priority=3
    )
    task2_id = await omniq.submit_task(
        "test_func", args=("task2",), queue="high_priority", priority=8
    )
    
    print(f"Task 1 ID: {task1_id}")
    print(f"Task 2 ID: {task2_id}")
    
    # Check queue sizes before processing
    print("\n=== Queue sizes before processing ===")
    test_queue_size = await omniq._task_queue.get_queue_size("test_queue")
    high_priority_size = await omniq._task_queue.get_queue_size("high_priority")
    print(f"test_queue size: {test_queue_size}")
    print(f"high_priority size: {high_priority_size}")
    
    # Create worker
    worker = AsyncWorker(
        task_queue=omniq._task_queue,
        result_storage=omniq._result_storage,
        event_storage=omniq._event_storage,
        queue_manager=omniq._queue_manager
    )
    worker.register_function("test_func", test_func)
    
    # Process first task
    print("\n=== Processing first task ===")
    result1 = await worker.process_single_task(["test_queue", "high_priority"])
    print(f"Result 1: {result1.result if result1 else 'None'}")
    
    # Check queue sizes after first processing
    print("\n=== Queue sizes after first processing ===")
    test_queue_size = await omniq._task_queue.get_queue_size("test_queue")
    high_priority_size = await omniq._task_queue.get_queue_size("high_priority")
    print(f"test_queue size: {test_queue_size}")
    print(f"high_priority size: {high_priority_size}")
    
    # Process second task
    print("\n=== Processing second task ===")
    result2 = await worker.process_single_task(["test_queue", "high_priority"])
    print(f"Result 2: {result2.result if result2 else 'None'}")
    
    # Check queue sizes after second processing
    print("\n=== Queue sizes after second processing ===")
    test_queue_size = await omniq._task_queue.get_queue_size("test_queue")
    high_priority_size = await omniq._task_queue.get_queue_size("high_priority")
    print(f"test_queue size: {test_queue_size}")
    print(f"high_priority size: {high_priority_size}")
    
    await omniq.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_dequeue_issue())