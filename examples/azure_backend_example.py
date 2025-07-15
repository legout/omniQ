"""
Example demonstrating Azure Blob Storage backend usage with OmniQ.

This example shows how to:
1. Configure and use the Azure backend
2. Create and execute tasks with Azure storage
3. Handle both sync and async operations
4. Use different authentication methods
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

from omniq.backend.azure import AzureBackend
from omniq.models.task import Task
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus


def example_task_function(x: int, y: int) -> int:
    """Example task function."""
    return x + y


async def async_example():
    """Demonstrate async Azure backend usage."""
    print("=== Async Azure Backend Example ===")
    
    # Configuration options - choose one authentication method:
    
    # Option 1: Connection string (recommended for development)
    backend = AzureBackend(
        container_name="omniq-test",
        prefix="async-example/",
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    )
    
    # Option 2: Account name and key
    # backend = AzureBackend(
    #     container_name="omniq-test",
    #     prefix="async-example/",
    #     account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
    #     account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
    # )
    
    # Option 3: Service principal authentication
    # backend = AzureBackend(
    #     container_name="omniq-test",
    #     prefix="async-example/",
    #     account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
    #     tenant_id=os.getenv("AZURE_TENANT_ID"),
    #     client_id=os.getenv("AZURE_CLIENT_ID"),
    #     client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    # )
    
    async with backend:
        # Get storage instances
        task_queue = backend.async_task_storage
        result_storage = backend.async_result_storage
        event_storage = backend.async_event_storage
        schedule_storage = backend.async_schedule_storage
        
        print(f"Backend: {backend}")
        
        # Create and enqueue a task
        task = Task(
            func="example_task_function",
            id="async-task-1",
            queue_name="math",
            args=(10, 20),
            kwargs={},
            priority=1,
            run_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        print(f"Enqueueing task: {task.id}")
        await task_queue.enqueue(task)
        
        # Check queue size
        queue_size = await task_queue.get_queue_size("math")
        print(f"Queue size: {queue_size}")
        
        # Dequeue the task
        dequeued_task = await task_queue.dequeue(["math"])
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
            
            # Simulate task execution and store result
            result = TaskResult(
                task_id=dequeued_task.id,
                status=ResultStatus.SUCCESS,
                result=30,  # 10 + 20
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            
            await result_storage.set(result)
            print(f"Stored result for task: {result.task_id}")
            
            # Log an event
            event = TaskEvent(
                task_id=dequeued_task.id,
                event_type=EventType.COMPLETED,
                worker_id="async-worker-1",
                queue_name="math",
                message="Task completed successfully",
            )
            
            await event_storage.log_event(event)
            print(f"Logged event: {event.event_type.value}")
        
        # Create a schedule
        schedule = Schedule(
            schedule_type=ScheduleType.CRON,
            func="example_task_function",
            id="schedule-1",
            cron_expression="0 */6 * * *",  # Every 6 hours
            args=(10, 20),
            status=ScheduleStatus.ACTIVE,
            created_at=datetime.utcnow(),
            next_run=datetime.utcnow() + timedelta(hours=6),
        )
        
        await schedule_storage.save_schedule(schedule)
        print(f"Saved schedule: {schedule.id}")
        
        # List stored data
        tasks = await task_queue.list_tasks()
        results = await result_storage.list_results()
        events = await event_storage.get_events()
        schedules = await schedule_storage.list_schedules()
        
        print(f"Tasks: {len(tasks)}")
        print(f"Results: {len(results)}")
        print(f"Events: {len(events)}")
        print(f"Schedules: {len(schedules)}")


def sync_example():
    """Demonstrate sync Azure backend usage."""
    print("\n=== Sync Azure Backend Example ===")
    
    # Create backend with connection string
    backend = AzureBackend(
        container_name="omniq-test",
        prefix="sync-example/",
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    )
    
    with backend:
        # Get storage instances
        task_queue = backend.task_storage
        result_storage = backend.result_storage
        event_storage = backend.event_storage
        schedule_storage = backend.schedule_storage
        
        print(f"Backend: {backend}")
        
        # Create and enqueue a task
        task = Task(
            func="example_task_function",
            id="sync-task-1",
            queue_name="math",
            args=(5, 15),
            kwargs={},
            priority=2,
            run_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        print(f"Enqueueing task: {task.id}")
        task_queue.enqueue_sync(task)
        
        # Check queue size
        queue_size = task_queue.get_queue_size_sync("math")
        print(f"Queue size: {queue_size}")
        
        # Dequeue the task
        dequeued_task = task_queue.dequeue_sync(["math"])
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
            
            # Simulate task execution and store result
            result = TaskResult(
                task_id=dequeued_task.id,
                status=ResultStatus.SUCCESS,
                result=20,  # 5 + 15
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            
            result_storage.set_sync(result)
            print(f"Stored result for task: {result.task_id}")
            
            # Log an event
            event = TaskEvent(
                task_id=dequeued_task.id,
                event_type=EventType.COMPLETED,
                worker_id="sync-worker-1",
                queue_name="math",
                message="Task completed successfully",
            )
            
            event_storage.log_event_sync(event)
            print(f"Logged event: {event.event_type.value}")
        
        # List stored data
        tasks = task_queue.list_tasks_sync()
        results = result_storage.list_results_sync()
        events = event_storage.get_events_sync()
        schedules = schedule_storage.list_schedules_sync()
        
        print(f"Tasks: {len(tasks)}")
        print(f"Results: {len(results)}")
        print(f"Events: {len(events)}")
        print(f"Schedules: {len(schedules)}")


def configuration_examples():
    """Show different configuration options."""
    print("\n=== Configuration Examples ===")
    
    # Example 1: Connection string (simplest)
    backend1 = AzureBackend(
        container_name="omniq-prod",
        connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
    )
    print(f"Connection string backend: {backend1}")
    
    # Example 2: Account name and key
    backend2 = AzureBackend(
        container_name="omniq-prod",
        account_name="myaccount",
        account_key="mykey"
    )
    print(f"Account key backend: {backend2}")
    
    # Example 3: Service principal
    backend3 = AzureBackend(
        container_name="omniq-prod",
        account_name="myaccount",
        tenant_id="tenant-id",
        client_id="client-id",
        client_secret="client-secret"
    )
    print(f"Service principal backend: {backend3}")
    
    # Example 4: SAS token
    backend4 = AzureBackend(
        container_name="omniq-prod",
        account_name="myaccount",
        sas_token="?sv=2020-08-04&ss=bfqt&srt=sco&sp=rwdlacupx&se=2021-01-01T00:00:00Z&st=2020-01-01T00:00:00Z&spr=https&sig=signature"
    )
    print(f"SAS token backend: {backend4}")
    
    # Example 5: Custom prefix and additional options
    backend5 = AzureBackend(
        container_name="omniq-prod",
        prefix="my-app/production/",
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        azure_additional_kwargs={
            "client_kwargs": {
                "connection_timeout": 30,
                "read_timeout": 60,
            }
        }
    )
    print(f"Custom configuration backend: {backend5}")


if __name__ == "__main__":
    # Check if Azure connection string is available
    if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
        print("Please set AZURE_STORAGE_CONNECTION_STRING environment variable")
        print("Example: export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net'")
        print("\nShowing configuration examples instead:")
        configuration_examples()
    else:
        # Run async example
        asyncio.run(async_example())
        
        # Run sync example
        sync_example()
        
        # Show configuration examples
        configuration_examples()