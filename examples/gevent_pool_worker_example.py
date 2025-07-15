"""
GeventPoolWorker Example

This example demonstrates how to use the GeventPoolWorker for high-concurrency
I/O-bound task execution using Gevent's cooperative multitasking.

Requirements:
- pip install gevent

The GeventPoolWorker is ideal for:
- I/O-bound tasks (network requests, file operations)
- High-concurrency scenarios
- Tasks that can benefit from cooperative multitasking
- Applications that need to handle many concurrent operations efficiently
"""

import asyncio
import time
from omniq.workers import GeventPoolWorker, WorkerPool, WorkerType
from omniq.models.task import Task
from omniq.storage.memory import MemoryQueue, MemoryResultStorage, MemoryEventStorage


def io_bound_task(duration: float, task_id: str) -> str:
    """
    Simulate an I/O-bound task that would benefit from cooperative multitasking.
    In a real scenario, this could be a network request, database query, etc.
    """
    import time
    time.sleep(duration)  # Simulate I/O wait
    return f"Task {task_id} completed after {duration}s"


def cpu_intensive_task(n: int) -> int:
    """
    A CPU-intensive task for comparison.
    Note: Gevent is not ideal for CPU-bound tasks.
    """
    result = 0
    for i in range(n):
        result += i * i
    return result


async def demonstrate_gevent_pool_worker():
    """Demonstrate GeventPoolWorker usage."""
    print("=== GeventPoolWorker Example ===\n")
    
    # Set up storage backends
    task_queue = MemoryQueue()
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    
    # Define function registry
    function_registry = {
        'io_bound_task': io_bound_task,
        'cpu_intensive_task': cpu_intensive_task,
    }
    
    try:
        # Create GeventPoolWorker
        print("1. Creating GeventPoolWorker...")
        worker = GeventPoolWorker(
            worker_id='gevent-demo',
            max_workers=4,  # 4 greenlets in the pool
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            task_timeout=30.0
        )
        print(f"   ✓ Created: {worker}")
        
        # Test direct task execution
        print("\n2. Testing direct task execution...")
        
        # Execute I/O-bound tasks concurrently
        print("   Executing I/O-bound tasks...")
        start_time = time.time()
        
        from datetime import datetime, timezone
        tasks = [
            Task(func='io_bound_task', args=(0.5, f'io-{i}'), created_at=datetime.now(timezone.utc))
            for i in range(6)  # 6 tasks, 4 workers
        ]
        
        async with worker:
            results = await asyncio.gather(*[
                worker.execute_task(task) for task in tasks
            ])
        
        end_time = time.time()
        
        print(f"   ✓ Completed {len(results)} I/O tasks in {end_time - start_time:.2f}s")
        for result in results:
            if result.is_successful():
                print(f"     - {result.result}")
            else:
                print(f"     - Error: {result.error}")
        
        # Test CPU-intensive task
        print("\n3. Testing CPU-intensive task...")
        cpu_task = Task(func='cpu_intensive_task', args=(1000000,))
        
        async with GeventPoolWorker(
            worker_id='gevent-cpu',
            max_workers=2,
            function_registry=function_registry
        ) as cpu_worker:
            cpu_result = await cpu_worker.execute_task(cpu_task)
        
        if cpu_result.is_successful():
            print(f"   ✓ CPU task result: {cpu_result.result}")
        else:
            print(f"   ✗ CPU task failed: {cpu_result.error}")
        
    except ImportError as e:
        print(f"⚠ GeventPoolWorker requires gevent to be installed: {e}")
        print("  Install with: pip install gevent")
        return
    
    print("\n4. Using WorkerPool with GeventPoolWorker...")
    
    try:
        # Create WorkerPool with GeventPoolWorker
        pool = WorkerPool(
            worker_type=WorkerType.GEVENT_POOL,
            max_workers=3,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry
        )
        
        print(f"   ✓ Created WorkerPool: {pool}")
        
        # Add some tasks to the queue
        for i in range(5):
            task = Task(func='io_bound_task', args=(0.3, f'queued-{i}'))
            await task_queue.enqueue(task)
        
        print("   ✓ Added 5 tasks to queue")
        print("   Note: In a real scenario, you would start the pool with:")
        print("   await pool.start(['default'])")
        
    except ImportError:
        print("   ⚠ Gevent not available for WorkerPool demo")


async def demonstrate_monkey_patching():
    """Demonstrate monkey patching capabilities."""
    print("\n=== Monkey Patching Example ===")
    
    try:
        # Create worker with monkey patching enabled
        worker = GeventPoolWorker(
            worker_id='monkey-patch-demo',
            max_workers=2,
            monkey_patch=True,  # Enable monkey patching
            function_registry={'io_bound_task': io_bound_task}
        )
        
        print("✓ GeventPoolWorker created with monkey patching enabled")
        print("  This patches standard library modules for cooperative multitasking")
        print("  Affects: socket, ssl, threading, select, subprocess, etc.")
        
        # Note: In a real application, you would use the worker here
        print("  Worker ready for cooperative I/O operations")
        
    except ImportError:
        print("⚠ Gevent not available for monkey patching demo")


def failing_task():
    """Task that always fails for error demonstration."""
    raise ValueError("This task always fails")


def timeout_task():
    """Task that times out for timeout demonstration."""
    import time
    time.sleep(10)  # Will timeout
    return "Should not reach here"


def demonstrate_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Example ===")
    
    async def run_error_demo():
        try:
            worker = GeventPoolWorker(
                worker_id='error-demo',
                max_workers=2,
                function_registry={
                    'failing_task': failing_task,
                    'timeout_task': timeout_task
                },
                task_timeout=2.0  # 2 second timeout
            )
            
            print("Testing error handling...")
            
            async with worker:
                # Test task that raises an exception
                fail_task = Task(func='failing_task')
                fail_result = await worker.execute_task(fail_task)
                
                if not fail_result.is_successful():
                    print(f"✓ Caught expected error: {fail_result.error}")
                
                # Test task that times out
                timeout_task_obj = Task(func='timeout_task')
                timeout_result = await worker.execute_task(timeout_task_obj)
                
                if not timeout_result.is_successful():
                    print(f"✓ Caught timeout error: {timeout_result.error}")
            
        except ImportError:
            print("⚠ Gevent not available for error handling demo")
    
    asyncio.run(run_error_demo())


if __name__ == "__main__":
    print("GeventPoolWorker Example")
    print("=" * 50)
    
    # Run the main demonstration
    asyncio.run(demonstrate_gevent_pool_worker())
    
    # Demonstrate monkey patching
    asyncio.run(demonstrate_monkey_patching())
    
    # Demonstrate error handling
    demonstrate_error_handling()
    
    print("\n" + "=" * 50)
    print("Example completed!")
    print("\nKey takeaways:")
    print("- GeventPoolWorker is ideal for I/O-bound tasks")
    print("- Uses cooperative multitasking for high concurrency")
    print("- Supports monkey patching for seamless integration")
    print("- Handles errors and timeouts gracefully")
    print("- Integrates with OmniQ's WorkerPool system")