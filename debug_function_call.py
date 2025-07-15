import asyncio
from src.omniq.core import OmniQ
from src.omniq.models.config import OmniQConfig, QueueConfig
from src.omniq.workers.async_worker import AsyncWorker

async def debug_function_call():
    """Debug the function calling issue in cross_queue_routing test."""
    
    # Create config
    config = OmniQConfig()
    config.add_queue_config(QueueConfig(
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
    omniq = OmniQ(config=config, independent_storage=True, base_dir="/test_debug")
    await omniq.connect()
    
    # Define test function
    def test_func(msg):
        return f"processed: {msg}"
    
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
    
    # Get tasks to inspect their structure
    task1 = await omniq.get_task(task1_id)
    task2 = await omniq.get_task(task2_id)
    
    if task1:
        print(f"\nTask 1 details:")
        print(f"  func: {task1.func}")
        print(f"  args: {task1.args}")
        print(f"  kwargs: {task1.kwargs}")
        print(f"  queue: {task1.queue_name}")
        print(f"  priority: {task1.priority}")
    else:
        print(f"\nTask 1 not found!")
    
    if task2:
        print(f"\nTask 2 details:")
        print(f"  func: {task2.func}")
        print(f"  args: {task2.args}")
        print(f"  kwargs: {task2.kwargs}")
        print(f"  queue: {task2.queue_name}")
        print(f"  priority: {task2.priority}")
    else:
        print(f"\nTask 2 not found!")
    
    # Create worker
    worker = AsyncWorker(
        task_queue=omniq._task_queue,
        result_storage=omniq._result_storage,
        event_storage=omniq._event_storage,
        queue_manager=omniq._queue_manager
    )
    worker.register_function("test_func", test_func)
    
    # Test function resolution
    print(f"\nTesting function resolution...")
    if task1:
        try:
            resolved_func = worker._resolve_task_function(task1)
            print(f"Task 1 function resolved: {resolved_func}")
            print(f"Function signature: {resolved_func.__code__.co_varnames[:resolved_func.__code__.co_argcount]}")
        except Exception as e:
            print(f"Task 1 function resolution failed: {e}")
    
    if task2:
        try:
            resolved_func = worker._resolve_task_function(task2)
            print(f"Task 2 function resolved: {resolved_func}")
            print(f"Function signature: {resolved_func.__code__.co_varnames[:resolved_func.__code__.co_argcount]}")
        except Exception as e:
            print(f"Task 2 function resolution failed: {e}")
    
    # Test function invocation manually
    print(f"\nTesting function invocation...")
    if task1:
        try:
            result1 = await worker._invoke_function(test_func, task1.args, task1.kwargs)
            print(f"Task 1 manual invocation result: {result1}")
        except Exception as e:
            print(f"Task 1 manual invocation failed: {e}")
    
    if task2:
        try:
            result2 = await worker._invoke_function(test_func, task2.args, task2.kwargs)
            print(f"Task 2 manual invocation result: {result2}")
        except Exception as e:
            print(f"Task 2 manual invocation failed: {e}")
    
    # Process tasks
    print(f"\nProcessing tasks...")
    try:
        result1 = await worker.process_single_task(["test_queue", "high_priority"])
        print(f"Result 1: {result1}")
        if result1:
            print(f"  Status: {result1.status}")
            print(f"  Result: {result1.result}")
            print(f"  Error: {result1.error}")
    except Exception as e:
        print(f"Processing task 1 failed: {e}")
    
    try:
        result2 = await worker.process_single_task(["test_queue", "high_priority"])
        print(f"Result 2: {result2}")
        if result2:
            print(f"  Status: {result2.status}")
            print(f"  Result: {result2.result}")
            print(f"  Error: {result2.error}")
    except Exception as e:
        print(f"Processing task 2 failed: {e}")
    
    await omniq.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_function_call())