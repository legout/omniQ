"""
Process Pool Worker Example

This example demonstrates how to use the ProcessPoolWorker for CPU-intensive tasks
that benefit from true parallelism and process isolation.
"""

import asyncio
import time
from omniq.workers import ProcessPoolWorker, WorkerPool, WorkerType
from omniq.models.task import Task
from omniq.storage.memory import MemoryQueue, MemoryResultStorage, MemoryEventStorage


def cpu_intensive_task(n):
    """CPU-intensive task that benefits from process isolation."""
    result = 0
    for i in range(n * 100000):
        result += i * i
    return result


def fibonacci(n):
    """Calculate Fibonacci number - CPU-intensive recursive task."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n):
    """Calculate factorial - CPU-intensive task."""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def prime_check(n):
    """Check if a number is prime - CPU-intensive task."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


async def example_1_basic_usage():
    """Example 1: Basic ProcessPoolWorker usage."""
    print("=" * 60)
    print("Example 1: Basic ProcessPoolWorker Usage")
    print("=" * 60)
    
    # Create storage components
    task_queue = MemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    # Function registry
    function_registry = {
        "cpu_intensive_task": cpu_intensive_task,
        "fibonacci": fibonacci,
        "factorial": factorial,
        "prime_check": prime_check,
    }
    
    # Create ProcessPoolWorker
    async with ProcessPoolWorker(
        worker_id="cpu-worker",
        task_queue=task_queue,
        result_storage=result_storage,
        event_storage=event_storage,
        function_registry=function_registry,
        max_workers=4,  # Use 4 processes
    ) as worker:
        
        print(f"Created ProcessPoolWorker: {worker}")
        print(f"Process pool size: {worker.get_process_pool_size()}")
        
        # Execute a CPU-intensive task
        task = Task(func="cpu_intensive_task", args=(1000,))
        
        start_time = time.time()
        result = await worker.execute_task(task)
        end_time = time.time()
        
        print(f"Task executed successfully: {result.is_successful()}")
        print(f"Result: {result.result}")
        print(f"Execution time: {end_time - start_time:.2f} seconds")
        print(f"Task ID: {result.task_id}")


async def example_2_concurrent_execution():
    """Example 2: Concurrent execution of multiple CPU-intensive tasks."""
    print("\n" + "=" * 60)
    print("Example 2: Concurrent CPU-Intensive Task Execution")
    print("=" * 60)
    
    # Create storage components
    task_queue = MemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    # Function registry
    function_registry = {
        "fibonacci": fibonacci,
        "factorial": factorial,
        "prime_check": prime_check,
    }
    
    # Create ProcessPoolWorker with multiple processes
    async with ProcessPoolWorker(
        worker_id="concurrent-worker",
        task_queue=task_queue,
        result_storage=result_storage,
        event_storage=event_storage,
        function_registry=function_registry,
        max_workers=3,  # Use 3 processes for parallel execution
    ) as worker:
        
        print(f"Created ProcessPoolWorker with {worker.get_process_pool_size()} processes")
        
        # Create multiple different CPU-intensive tasks
        tasks = [
            Task(func="fibonacci", args=(35,)),
            Task(func="factorial", args=(20,)),
            Task(func="prime_check", args=(982451653,)),  # Large prime number
            Task(func="fibonacci", args=(40,)),
            Task(func="prime_check", args=(982451654,)),  # Not prime
        ]
        
        print(f"Executing {len(tasks)} CPU-intensive tasks concurrently...")
        
        start_time = time.time()
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[
            worker.execute_task(task) for task in tasks
        ])
        
        end_time = time.time()
        
        print(f"All tasks completed in {end_time - start_time:.2f} seconds")
        print("\nResults:")
        
        task_names = ["fibonacci(35)", "factorial(20)", "prime_check(982451653)", 
                     "fibonacci(40)", "prime_check(982451654)"]
        
        for i, (result, task_name) in enumerate(zip(results, task_names)):
            print(f"  {task_name}: {result.result} (success: {result.is_successful()})")


async def example_3_process_pool_worker_pool():
    """Example 3: ProcessPoolWorker with WorkerPool."""
    print("\n" + "=" * 60)
    print("Example 3: ProcessPoolWorker with WorkerPool")
    print("=" * 60)
    
    # Create storage components
    task_queue = MemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    # Connect storage components
    await task_queue.connect()
    await result_storage.connect()
    await event_storage.connect()
    
    try:
        # Function registry
        function_registry = {
            "cpu_intensive_task": cpu_intensive_task,
            "fibonacci": fibonacci,
        }
        
        # Create WorkerPool with ProcessPoolWorker type
        async with WorkerPool(
            worker_type=WorkerType.PROCESS_POOL,
            max_workers=2,  # 2 process pool workers
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        ) as pool:
            
            print(f"Created WorkerPool: {pool}")
            print(f"Worker type: {pool.worker_type}")
            print(f"Number of workers: {pool.get_worker_count()}")
            
            # Enqueue some tasks
            tasks = [
                Task(func="fibonacci", args=(30,)),
                Task(func="cpu_intensive_task", args=(500,)),
                Task(func="fibonacci", args=(35,)),
            ]
            
            print(f"Enqueueing {len(tasks)} tasks...")
            
            for task in tasks:
                await task_queue.enqueue(task)
            
            print("Tasks enqueued. Worker pool will process them automatically.")
            print("Note: In a real application, you would start the pool with pool.start()")
    
    finally:
        # Disconnect storage components
        await task_queue.disconnect()
        await result_storage.disconnect()
        await event_storage.disconnect()


async def example_4_error_handling():
    """Example 4: Error handling in ProcessPoolWorker."""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling in ProcessPoolWorker")
    print("=" * 60)
    
    # Create storage components
    task_queue = MemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    def error_prone_function(x):
        """Function that may raise an error."""
        if x < 0:
            raise ValueError("Negative numbers not allowed")
        return x * x
    
    # Function registry
    function_registry = {
        "error_prone_function": error_prone_function,
        "fibonacci": fibonacci,
    }
    
    # Create ProcessPoolWorker
    async with ProcessPoolWorker(
        worker_id="error-handling-worker",
        task_queue=task_queue,
        result_storage=result_storage,
        event_storage=event_storage,
        function_registry=function_registry,
        max_workers=2,
    ) as worker:
        
        print(f"Created ProcessPoolWorker: {worker}")
        
        # Test successful task
        success_task = Task(func="fibonacci", args=(10,))
        success_result = await worker.execute_task(success_task)
        
        print(f"Success task result: {success_result.result} (success: {success_result.is_successful()})")
        
        # Test error task
        error_task = Task(func="error_prone_function", args=(-5,))
        error_result = await worker.execute_task(error_task)
        
        print(f"Error task result: success={error_result.is_successful()}")
        if not error_result.is_successful():
            print(f"Error message: {error_result.error}")
        
        print("Process isolation ensures that errors in one task don't affect others.")


async def main():
    """Run all examples."""
    print("ProcessPoolWorker Examples")
    print("=" * 60)
    print("Demonstrating CPU-intensive task execution with true parallelism")
    print("and process isolation using ProcessPoolWorker.")
    
    await example_1_basic_usage()
    await example_2_concurrent_execution()
    await example_3_process_pool_worker_pool()
    await example_4_error_handling()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nKey benefits of ProcessPoolWorker:")
    print("• True parallelism for CPU-intensive tasks")
    print("• Process isolation for fault tolerance")
    print("• Automatic function picklability checking")
    print("• Configurable process pool size")
    print("• Seamless integration with OmniQ task system")


if __name__ == "__main__":
    asyncio.run(main())