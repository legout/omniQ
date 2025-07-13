#!/usr/bin/env python3
"""
Basic OmniQ Usage Example

This example demonstrates the core functionality of OmniQ:
- Enqueueing tasks
- Processing tasks with different worker types
- Getting results
- Event monitoring

Run with: python example_basic.py
"""

import asyncio
import time
from typing import Any

import omniq


# Example task functions
def simple_task(x: int, y: int) -> int:
    """A simple synchronous task."""
    time.sleep(0.1)  # Simulate some work
    return x + y


async def async_task(name: str, delay: float = 0.1) -> str:
    """A simple asynchronous task."""
    await asyncio.sleep(delay)
    return f"Hello, {name}!"


def cpu_intensive_task(n: int) -> int:
    """A CPU-intensive task suitable for process workers."""
    # Calculate sum of squares (CPU intensive)
    result = sum(i * i for i in range(n))
    return result


def failing_task() -> None:
    """A task that always fails."""
    raise ValueError("This task is designed to fail!")


async def main():
    """Main example function."""
    print("🚀 OmniQ Basic Usage Example")
    print("=" * 50)
    
    # Create OmniQ instance with in-memory SQLite storage
    async with omniq.AsyncOmniQ() as queue:
        print("✅ OmniQ started successfully")
        
        # Example 1: Simple synchronous task
        print("\n📋 Example 1: Simple synchronous task")
        task1 = await queue.enqueue(simple_task, 10, 20, priority=1)
        print(f"   Enqueued task: {task1.id}")
        
        result1 = await queue.wait_for_result(task1.id, timeout=5)
        print(f"   Result: {result1.result}")
        
        # Example 2: Async task
        print("\n📋 Example 2: Asynchronous task")
        task2 = await queue.enqueue(async_task, "OmniQ", delay=0.2)
        print(f"   Enqueued task: {task2.id}")
        
        result2 = await queue.wait_for_result(task2.id, timeout=5)
        print(f"   Result: {result2.result}")
        
        # Example 3: Multiple tasks with different priorities
        print("\n📋 Example 3: Multiple tasks with priorities")
        tasks = []
        
        # Enqueue low priority tasks first
        for i in range(3):
            task = await queue.enqueue(
                simple_task, 
                i, i + 1, 
                priority=1,  # Low priority
                queue=f"queue_{i % 2}"  # Different queues
            )
            tasks.append(task)
            print(f"   Enqueued low priority task: {task.id}")
        
        # Enqueue high priority task
        high_priority_task = await queue.enqueue(
            simple_task, 
            100, 200, 
            priority=10  # High priority
        )
        tasks.append(high_priority_task)
        print(f"   Enqueued HIGH priority task: {high_priority_task.id}")
        
        # Get all results
        print("   Getting results...")
        for task in tasks:
            result = await queue.wait_for_result(task.id, timeout=5)
            print(f"   Task {task.id}: {result.result} (priority: {task.priority})")
        
        # Example 4: Task with failure handling
        print("\n📋 Example 4: Failure handling")
        failing_task_obj = await queue.enqueue(failing_task, max_retries=2)
        print(f"   Enqueued failing task: {failing_task_obj.id}")
        
        try:
            await queue.wait_for_result(failing_task_obj.id, timeout=5)
        except ValueError as e:
            print(f"   ✅ Expected failure caught: {e}")
        
        # Get the actual result to see error details
        failed_result = await queue.get_result(failing_task_obj.id)
        if failed_result and failed_result.error:
            print(f"   Error type: {failed_result.error.error_type}")
            print(f"   Error message: {failed_result.error.error_message}")
        
        # Example 5: Delayed task execution
        print("\n📋 Example 5: Delayed execution")
        delayed_task = await queue.enqueue(
            simple_task, 
            5, 10, 
            delay=1.0  # Execute after 1 second
        )
        print(f"   Enqueued delayed task: {delayed_task.id}")
        print("   Waiting for delayed execution...")
        
        start_time = time.time()
        delayed_result = await queue.wait_for_result(delayed_task.id, timeout=5)
        execution_time = time.time() - start_time
        print(f"   Result: {delayed_result.result} (executed after {execution_time:.1f}s)")
        
        # Example 6: System health check
        print("\n📋 Example 6: System status")
        health = await queue.health_check()
        print(f"   OmniQ Status: {health['omniq_started']}")
        print(f"   Workers: {len(health['workers'])} active")
        
        for worker in health['workers']:
            print(f"   - Worker {worker['worker_id']}: {worker['state']}")
            print(f"     Tasks processed: {worker['tasks_processed']}")
            print(f"     Tasks failed: {worker['tasks_failed']}")
        
        # Example 7: Queue statistics
        print("\n📋 Example 7: Queue statistics")
        queue_size = await queue.get_queue_size("default")
        print(f"   Default queue size: {queue_size}")
        
        # Show component health
        components = health.get('components', {})
        for name, component in components.items():
            if component:
                print(f"   {name}: {component.get('status', 'unknown')}")
        
        print("\n🎉 All examples completed successfully!")


def sync_example():
    """Example using synchronous API."""
    print("\n🔄 Synchronous API Example")
    print("=" * 30)
    
    # Use synchronous wrapper
    with omniq.OmniQ() as queue:
        print("✅ Sync OmniQ started")
        
        # Enqueue a simple task
        task = queue.enqueue(simple_task, 42, 8)
        print(f"   Enqueued task: {task.id}")
        
        # Wait for result
        result = queue.wait_for_result(task.id, timeout=5)
        print(f"   Result: {result.result}")
        
        print("✅ Sync example completed")


if __name__ == "__main__":
    # Run async example
    asyncio.run(main())
    
    # Run sync example
    sync_example()
    
    print("\n✨ OmniQ example finished! ✨")