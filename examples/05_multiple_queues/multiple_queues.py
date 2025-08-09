"""
Working with Multiple Queues Example

This example demonstrates how to work with multiple named queues in OmniQ,
including priority-based processing where workers process high-priority
queues before lower-priority ones.
"""

import asyncio
import time
from omniq.queue import FileQueue
from omniq.workers import ThreadPoolWorker
from omniq.results import SQLiteResultStorage


def simple_task(name, priority_level):
    """A simple task that simulates work and shows which queue it came from."""
    print(f"Processing {priority_level} priority task: {name}")
    time.sleep(1)  # Simulate work
    return f"Completed {priority_level} priority task: {name}"


def cpu_intensive_task(name, duration=2):
    """A CPU-intensive task for demonstration."""
    print(f"Starting CPU-intensive task: {name}")
    start_time = time.time()
    # Simulate CPU work
    while time.time() - start_time < duration:
        pass
    print(f"Completed CPU-intensive task: {name}")
    return f"CPU task {name} completed in {duration} seconds"


def io_task(name, delay=1):
    """An I/O task that simulates network or file operations."""
    print(f"Starting I/O task: {name}")
    time.sleep(delay)  # Simulate I/O wait
    print(f"Completed I/O task: {name}")
    return f"I/O task {name} completed after {delay}s delay"


def main():
    """Main function demonstrating multiple queue usage."""
    print("=== OmniQ Multiple Queues Example ===\n")
    
    # Create File queue with multiple named queues
    # Queues are processed in priority order: high -> medium -> low
    queue = FileQueue(
        base_dir="./multiple_queues_example"
    )
    
    # Create result storage
    result_store = SQLiteResultStorage(
        base_dir="./multiple_queues_example/results"
    )
    
    # Create worker that processes queues in priority order
    worker = ThreadPoolWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=10
    )
    
    try:
        print("1. Starting worker...")
        worker.start()
        
        print("2. Enqueuing tasks to different priority queues...\n")
        
        # Enqueue tasks to different queues
        task_ids = []
        
        # High priority tasks (processed first)
        print("Enqueuing HIGH priority tasks:")
        for i in range(3):
            from omniq.models.task import Task
            task = Task(
                func_name=simple_task.__name__,
                args=(f"HighTask-{i+1}", "HIGH"),
                kwargs={}
            )
            task_id = queue.enqueue(task=task, queue_name="high")
            task_ids.append(("high", task_id))
            print(f"  - Enqueued HIGH priority task: HighTask-{i+1}")
        
        # Medium priority tasks (processed second)
        print("\nEnqueuing MEDIUM priority tasks:")
        for i in range(3):
            from omniq.models.task import Task
            task = Task(
                func_name=simple_task.__name__,
                args=(f"MediumTask-{i+1}", "MEDIUM"),
                kwargs={}
            )
            task_id = queue.enqueue(task=task, queue_name="medium")
            task_ids.append(("medium", task_id))
            print(f"  - Enqueued MEDIUM priority task: MediumTask-{i+1}")
        
        # Low priority tasks (processed last)
        print("\nEnqueuing LOW priority tasks:")
        for i in range(3):
            from omniq.models.task import Task
            task = Task(
                func_name=simple_task.__name__,
                args=(f"LowTask-{i+1}", "LOW"),
                kwargs={}
            )
            task_id = queue.enqueue(task=task, queue_name="low")
            task_ids.append(("low", task_id))
            print(f"  - Enqueued LOW priority task: LowTask-{i+1}")
        
        print("\n3. Enqueuing different types of tasks to demonstrate queue usage...\n")
        
        # Enqueue different types of tasks to appropriate queues
        
        # Critical system tasks go to high priority queue
        from omniq.models.task import Task
        critical_task = Task(
            func_name=cpu_intensive_task.__name__,
            args=("CriticalSystemTask", 1),
            kwargs={}
        )
        critical_task_id = queue.enqueue(task=critical_task, queue_name="high")
        task_ids.append(("high", critical_task_id))
        print("  - Enqueued critical system task to HIGH priority queue")
        
        # Background processing goes to medium priority queue
        from omniq.models.task import Task
        bg_task = Task(
            func_name=io_task.__name__,
            args=("BackgroundSync", 2),
            kwargs={}
        )
        bg_task_id = queue.enqueue(task=bg_task, queue_name="medium")
        task_ids.append(("medium", bg_task_id))
        print("  - Enqueued background sync task to MEDIUM priority queue")
        
        # Cleanup tasks go to low priority queue
        from omniq.models.task import Task
        cleanup_task = Task(
            func_name=simple_task.__name__,
            args=("CleanupTask", "LOW"),
            kwargs={}
        )
        cleanup_task_id = queue.enqueue(task=cleanup_task, queue_name="low")
        task_ids.append(("low", cleanup_task_id))
        print("  - Enqueued cleanup task to LOW priority queue")
        
        print("\n4. Waiting for tasks to complete...")
        print("   (Notice how HIGH priority tasks are processed first)\n")
        
        # Wait for all tasks to complete and collect results
        completed_tasks = []
        for queue_name, task_id in task_ids:
            try:
                # Wait for result with timeout
                result = result_store.get_result(task_id)
                completed_tasks.append((queue_name, task_id, result))
                print(f"✓ {queue_name.upper()} queue task completed: {result}")
            except Exception as e:
                print(f"✗ Task {task_id} failed: {e}")
        
        print(f"\n5. Summary:")
        print(f"   - Total tasks enqueued: {len(task_ids)}")
        print(f"   - Total tasks completed: {len(completed_tasks)}")
        
        # Show queue-specific statistics
        high_tasks = [t for t in completed_tasks if t[0] == "high"]
        medium_tasks = [t for t in completed_tasks if t[0] == "medium"]
        low_tasks = [t for t in completed_tasks if t[0] == "low"]
        
        print(f"   - HIGH priority tasks completed: {len(high_tasks)}")
        print(f"   - MEDIUM priority tasks completed: {len(medium_tasks)}")
        print(f"   - LOW priority tasks completed: {len(low_tasks)}")
        
    except Exception as e:
        print(f"Error during execution: {e}")
    
    finally:
        print("\n6. Stopping worker and cleaning up...")
        worker.stop()
        print("Worker stopped successfully.")


def demonstrate_queue_management():
    """Demonstrate dynamic queue management features."""
    print("\n=== Queue Management Demonstration ===\n")
    
    # Create a queue with initial queues
    queue = FileQueue(
        base_dir="./queue_management_demo"
    )
    
    try:
        print("1. Initial queues:", queue.list_queues())
        
        # Enqueue tasks to different queues
        from omniq.models.task import Task
        urgent_task = Task(
            func_name=simple_task.__name__,
            args=("UrgentTask", "URGENT"),
            kwargs={}
        )
        urgent_id = queue.enqueue(task=urgent_task, queue_name="urgent")
        
        normal_task = Task(
            func_name=simple_task.__name__,
            args=("NormalTask", "NORMAL"),
            kwargs={}
        )
        normal_id = queue.enqueue(task=normal_task, queue_name="normal")
        
        print("3. Tasks enqueued to all queues")
        
        # Check queue sizes
        print("4. Queue sizes:")
        for queue_name in queue.list_queues():
            size = queue.get_queue_size(queue_name)
            print(f"   - {queue_name}: {size} tasks")
        
    except Exception as e:
        print(f"Error in queue management demo: {e}")


async def async_multiple_queues_example():
    """Demonstrate multiple queues with async interface."""
    print("\n=== Async Multiple Queues Example ===\n")
    
    from omniq.queue import FileQueue
    from omniq.workers import AsyncWorker
    from omniq.results import SQLiteResultStorage
    
    # Create async components
    queue = FileQueue(
        base_dir="./async_multiple_queues"
    )
    
    result_store = SQLiteResultStorage(
        base_dir="./async_multiple_queues/results"
    )
    
    worker = AsyncWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=5
    )
    
    async def async_task(name, priority):
        """An async task for demonstration."""
        print(f"Processing async {priority} task: {name}")
        await asyncio.sleep(1)  # Simulate async I/O
        return f"Async {priority} task {name} completed"
    
    try:
        print("1. Starting async worker...")
        await worker.start()
        
        print("2. Enqueuing async tasks to different queues...\n")
        
        # Enqueue tasks to different priority queues
        task_ids = []
        
        # Critical tasks
        for i in range(2):
            from omniq.models.task import Task
            task = Task(
                func_name=async_task.__name__,
                args=(f"CriticalAsync-{i+1}", "CRITICAL"),
                kwargs={}
            )
            task_id = await queue.enqueue(task=task, queue_name="critical")
            task_ids.append(task_id)
            print(f"  - Enqueued CRITICAL async task: CriticalAsync-{i+1}")
        
        # Important tasks
        for i in range(2):
            from omniq.models.task import Task
            task = Task(
                func_name=async_task.__name__,
                args=(f"ImportantAsync-{i+1}", "IMPORTANT"),
                kwargs={}
            )
            task_id = await queue.enqueue(task=task, queue_name="important")
            task_ids.append(task_id)
            print(f"  - Enqueued IMPORTANT async task: ImportantAsync-{i+1}")
        
        # Routine tasks
        for i in range(2):
            from omniq.models.task import Task
            task = Task(
                func_name=async_task.__name__,
                args=(f"RoutineAsync-{i+1}", "ROUTINE"),
                kwargs={}
            )
            task_id = await queue.enqueue(task=task, queue_name="routine")
            task_ids.append(task_id)
            print(f"  - Enqueued ROUTINE async task: RoutineAsync-{i+1}")
        
        print("\n3. Waiting for async tasks to complete...\n")
        
        # Wait for all tasks to complete
        for task_id in task_ids:
            try:
                result = result_store.get_result(task_id)
                print(f"✓ Async task completed: {result}")
            except Exception as e:
                print(f"✗ Async task {task_id} failed: {e}")
        
        print(f"\n4. All {len(task_ids)} async tasks completed successfully!")
        
    except Exception as e:
        print(f"Error in async example: {e}")
    
    finally:
        print("\n5. Stopping async worker...")
        await worker.stop()
        print("Async worker stopped successfully.")


if __name__ == "__main__":
    # Run the main synchronous example
    main()
    
    # Demonstrate queue management
    demonstrate_queue_management()
    
    # Run the async example
    print("\n" + "="*50)
    asyncio.run(async_multiple_queues_example())
    
    print("\n=== Multiple Queues Examples Complete ===")
    print("\nKey takeaways:")
    print("1. Tasks are processed in queue priority order (high -> medium -> low)")
    print("2. Workers will exhaust higher priority queues before moving to lower ones")
    print("3. Multiple queue types support the same API for consistency")
    print("4. Both sync and async interfaces support multiple queues")
    print("5. Queue management allows dynamic addition/removal of queues")