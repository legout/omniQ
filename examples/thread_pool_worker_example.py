"""
Example demonstrating ThreadPoolWorker usage for I/O-bound synchronous tasks.

This example shows how to use the ThreadPoolWorker for executing I/O-bound
synchronous tasks with configurable thread pool size and thread-safe execution.
"""

import asyncio
import time
from omniq.workers.thread_pool_worker import ThreadPoolWorker
from omniq.workers.pool import WorkerPool, WorkerType
from omniq.models.task import Task
from omniq.storage.sqlite import AsyncSQLiteQueue, AsyncSQLiteResultStorage, AsyncSQLiteEventStorage


# Example I/O-bound synchronous functions
def file_io_task(filename: str, content: str) -> str:
    """Simulate file I/O operation."""
    time.sleep(0.1)  # Simulate I/O delay
    return f"File '{filename}' processed with {len(content)} characters"


def network_request_task(url: str, timeout: float = 0.2) -> str:
    """Simulate network request."""
    time.sleep(timeout)  # Simulate network delay
    return f"Response from {url} received"


def database_query_task(query: str, delay: float = 0.15) -> str:
    """Simulate database query."""
    time.sleep(delay)  # Simulate database query time
    return f"Query '{query}' executed successfully"


def cpu_light_task(data: str) -> str:
    """Light CPU processing task."""
    # Simple string processing
    processed = data.upper().replace(" ", "_")
    return f"Processed: {processed}"


async def main():
    """Main example function."""
    print("=== ThreadPoolWorker Example ===\n")
    
    # Create storage components
    db_path = "example_thread_pool.db"
    task_queue = AsyncSQLiteQueue(db_path)
    result_storage = AsyncSQLiteResultStorage(db_path)
    event_storage = AsyncSQLiteEventStorage(db_path)
    
    # Connect storage components
    await task_queue.connect()
    await result_storage.connect()
    await event_storage.connect()
    
    try:
        # Create function registry
        function_registry = {
            "file_io_task": file_io_task,
            "network_request_task": network_request_task,
            "database_query_task": database_query_task,
            "cpu_light_task": cpu_light_task,
        }
        
        print("Example 1: Direct ThreadPoolWorker Usage")
        print("-" * 40)
        
        # Create ThreadPoolWorker with configurable thread pool size
        async with ThreadPoolWorker(
            worker_id="io-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=4,  # Configurable thread pool size
            task_timeout=5.0,
        ) as worker:
            
            print(f"Worker: {worker}")
            print(f"Thread pool size: {worker.get_thread_pool_size()}")
            print(f"Active tasks: {worker.get_active_task_count()}")
            
            # Execute individual tasks
            tasks = [
                Task(func="file_io_task", args=("document.txt", "Hello World!")),
                Task(func="network_request_task", args=("https://api.example.com",)),
                Task(func="database_query_task", args=("SELECT * FROM users",)),
                Task(func="cpu_light_task", args=("process this text",)),
            ]
            
            print("\nExecuting tasks concurrently...")
            start_time = time.time()
            
            # Execute tasks concurrently
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
            
            end_time = time.time()
            print(f"All tasks completed in {end_time - start_time:.2f} seconds")
            
            # Display results
            for i, result in enumerate(results):
                if result.is_successful():
                    print(f"Task {i+1}: {result.result}")
                else:
                    print(f"Task {i+1} failed: {result.error}")
        
        print("\n" + "="*50 + "\n")
        
        print("Example 2: ThreadPoolWorker with WorkerPool")
        print("-" * 40)
        
        # Use ThreadPoolWorker through WorkerPool
        async with WorkerPool(
            worker_type=WorkerType.THREAD_POOL,
            max_workers=3,  # Number of ThreadPoolWorkers
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
        ) as pool:
            
            print(f"Pool: {pool}")
            print(f"Worker count: {pool.get_worker_count()}")
            
            # Enqueue multiple tasks
            task_data = [
                ("file_io_task", ("report.pdf", "Annual Report Content")),
                ("network_request_task", ("https://service.example.com",)),
                ("database_query_task", ("UPDATE users SET active = 1",)),
                ("cpu_light_task", ("transform this data",)),
                ("file_io_task", ("config.json", '{"setting": "value"}')),
                ("network_request_task", ("https://backup.example.com",)),
            ]
            
            print(f"\nEnqueuing {len(task_data)} tasks...")
            task_ids = []
            for func_name, args in task_data:
                task = Task(func=func_name, args=args)
                await task_queue.enqueue(task)
                task_ids.append(task.id)
            
            print("Tasks enqueued. Starting pool processing...")
            
            # Start pool processing (this would normally run continuously)
            # For demo purposes, we'll process for a short time
            start_time = time.time()
            
            # In a real application, you would call pool.start() and let it run
            # Here we'll simulate by processing tasks manually
            processed_count = 0
            while processed_count < len(task_ids) and time.time() - start_time < 10:
                # Check for completed results
                for task_id in task_ids:
                    result = await result_storage.get(task_id)
                    if result and result.is_successful():
                        print(f"Completed task {task_id}: {result.result}")
                        processed_count += 1
                
                await asyncio.sleep(0.1)
            
            print(f"Processed {processed_count} tasks")
        
        print("\n" + "="*50 + "\n")
        
        print("Example 3: Error Handling and Thread Safety")
        print("-" * 40)
        
        # Add a function that might fail
        def unreliable_task(should_fail: bool) -> str:
            time.sleep(0.1)
            if should_fail:
                raise ValueError("Task intentionally failed")
            return "Task completed successfully"
        
        function_registry["unreliable_task"] = unreliable_task
        
        async with ThreadPoolWorker(
            worker_id="error-handling-worker",
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_workers=2,
            max_retries=2,  # Enable retries
        ) as worker:
            
            # Test error handling
            error_tasks = [
                Task(func="unreliable_task", args=(False,)),  # Should succeed
                Task(func="unreliable_task", args=(True,)),   # Should fail
                Task(func="unreliable_task", args=(False,)),  # Should succeed
            ]
            
            print("Testing error handling...")
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in error_tasks
            ])
            
            for i, result in enumerate(results):
                if result.is_successful():
                    print(f"Task {i+1}: SUCCESS - {result.result}")
                else:
                    print(f"Task {i+1}: FAILED - {result.error}")
        
        print("\nExample completed successfully!")
    
    finally:
        # Cleanup storage components
        await task_queue.disconnect()
        await result_storage.disconnect()
        await event_storage.disconnect()
        
        # Clean up database file
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    asyncio.run(main())