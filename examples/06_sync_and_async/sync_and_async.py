"""
Handling Both Sync and Async Tasks

This example demonstrates how OmniQ workers can seamlessly handle both synchronous 
and asynchronous tasks, showcasing the library's flexibility in mixed workload scenarios.
"""

import asyncio
import time
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.workers import AsyncWorker


def sync_task(x, y):
    """A synchronous task that performs multiplication"""
    print(f"Executing sync task: {x} * {y}")
    time.sleep(0.1)  # Simulate some work
    result = x * y
    print(f"Sync task result: {result}")
    return result


async def async_task(x, y):
    """An asynchronous task that performs addition"""
    print(f"Executing async task: {x} + {y}")
    await asyncio.sleep(0.1)  # Simulate async I/O
    result = x + y
    print(f"Async task result: {result}")
    return result


def main():
    """Main example showing mixed sync/async task execution"""
    print("=== Handling Both Sync and Async Tasks ===\n")
    
    # Create components
    queue = FileTaskQueue(project_name="sync_async_example", base_dir="./temp_storage")
    worker = AsyncWorker(queue=queue, max_workers=10)
    
    print("1. Starting AsyncWorker...")
    worker.start()
    
    print("\n2. Enqueuing mixed sync and async tasks...")
    
    # Enqueue both types of tasks
    sync_task_id = queue.enqueue(sync_task, func_args=dict(x=5, y=10))
    async_task_id = queue.enqueue(async_task, func_args=dict(x=5, y=10))
    
    print(f"   - Sync task enqueued with ID: {sync_task_id}")
    print(f"   - Async task enqueued with ID: {async_task_id}")
    
    # Wait a moment for tasks to execute
    time.sleep(1)
    
    print("\n3. Retrieving results...")
    
    # Get results (AsyncWorker handles both task types automatically)
    sync_result = worker.get_result(sync_task_id)  # Should be 50
    async_result = worker.get_result(async_task_id)  # Should be 15
    
    print(f"   - Sync task result: {sync_result}")
    print(f"   - Async task result: {async_result}")
    
    print("\n4. Stopping worker...")
    worker.stop()
    
    print("\nExample completed successfully!")


def thread_worker_example():
    """Example using ThreadWorker with mixed tasks"""
    from omniq.workers import ThreadWorker
    
    print("\n=== Using ThreadWorker with Mixed Tasks ===\n")
    
    # Create components with ThreadWorker
    queue = FileTaskQueue(project_name="thread_sync_async_example", base_dir="./temp_storage")
    worker = ThreadWorker(queue=queue, max_workers=5)
    
    print("1. Starting ThreadWorker...")
    worker.start()
    
    print("\n2. Enqueuing tasks to ThreadWorker...")
    
    # Enqueue both types of tasks
    sync_task_id = queue.enqueue(sync_task, func_args=dict(x=3, y=7))
    async_task_id = queue.enqueue(async_task, func_args=dict(x=3, y=7))
    
    print(f"   - Sync task enqueued with ID: {sync_task_id}")
    print(f"   - Async task enqueued with ID: {async_task_id}")
    
    # Wait for tasks to execute
    time.sleep(1)
    
    print("\n3. Retrieving results...")
    
    # Get results (ThreadWorker handles both task types)
    sync_result = worker.get_result(sync_task_id)  # Should be 21
    async_result = worker.get_result(async_task_id)  # Should be 10
    
    print(f"   - Sync task result: {sync_result}")
    print(f"   - Async task result: {async_result}")
    
    print("\n4. Stopping worker...")
    worker.stop()
    
    print("\nThreadWorker example completed!")


def context_manager_example():
    """Example using context managers for proper resource management"""
    print("\n=== Using Context Managers ===\n")
    
    # Using context managers for automatic cleanup
    with FileTaskQueue(project_name="context_example", base_dir="./temp_storage") as queue, \
         AsyncWorker(queue=queue, max_workers=5) as worker:
        
        print("1. Components created with context managers")
        
        print("\n2. Enqueuing tasks...")
        sync_task_id = queue.enqueue(sync_task, func_args=dict(x=2, y=8))
        async_task_id = queue.enqueue(async_task, func_args=dict(x=2, y=8))
        
        # Wait for execution
        time.sleep(1)
        
        print("\n3. Getting results...")
        sync_result = worker.get_result(sync_task_id)  # Should be 16
        async_result = worker.get_result(async_task_id)  # Should be 10
        
        print(f"   - Sync task result: {sync_result}")
        print(f"   - Async task result: {async_result}")
        
        print("\n4. Context managers will handle cleanup automatically")
    
    print("\nContext manager example completed!")


def performance_comparison():
    """Compare performance of different worker types with mixed tasks"""
    print("\n=== Performance Comparison ===\n")
    
    # Test with multiple tasks
    num_tasks = 5
    
    print(f"Testing with {num_tasks} sync and {num_tasks} async tasks each...")
    
    # AsyncWorker test
    print("\n1. Testing AsyncWorker performance...")
    start_time = time.time()
    
    with FileTaskQueue(project_name="perf_async", base_dir="./temp_storage") as queue, \
         AsyncWorker(queue=queue, max_workers=10) as worker:
        
        # Enqueue multiple tasks
        task_ids = []
        for i in range(num_tasks):
            sync_id = queue.enqueue(sync_task, func_args=dict(x=i, y=i+1))
            async_id = queue.enqueue(async_task, func_args=dict(x=i, y=i+1))
            task_ids.extend([sync_id, async_id])
        
        # Wait for completion
        time.sleep(2)
        
        # Collect results
        results = [worker.get_result(task_id) for task_id in task_ids]
        
    async_worker_time = time.time() - start_time
    print(f"   AsyncWorker completed in {async_worker_time:.2f} seconds")
    
    # ThreadWorker test
    print("\n2. Testing ThreadWorker performance...")
    start_time = time.time()
    
    from omniq.workers import ThreadWorker
    with FileTaskQueue(project_name="perf_thread", base_dir="./temp_storage") as queue, \
         ThreadWorker(queue=queue, max_workers=10) as worker:
        
        # Enqueue multiple tasks
        task_ids = []
        for i in range(num_tasks):
            sync_id = queue.enqueue(sync_task, func_args=dict(x=i, y=i+1))
            async_id = queue.enqueue(async_task, func_args=dict(x=i, y=i+1))
            task_ids.extend([sync_id, async_id])
        
        # Wait for completion
        time.sleep(2)
        
        # Collect results
        results = [worker.get_result(task_id) for task_id in task_ids]
    
    thread_worker_time = time.time() - start_time
    print(f"   ThreadWorker completed in {thread_worker_time:.2f} seconds")
    
    print(f"\nPerformance comparison completed!")
    print(f"Both workers successfully handled mixed sync/async workloads.")


if __name__ == "__main__":
    # Run all examples
    main()
    thread_worker_example()
    context_manager_example()
    performance_comparison()
    
    print("\n" + "="*50)
    print("All examples completed successfully!")
    print("="*50)