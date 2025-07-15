import asyncio
from src.omniq.core import OmniQ
from src.omniq.models.config import OmniQConfig, QueueConfig
from src.omniq.workers.async_worker import AsyncWorker

async def debug_cross_queue_routing():
    """Debug the cross-queue routing issue."""
    
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
    
    # Create OmniQ instance
    omniq = OmniQ(config=config)
    await omniq.connect()
    
    # Define test function
    def test_func(msg):
        print(f"Function called with: {msg} (type: {type(msg)})")
        return f"processed: {msg}"
    
    # Register function
    omniq.register_function("test_func", test_func)
    
    # Submit tasks
    print("Submitting tasks...")
    task1_id = await omniq.submit_task(
        "test_func", args=("task1",), queue="test_queue", priority=3
    )
    task2_id = await omniq.submit_task(
        "test_func", args=("task2",), queue="high_priority", priority=8
    )
    
    print(f"Task 1 ID: {task1_id}")
    print(f"Task 2 ID: {task2_id}")
    
    # Get tasks to inspect them
    task1 = await omniq.get_task(task1_id)
    task2 = await omniq.get_task(task2_id)
    
    if task1:
        print(f"Task 1 args: {task1.args}, kwargs: {task1.kwargs}")
    else:
        print("Task 1 not found")
    
    if task2:
        print(f"Task 2 args: {task2.args}, kwargs: {task2.kwargs}")
    else:
        print("Task 2 not found")
    
    # Create worker
    worker = AsyncWorker(
        task_queue=omniq._task_queue,
        result_storage=omniq._result_storage,
        event_storage=omniq._event_storage,
        queue_manager=omniq._queue_manager
    )
    worker.register_function("test_func", test_func)
    
    # Process tasks
    print("Processing tasks...")
    result1 = await worker.process_single_task(["test_queue", "high_priority"])
    result2 = await worker.process_single_task(["test_queue", "high_priority"])
    
    print(f"Result 1: {result1.result if result1 else None}")
    print(f"Result 2: {result2.result if result2 else None}")
    
    await omniq.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_cross_queue_routing())