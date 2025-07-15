"""
Example demonstrating the File Storage Backend for OmniQ.

This example shows how to use the file-based storage backend with fsspec
for tasks, results, events, and schedules.
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

from omniq.backend.file import FileBackend
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType


async def basic_file_storage_example():
    """Basic example using local file storage."""
    print("=== Basic File Storage Example ===")
    
    # Create file backend with local storage
    backend = FileBackend(
        base_dir="./example_data",
        fs_protocol="file"
    )
    
    async with backend:
        # Get storage components
        task_queue = backend.get_task_queue()
        result_storage = backend.get_result_storage()
        event_storage = backend.get_event_storage()
        schedule_storage = backend.get_schedule_storage()
        
        # Create and enqueue a task
        task = Task(
            func="math.add",
            args=(10, 20),
            queue_name="default",
            status=TaskStatus.PENDING
        )
        
        await task_queue.enqueue(task)
        print(f"Enqueued task: {task.id}")
        
        # Dequeue the task
        dequeued_task = await task_queue.dequeue(["default"])
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
        
            # Create and store a result
            result = TaskResult(
                task_id=task.id,
                status=ResultStatus.SUCCESS,
                result=30,
                execution_time=0.001
            )
            
            await result_storage.set(result)
            print(f"Stored result for task: {result.task_id}")
            
            # Retrieve the result
            retrieved_result = await result_storage.get(task.id)
            if retrieved_result:
                print(f"Retrieved result: {retrieved_result.result}")
        
        # Create and store an event
        event = TaskEvent(
            task_id=task.id,
            event_type=EventType.COMPLETED,
            message="Task completed successfully",
            details={"execution_time": 0.001}
        )
        
        await event_storage.log_event(event)
        print(f"Stored event: {event.id}")
        
        # Create and store a schedule
        schedule = Schedule(
            schedule_type=ScheduleType.CRON,
            func="daily_report",
            cron_expression="0 9 * * *",  # Daily at 9 AM
            queue_name="scheduled"
        )
        
        await schedule_storage.save_schedule(schedule)
        print(f"Stored schedule: {schedule.id}")
        
        # List all tasks in queue
        tasks = await task_queue.list_tasks(queue_name="default")
        print(f"Tasks in queue: {len(tasks)}")
        
        # List all results
        results = await result_storage.list_results()
        print(f"Total results: {len(results)}")
        
        # List all events
        events = await event_storage.get_events()
        print(f"Total events: {len(events)}")
        
        # List all schedules
        schedules = await schedule_storage.list_schedules()
        print(f"Total schedules: {len(schedules)}")


async def advanced_file_storage_example():
    """Advanced example with custom configuration."""
    print("\n=== Advanced File Storage Example ===")
    
    # Create file backend with custom configuration
    backend = FileBackend(
        base_dir="./advanced_data",
        fs_protocol="file",
        fs_kwargs={}
    )
    
    async with backend:
        task_queue = backend.get_task_queue()
        result_storage = backend.get_result_storage()
        
        # Enqueue multiple tasks
        tasks = []
        for i in range(5):
            task = Task(
                func="process_data",
                args=(f"data_{i}",),
                queue_name="batch",
                status=TaskStatus.PENDING,
                priority=i % 3  # Different priorities
            )
            tasks.append(task)
            await task_queue.enqueue(task)
        
        print(f"Enqueued {len(tasks)} batch tasks")
        
        # Process tasks by priority
        processed = 0
        while processed < len(tasks):
            task = await task_queue.dequeue(["batch"])
            if task:
                print(f"Processing task {task.id} (priority: {task.priority})")
                
                # Simulate processing
                await asyncio.sleep(0.1)
                
                # Store result
                result = TaskResult(
                    task_id=task.id,
                    status=ResultStatus.SUCCESS,
                    result=f"processed_{task.args[0]}",
                    execution_time=0.1
                )
                await result_storage.set(result)
                processed += 1
            else:
                break
        
        print(f"Processed {processed} tasks")
        
        # Get results
        all_results = await result_storage.list_results()
        success_results = [r for r in all_results if r.status == ResultStatus.SUCCESS]
        print(f"Successful results: {len(success_results)}")


def sync_file_storage_example():
    """Example using synchronous file storage."""
    print("\n=== Synchronous File Storage Example ===")
    
    # Create file backend
    backend = FileBackend(base_dir="./sync_data")
    
    with backend:
        # Get sync storage components
        task_queue = backend.get_task_queue(async_mode=False)
        result_storage = backend.get_result_storage(async_mode=False)
        
        # Create and enqueue a task
        task = Task(
            func="sync_operation",
            args=("sync_data",),
            queue_name="sync",
            status=TaskStatus.PENDING
        )
        
        # Use sync methods from the file storage classes
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(task_queue.enqueue(task))
            print(f"Enqueued sync task: {task.id}")
            
            # Dequeue and process
            dequeued_task = loop.run_until_complete(task_queue.dequeue(["sync"]))
            if dequeued_task:
                print(f"Dequeued sync task: {dequeued_task.id}")
                
                # Store result
                result = TaskResult(
                    task_id=dequeued_task.id,
                    status=ResultStatus.SUCCESS,
                    result="sync_processed",
                    execution_time=0.05
                )
                
                loop.run_until_complete(result_storage.set(result))
                print(f"Stored sync result for: {result.task_id}")
                
                # Retrieve result
                retrieved_result = loop.run_until_complete(result_storage.get(dequeued_task.id))
                if retrieved_result:
                    print(f"Retrieved sync result: {retrieved_result.result}")
        finally:
            loop.close()


async def cleanup_example():
    """Example demonstrating cleanup operations."""
    print("\n=== Cleanup Example ===")
    
    backend = FileBackend(base_dir="./cleanup_data")
    
    async with backend:
        task_queue = backend.get_task_queue()
        result_storage = backend.get_result_storage()
        
        # Create tasks with different TTLs
        for i in range(3):
            task = Task(
                func="temp_task",
                args=(i,),
                queue_name="temp",
                status=TaskStatus.PENDING,
                ttl=timedelta(seconds=1) if i == 0 else timedelta(hours=1)  # First task expires in 1 second
            )
            await task_queue.enqueue(task)
        
        print("Created tasks with different TTLs")
        
        # Wait for first task to expire
        await asyncio.sleep(2)
        
        # Run cleanup
        stats = await backend.cleanup_expired()
        print(f"Cleanup stats: {stats}")
        
        # Check remaining tasks
        remaining_tasks = await task_queue.list_tasks(queue_name="temp")
        print(f"Remaining tasks after cleanup: {len(remaining_tasks)}")


async def url_based_example():
    """Example using URL-based backend creation."""
    print("\n=== URL-based Backend Example ===")
    
    # Create backend from URL
    backend = FileBackend.from_url("file:///tmp/omniq_url_test")
    
    async with backend:
        task_queue = backend.get_task_queue()
        
        task = Task(
            func="url_test",
            args=("test",),
            queue_name="url_test",
            status=TaskStatus.PENDING
        )
        
        await task_queue.enqueue(task)
        print(f"Enqueued task via URL backend: {task.id}")
        
        # Verify task was stored
        tasks = await task_queue.list_tasks(queue_name="url_test")
        print(f"Tasks in URL backend: {len(tasks)}")


async def main():
    """Run all examples."""
    print("File Storage Backend Examples")
    print("=" * 50)
    
    # Clean up any existing data
    import shutil
    for path in ["./example_data", "./advanced_data", "./sync_data", "./cleanup_data"]:
        if Path(path).exists():
            shutil.rmtree(path)
    
    try:
        await basic_file_storage_example()
        await advanced_file_storage_example()
        sync_file_storage_example()
        await cleanup_example()
        await url_based_example()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())