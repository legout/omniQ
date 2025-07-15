"""
Example demonstrating the Google Cloud Storage (GCS) backend for OmniQ.

This example shows how to use the GCS backend for task queue, result storage,
event storage, and schedule storage using Google Cloud Storage.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

from omniq.backend.gcs import GCSBackend
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus


def example_task_function(x: int, y: int) -> int:
    """Example task function."""
    return x + y


async def async_gcs_backend_example():
    """Demonstrate async GCS backend usage."""
    print("=== Async GCS Backend Example ===")
    
    # Initialize GCS backend
    # Note: You'll need to set up GCP credentials and have a GCS bucket
    backend = GCSBackend(
        bucket_name="your-omniq-bucket",  # Replace with your bucket name
        prefix="omniq/",
        project="your-gcp-project",  # Replace with your GCP project ID
        # token="/path/to/service-account.json",  # Optional: path to service account JSON
    )
    
    try:
        async with backend:
            print("✓ GCS Backend async context entered successfully")
            
            # Access async storage components
            task_storage = backend.async_task_storage
            result_storage = backend.async_result_storage
            event_storage = backend.async_event_storage
            schedule_storage = backend.async_schedule_storage
            
            print(f"  Task storage: {type(task_storage).__name__}")
            print(f"  Result storage: {type(result_storage).__name__}")
            print(f"  Event storage: {type(event_storage).__name__}")
            print(f"  Schedule storage: {type(schedule_storage).__name__}")
            
            # Create and enqueue a task
            task = Task(
                id="task-001",
                func="example_task_function",
                queue_name="default",
                args=(10, 20),
                kwargs={},
                priority=1,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING
            )
            
            print(f"\n📝 Enqueueing task: {task.id}")
            await task_storage.enqueue(task)
            
            # Get queue size
            queue_size = await task_storage.get_queue_size("default")
            print(f"📊 Queue size: {queue_size}")
            
            # Dequeue the task
            print(f"\n🔄 Dequeuing task from 'default' queue...")
            dequeued_task = await task_storage.dequeue(["default"])
            if dequeued_task:
                print(f"✓ Dequeued task: {dequeued_task.id}")
                print(f"  Status: {dequeued_task.status}")
                print(f"  Args: {dequeued_task.args}")
            
            # Create and store a result
            if dequeued_task:
                result = TaskResult(
                    task_id=dequeued_task.id,
                    status=ResultStatus.SUCCESS,
                    result=30,  # 10 + 20
                    created_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                
                print(f"\n💾 Storing result for task: {result.task_id}")
                await result_storage.set(result)
                
                # Retrieve the result
                retrieved_result = await result_storage.get(dequeued_task.id)
                if retrieved_result:
                    print(f"✓ Retrieved result: {retrieved_result.result}")
                    print(f"  Status: {retrieved_result.status}")
            
            # Log an event
            event = TaskEvent(
                id="event-001",
                task_id=task.id,
                event_type=EventType.COMPLETED,
                timestamp=datetime.utcnow(),
                worker_id="worker-001",
                queue_name="default",
                details={"execution_time": 0.1}
            )
            
            print(f"\n📋 Logging event: {event.id}")
            await event_storage.log_event(event)
            
            # Get events
            events = await event_storage.get_events(task_id=task.id)
            print(f"✓ Retrieved {len(events)} events for task {task.id}")
            
            # Create and save a schedule
            schedule = Schedule(
                id="schedule-001",
                schedule_type=ScheduleType.INTERVAL,
                func="example_task_function",
                interval=timedelta(hours=1),  # Every hour
                args=(5, 15),
                kwargs={},
                queue_name="scheduled",
                status=ScheduleStatus.ACTIVE,
                created_at=datetime.utcnow(),
                next_run=datetime.utcnow() + timedelta(hours=1)
            )
            
            print(f"\n⏰ Saving schedule: {schedule.id}")
            await schedule_storage.save_schedule(schedule)
            
            # List schedules
            schedules = await schedule_storage.list_schedules()
            print(f"✓ Retrieved {len(schedules)} schedules")
            
        print("✓ Async context manager exited successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("Note: Make sure you have:")
        print("  1. A GCS bucket created")
        print("  2. Proper GCP credentials configured")
        print("  3. The gcsfs package installed: pip install gcsfs")


def sync_gcs_backend_example():
    """Demonstrate sync GCS backend usage."""
    print("\n=== Sync GCS Backend Example ===")
    
    # Initialize GCS backend
    backend = GCSBackend(
        bucket_name="your-omniq-bucket",  # Replace with your bucket name
        prefix="omniq/",
        project="your-gcp-project",  # Replace with your GCP project ID
    )
    
    try:
        with backend:
            print("✓ GCS Backend sync context entered successfully")
            
            # Access sync storage components
            print(f"Sync task storage: {type(backend.task_storage).__name__}")
            print(f"Sync result storage: {type(backend.result_storage).__name__}")
            print(f"Sync event storage: {type(backend.event_storage).__name__}")
            print(f"Sync schedule storage: {type(backend.schedule_storage).__name__}")
            
            # Example sync operations
            task_storage = backend.task_storage
            
            # Create a simple task
            task = Task(
                id="sync-task-001",
                func="example_task_function",
                queue_name="sync-queue",
                args=(100, 200),
                kwargs={},
                priority=2,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING
            )
            
            print(f"\n📝 Enqueueing sync task: {task.id}")
            # Access the actual sync storage implementation
            from omniq.storage.gcs import GCSQueue
            sync_task_storage = backend.task_storage
            if isinstance(sync_task_storage, GCSQueue):
                sync_task_storage.enqueue_sync(task)
                
                # Get queue size
                queue_size = sync_task_storage.get_queue_size_sync("sync-queue")
                print(f"📊 Sync queue size: {queue_size}")
                
                # List tasks
                tasks = sync_task_storage.list_tasks_sync(queue_name="sync-queue")
                print(f"✓ Found {len(tasks)} tasks in sync-queue")
            else:
                print("✗ Could not access sync methods")
            
        print("✓ Sync context manager exited successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def configuration_example():
    """Show different ways to configure the GCS backend."""
    print("\n=== GCS Backend Configuration Examples ===")
    
    # 1. Basic configuration
    print("1. Basic configuration:")
    backend1 = GCSBackend(
        bucket_name="my-omniq-bucket",
        prefix="production/",
    )
    print(f"   {backend1}")
    
    # 2. With explicit project and credentials
    print("\n2. With explicit project and credentials:")
    backend2 = GCSBackend(
        bucket_name="my-omniq-bucket",
        prefix="staging/",
        project="my-gcp-project",
        token="/path/to/service-account.json",
    )
    print(f"   {backend2}")
    
    # 3. With custom access and consistency settings
    print("\n3. With custom access and consistency settings:")
    backend3 = GCSBackend(
        bucket_name="my-omniq-bucket",
        prefix="development/",
        access="read_write",
        consistency="crc32c",
        cache_timeout=600,
    )
    print(f"   {backend3}")
    
    # 4. From configuration dictionary
    print("\n4. From configuration dictionary:")
    from omniq.backend.gcs import create_gcs_backend_from_config
    
    config = {
        "bucket_name": "my-omniq-bucket",
        "prefix": "omniq/",
        "project": "my-gcp-project",
        "access": "read_write",
        "consistency": "md5",
        "cache_timeout": 300,
        "gcs_kwargs": {
            "block_size": 5 * 1024 * 1024,  # 5MB blocks
        }
    }
    
    backend4 = create_gcs_backend_from_config(config)
    print(f"   {backend4}")


async def main():
    """Run all examples."""
    print("🚀 OmniQ GCS Backend Examples")
    print("=" * 50)
    
    # Configuration examples
    configuration_example()
    
    # Note: The actual backend examples require valid GCS credentials
    # and a bucket, so they're commented out by default
    
    print("\n" + "=" * 50)
    print("📝 Note: To run the actual GCS backend examples:")
    print("1. Create a GCS bucket")
    print("2. Set up GCP credentials (service account or gcloud auth)")
    print("3. Install gcsfs: pip install gcsfs")
    print("4. Update the bucket_name and project in the examples above")
    print("5. Uncomment the lines below:")
    
    # Uncomment these lines when you have GCS set up:
    # await async_gcs_backend_example()
    # sync_gcs_backend_example()


if __name__ == "__main__":
    asyncio.run(main())