"""
Example demonstrating the OmniQ worker pool functionality.

This example shows how to use different types of worker pools
to process tasks concurrently.
"""

import asyncio
import time
from omniq import OmniQ
from omniq.workers import WorkerPool, WorkerType


def cpu_intensive_task(n: int) -> int:
    """A CPU-intensive task for demonstration."""
    result = 0
    for i in range(n * 1000000):
        result += i % 7
    return result


def io_task(duration: float) -> str:
    """An I/O task simulation."""
    time.sleep(duration)
    return f"Completed after {duration} seconds"


async def async_task(message: str) -> str:
    """An async task for demonstration."""
    await asyncio.sleep(0.1)
    return f"Async: {message}"


async def main():
    """Main example function."""
    # Initialize OmniQ with SQLite backend
    omniq = OmniQ("sqlite:///worker_pool_example.db")
    
    print("=== OmniQ Worker Pool Example ===\n")
    
    # Connect to the backend
    await omniq.connect()
    
    try:
        # Create function registry for workers
        function_registry = {
            "cpu_task": cpu_intensive_task,
            "io_task": io_task,
            "async_task": async_task,
        }
        
        # Example 1: Async Worker Pool
        print("1. Testing Async Worker Pool")
        async with WorkerPool(
            worker_type=WorkerType.ASYNC,
            max_workers=3,
            task_queue=omniq._task_queue,
            result_storage=omniq._result_storage,
            event_storage=omniq._event_storage,
            function_registry=function_registry
        ) as pool:
            # Submit some async tasks
            task_ids = []
            for i in range(5):
                task_id = await omniq.submit_task("async_task", args=(f"message-{i}",))
                task_ids.append(task_id)
            
            print(f"Submitted {len(task_ids)} async tasks")
            
            # Start the pool (this will run until all tasks are processed)
            # In a real application, you might run this in the background
            await asyncio.sleep(2)  # Let tasks process
            
            # Check results
            for task_id in task_ids:
                result = await omniq.get_result(task_id)
                if result and result.is_successful():
                    print(f"Task {task_id}: {result.result}")
        
        print("\n2. Testing Thread Worker Pool")
        # Example 2: Thread Worker Pool for I/O tasks
        async with WorkerPool(
            worker_type=WorkerType.THREAD,
            max_workers=2,
            task_queue=omniq._task_queue,
            result_storage=omniq._result_storage,
            event_storage=omniq._event_storage,
            function_registry=function_registry
        ) as pool:
            # Submit some I/O tasks
            task_ids = []
            for i in range(3):
                task_id = await omniq.submit_task("io_task", args=(0.5,))
                task_ids.append(task_id)
            
            print(f"Submitted {len(task_ids)} I/O tasks")
            
            await asyncio.sleep(3)  # Let tasks process
            
            # Check results
            for task_id in task_ids:
                result = await omniq.get_result(task_id)
                if result and result.is_successful():
                    print(f"Task {task_id}: {result.result}")
        
        print("\n3. Testing Process Worker Pool")
        # Example 3: Process Worker Pool for CPU-intensive tasks
        async with WorkerPool(
            worker_type=WorkerType.PROCESS,
            max_workers=2,
            task_queue=omniq._task_queue,
            result_storage=omniq._result_storage,
            event_storage=omniq._event_storage,
            function_registry=function_registry
        ) as pool:
            # Submit some CPU-intensive tasks
            task_ids = []
            for i in range(3):
                task_id = await omniq.submit_task("cpu_task", args=(100 + i * 50,))
                task_ids.append(task_id)
            
            print(f"Submitted {len(task_ids)} CPU-intensive tasks")
            
            await asyncio.sleep(5)  # Let tasks process
            
            # Check results
            for task_id in task_ids:
                result = await omniq.get_result(task_id)
                if result and result.is_successful():
                    print(f"Task {task_id}: {result.result}")
        
        print("\n=== Example completed ===")
    
    finally:
        # Disconnect from the backend
        await omniq.disconnect()


if __name__ == "__main__":
    asyncio.run(main())