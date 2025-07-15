"""
PostgreSQL Backend Example for OmniQ

This example demonstrates how to use the PostgreSQL backend with OmniQ
for persistent task queue, result storage, event logging, and scheduling.
"""

import asyncio
from datetime import datetime, timedelta
from omniq.backend.postgres import create_postgres_backend, create_async_postgres_backend
from omniq.models.task import Task
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType


def example_task(x: int, y: int) -> int:
    """Simple example task function."""
    return x + y


async def async_example():
    """Demonstrate async PostgreSQL backend usage."""
    print("=== Async PostgreSQL Backend Example ===")
    
    # Create async backend
    backend = create_async_postgres_backend(
        host="localhost",
        port=5432,
        database="omniq_test",
        username="postgres",
        password="password",
        schema="omniq_async"
    )
    
    async with backend:
        # Create a task
        task = Task(
            func="examples.postgres_backend_example.example_task",
            args=(10, 20),
            queue_name="math_queue",
            priority=1
        )
        
        print(f"Created task: {task.id}")
        
        # Enqueue the task
        await backend.task_queue.enqueue(task)
        print("Task enqueued successfully")
        
        # Dequeue the task
        dequeued_task = await backend.task_queue.dequeue(["math_queue"])
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
            
            # Create and store a result
            result = TaskResult(
                task_id=dequeued_task.id,
                status=ResultStatus.SUCCESS,
                result=30,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                execution_time=0.001
            )
            
            await backend.result_storage.set(result)
            print("Result stored successfully")
            
            # Retrieve the result
            retrieved_result = await backend.result_storage.get(dequeued_task.id)
            if retrieved_result:
                print(f"Retrieved result: {retrieved_result.result}")
            
            # Log an event
            event = TaskEvent(
                task_id=dequeued_task.id,
                event_type=EventType.COMPLETED,
                message="Task completed successfully",
                timestamp=datetime.utcnow()
            )
            
            await backend.event_storage.log_event(event)
            print("Event logged successfully")
            
            # Retrieve events
            events = await backend.event_storage.get_events(task_id=dequeued_task.id)
            print(f"Retrieved {len(events)} events")
        
        # Create a schedule
        schedule = Schedule(
            func="examples.postgres_backend_example.example_task",
            args=(5, 15),
            schedule_type=ScheduleType.INTERVAL,
            interval=timedelta(minutes=5),
            queue_name="scheduled_queue"
        )
        
        await backend.schedule_storage.save_schedule(schedule)
        print(f"Schedule saved: {schedule.id}")
        
        # List schedules
        schedules = await backend.schedule_storage.list_schedules()
        print(f"Total schedules: {len(schedules)}")


def sync_example():
    """Demonstrate sync PostgreSQL backend usage."""
    print("\n=== Sync PostgreSQL Backend Example ===")
    
    # Create sync backend
    backend = create_postgres_backend(
        host="localhost",
        port=5432,
        database="omniq_test",
        username="postgres",
        password="password",
        schema="omniq_sync"
    )
    
    with backend:
        # Create a task
        task = Task(
            func="examples.postgres_backend_example.example_task",
            args=(100, 200),
            queue_name="sync_queue",
            priority=2
        )
        
        print(f"Created task: {task.id}")
        
        # Enqueue the task
        backend.task_queue.enqueue_sync(task)
        print("Task enqueued successfully")
        
        # Get queue size
        queue_size = backend.task_queue.get_queue_size_sync("sync_queue")
        print(f"Queue size: {queue_size}")
        
        # Dequeue the task
        dequeued_task = backend.task_queue.dequeue_sync(["sync_queue"])
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
            
            # Create and store a result
            result = TaskResult(
                task_id=dequeued_task.id,
                status=ResultStatus.SUCCESS,
                result=300,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                execution_time=0.002
            )
            
            backend.result_storage.set_sync(result)
            print("Result stored successfully")
            
            # List results
            results = backend.result_storage.list_results_sync(limit=10)
            print(f"Total results: {len(results)}")


def connection_example():
    """Demonstrate connection management."""
    print("\n=== Connection Management Example ===")
    
    backend = create_postgres_backend(
        host="localhost",
        port=5432,
        database="omniq_test",
        username="postgres",
        password="password"
    )
    
    # Manual connection management
    backend.connect()
    print("Connected to PostgreSQL")
    
    # Use the backend
    task = Task(func="examples.postgres_backend_example.example_task", args=(1, 2))
    backend.task_queue.enqueue_sync(task)
    print("Task enqueued")
    
    # Manual disconnection
    backend.disconnect()
    print("Disconnected from PostgreSQL")


if __name__ == "__main__":
    print("PostgreSQL Backend Example")
    print("=" * 50)
    print()
    print("Prerequisites:")
    print("1. PostgreSQL server running on localhost:5432")
    print("2. Database 'omniq_test' created")
    print("3. User 'postgres' with password 'password'")
    print("4. asyncpg installed: pip install asyncpg")
    print()
    
    try:
        # Run async example
        asyncio.run(async_example())
        
        # Run sync example
        sync_example()
        
        # Run connection example
        connection_example()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure PostgreSQL is running and configured correctly.")