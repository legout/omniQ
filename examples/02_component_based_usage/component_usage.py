"""
Component-Based Usage Example

This example demonstrates how to use OmniQ components individually, providing maximum
flexibility by decoupling the task queue, result storage, and worker components.
"""

import datetime as dt
from omniq.queue import FileQueue
from omniq.results import SQLiteResultStorage
from omniq.workers import ThreadPoolWorker


def main():
    """Main example showing component-based usage"""
    
    # Create components individually
    queue = FileQueue(
        base_dir="some/path"
    )

    result_store = SQLiteResultStorage(
        base_dir="some/path"
    )

    # Create worker with reference to queue and result store
    worker = ThreadPoolWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=20
    )

    # Define a task
    def simple_task(name):
        print(f"Hello {name}")
        return name

    print("Starting worker...")
    # Start the worker
    worker.start()

    print("Enqueueing task...")
    # Enqueue a task
    from omniq.models.task import Task
    task = Task(
        func_name=simple_task.__name__,
        args=("Tom",),
        kwargs={}
    )
    task_id = queue.enqueue(
        task=task,
        queue_name="low"
    )

    print(f"Enqueued task with ID: {task_id}")

    # Get the result
    result = result_store.get_result(task_id)
    print(f"Task result: {result}")

    print("Stopping worker...")
    # Stop the worker
    worker.stop()


def context_manager_example():
    """Example using context managers for proper resource management"""
    
    # Define a task
    def simple_task(name):
        print(f"Hello {name}")
        return name

    # Using context managers for automatic resource cleanup
    with FileQueue(
        base_dir="some/path"
    ) as queue, SQLiteResultStorage(
        base_dir="some/path"
    ) as result_store, ThreadPoolWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=10
    ) as worker:
        
        print("Enqueueing task with context managers...")
        from omniq.models.task import Task
        task = Task(
            func_name=simple_task.__name__,
            args=("Tom",),
            kwargs={}
        )
        task_id = queue.enqueue(task=task)
        print(f"Enqueued task with ID: {task_id}")
        
        result = result_store.get_result(task_id)
        print(f"Context manager result: {result}")


def mixed_backends_example():
    """Example showing how to mix different backends for different components"""
    
    from omniq.results import FileResultStorage
    from omniq.workers import AsyncWorker
    
    # Define a task
    def simple_task(name):
        print(f"Processing {name} with mixed backends")
        return f"Processed: {name}"

    # Mix different backends:
    # - File-based task queue for simplicity
    # - File result storage for structured data
    queue = FileQueue(
        base_dir="./queue_storage"
    )

    result_store = FileResultStorage(
        base_dir="./result_storage"
    )

    # Use async worker for better I/O performance
    worker = AsyncWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=5
    )

    print("Starting mixed backends example...")
    
    with queue, result_store, event_store, worker:
        # Enqueue multiple tasks to different queues
        task_ids = []
        for i in range(3):
            from omniq.models.task import Task
            task = Task(
                func_name=simple_task.__name__,
                args=(f"Task-{i+1}",),
                kwargs={}
            )
            task_id = queue.enqueue(task=task)
            task_ids.append(task_id)
            print(f"Enqueued task {i+1} with ID: {task_id}")

        # Get results
        for task_id in task_ids:
            result = result_store.get_result(task_id)
            print(f"Result for {task_id}: {result}")


def priority_queue_example():
    """Example demonstrating priority queue processing"""
    
    from omniq.queue import SQLiteQueue
    from omniq.workers import ThreadPoolWorker
    
    # Define tasks with different priorities
    def urgent_task(message):
        print(f"🚨 URGENT: {message}")
        return f"urgent_result: {message}"
    
    def normal_task(message):
        print(f"📋 Normal: {message}")
        return f"normal_result: {message}"
    
    def low_priority_task(message):
        print(f"⏳ Low priority: {message}")
        return f"low_result: {message}"

    # Create SQLite queue with priority queues
    queue = SQLiteQueue(
        base_dir="./priority_storage"
    )

    result_store = SQLiteResultStorage(
        base_dir="./priority_storage"
    )

    worker = ThreadPoolWorker(
        task_queue=queue,
        result_store=result_store,
        max_workers=3
    )

    print("Starting priority queue example...")
    
    with queue, result_store, worker:
        # Enqueue tasks in mixed order - worker will process by priority
        task_ids = []
        
        # Enqueue low priority first
        from omniq.models.task import Task
        low_task = Task(
            func_name=low_priority_task.__name__,
            args=("This should run last",),
            kwargs={}
        )
        low_id = queue.enqueue(task=low_task, queue_name="low")
        task_ids.append(("low", low_id))
        
        # Then normal priority
        normal_task_obj = Task(
            func_name=normal_task.__name__,
            args=("This should run second",),
            kwargs={}
        )
        normal_id = queue.enqueue(task=normal_task_obj, queue_name="medium")
        task_ids.append(("medium", normal_id))
        
        # Finally high priority (but will be processed first)
        high_task_obj = Task(
            func_name=urgent_task.__name__,
            args=("This should run first",),
            kwargs={}
        )
        high_id = queue.enqueue(task=high_task_obj, queue_name="high")
        task_ids.append(("high", high_id))

        print("Tasks enqueued. Worker will process high -> medium -> low priority.")
        
        # Get results
        for priority, task_id in task_ids:
            result = result_store.get_result(task_id)
            print(f"[{priority}] Result: {result}")


if __name__ == "__main__":
    print("=== Component-Based Usage Examples ===\n")
    
    print("1. Basic component-based usage:")
    main()
    
    print("\n2. Context manager example:")
    context_manager_example()
    
    print("\n3. Mixed backends example:")
    mixed_backends_example()
    
    print("\n4. Priority queue example:")
    priority_queue_example()
    
    print("\n=== All examples completed ===")