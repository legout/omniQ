"""
Basic usage example for OmniQ.

This example demonstrates how to use OmniQ for basic task queue operations
including task submission, execution, and result retrieval.
"""

import asyncio
import time
from datetime import timedelta

from omniq import OmniQ, Task


# Example task functions
def add_numbers(a: int, b: int) -> int:
    """Simple addition task."""
    return a + b


def slow_task(duration: int = 5) -> str:
    """A task that takes some time to complete."""
    time.sleep(duration)
    return f"Task completed after {duration} seconds"


def failing_task() -> str:
    """A task that always fails."""
    raise ValueError("This task always fails")


async def main():
    """Main example function."""
    print("=== OmniQ Basic Usage Example ===\n")
    
    # Initialize OmniQ with SQLite backend
    async with OmniQ() as omniq:
        print("✓ Connected to OmniQ with SQLite backend")
        
        # Example 1: Submit a simple task
        print("\n1. Submitting a simple addition task...")
        task_id = await omniq.submit_task(
            func_name="add_numbers",
            args=(10, 20),
            queue="math",
            priority=1
        )
        print(f"   Task submitted with ID: {task_id}")
        
        # Example 2: Submit a task with delay
        print("\n2. Submitting a delayed task...")
        delayed_task_id = await omniq.submit_task(
            func_name="slow_task",
            kwargs={"duration": 2},
            delay=timedelta(seconds=3),
            queue="slow_tasks"
        )
        print(f"   Delayed task submitted with ID: {delayed_task_id}")
        
        # Example 3: Submit a task with TTL
        print("\n3. Submitting a task with TTL...")
        ttl_task_id = await omniq.submit_task(
            func_name="add_numbers",
            args=(5, 15),
            ttl=timedelta(minutes=5),
            metadata={"description": "Task with 5-minute TTL"}
        )
        print(f"   TTL task submitted with ID: {ttl_task_id}")
        
        # Example 4: Submit a failing task with retries
        print("\n4. Submitting a failing task with retries...")
        failing_task_id = await omniq.submit_task(
            func_name="failing_task",
            retry_attempts=2,
            retry_delay=1.0,
            queue="error_prone"
        )
        print(f"   Failing task submitted with ID: {failing_task_id}")
        
        # Example 5: Get task information
        print("\n5. Retrieving task information...")
        task = await omniq.get_task(task_id)
        if task:
            print(f"   Task {task_id}:")
            print(f"     Function: {task.func}")
            print(f"     Args: {task.args}")
            print(f"     Queue: {task.queue_name}")
            print(f"     Status: {task.status}")
            print(f"     Created: {task.created_at}")
        
        # Example 6: List tasks by queue
        print("\n6. Listing tasks in 'math' queue...")
        math_tasks = await omniq.get_tasks_by_queue("math", limit=5)
        print(f"   Found {len(math_tasks)} tasks in 'math' queue")
        for task in math_tasks:
            print(f"     - {task.id}: {task.func}{task.args} [{task.status}]")
        
        # Example 7: Get task events
        print(f"\n7. Getting events for task {task_id}...")
        events = await omniq.get_task_events(task_id)
        print(f"   Found {len(events)} events:")
        for event in events:
            print(f"     - {event.timestamp}: {event.event_type} - {event.message}")
        
        # Example 8: Cleanup expired tasks
        print("\n8. Cleaning up expired tasks...")
        cleanup_stats = await omniq.cleanup_expired()
        print(f"   Cleanup stats: {cleanup_stats}")
        
        print("\n=== Example completed successfully! ===")


def sync_example():
    """Synchronous version of the example."""
    print("=== OmniQ Synchronous Usage Example ===\n")
    
    # Initialize OmniQ with SQLite backend (sync)
    with OmniQ() as omniq:
        print("✓ Connected to OmniQ with SQLite backend (sync)")
        
        # Submit a simple task synchronously
        print("\n1. Submitting a simple task (sync)...")
        task_id = omniq.submit_task_sync(
            func_name="add_numbers",
            args=(100, 200),
            queue="sync_math"
        )
        print(f"   Task submitted with ID: {task_id}")
        
        # Get task information synchronously
        print("\n2. Retrieving task information (sync)...")
        task = omniq.get_task_sync(task_id)
        if task:
            print(f"   Task {task_id}: {task.func}{task.args} [{task.status}]")
        
        print("\n=== Sync example completed successfully! ===")


def decorator_example():
    """Example using the task decorator."""
    print("=== OmniQ Task Decorator Example ===\n")
    
    # Initialize OmniQ
    omniq = OmniQ()
    
    # Register tasks using decorator
    @omniq.task(name="multiply", queue="math", priority=2)
    def multiply_numbers(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y
    
    @omniq.task(name="greet", queue="messages")
    def greet_user(name: str, greeting: str = "Hello") -> str:
        """Greet a user."""
        return f"{greeting}, {name}!"
    
    async def run_decorator_example():
        async with omniq:
            print("✓ Connected to OmniQ")
            
            # Submit tasks using the decorator methods
            print("\n1. Submitting tasks using decorators...")
            
            # Submit multiply task
            multiply_task_id = await multiply_numbers.submit(6, 7)
            print(f"   Multiply task submitted: {multiply_task_id}")
            
            # Submit greet task
            greet_task_id = await greet_user.submit("Alice", greeting="Hi")
            print(f"   Greet task submitted: {greet_task_id}")
            
            # List registered tasks
            print(f"\n2. Registered tasks: {omniq.list_registered_tasks()}")
            
            print("\n=== Decorator example completed successfully! ===")
    
    # Run the async example
    asyncio.run(run_decorator_example())


if __name__ == "__main__":
    # Run async example
    asyncio.run(main())
    
    print("\n" + "="*50 + "\n")
    
    # Run sync example
    sync_example()
    
    print("\n" + "="*50 + "\n")
    
    # Run decorator example
    decorator_example()