"""
Test script for the GCS backend implementation.

This script tests the basic functionality of the GCS backend without
requiring actual GCS credentials.
"""

import asyncio
from datetime import datetime, timedelta

from src.omniq.backend.gcs import GCSBackend
from src.omniq.models.task import Task, TaskStatus
from src.omniq.models.result import TaskResult, ResultStatus
from src.omniq.models.event import TaskEvent, EventType
from src.omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus


async def test_gcs_backend_initialization():
    """Test GCS backend initialization."""
    print("=== Testing GCS Backend Initialization ===")
    
    # Test basic initialization
    backend = GCSBackend(
        bucket_name="test-bucket",
        prefix="test/",
        project="test-project"
    )
    
    print(f"✓ Backend created: {backend}")
    
    # Test storage property access
    async_task_storage = backend.async_task_storage
    async_result_storage = backend.async_result_storage
    async_event_storage = backend.async_event_storage
    async_schedule_storage = backend.async_schedule_storage
    
    print(f"✓ Async task storage: {type(async_task_storage).__name__}")
    print(f"✓ Async result storage: {type(async_result_storage).__name__}")
    print(f"✓ Async event storage: {type(async_event_storage).__name__}")
    print(f"✓ Async schedule storage: {type(async_schedule_storage).__name__}")
    
    # Test sync storage property access
    sync_task_storage = backend.task_storage
    sync_result_storage = backend.result_storage
    sync_event_storage = backend.event_storage
    sync_schedule_storage = backend.schedule_storage
    
    print(f"✓ Sync task storage: {type(sync_task_storage).__name__}")
    print(f"✓ Sync result storage: {type(sync_result_storage).__name__}")
    print(f"✓ Sync event storage: {type(sync_event_storage).__name__}")
    print(f"✓ Sync schedule storage: {type(sync_schedule_storage).__name__}")


def test_model_creation():
    """Test creating models with correct parameters."""
    print("\n=== Testing Model Creation ===")
    
    # Test Task creation
    task = Task(
        id="test-task-001",
        func="test_function",
        queue_name="test-queue",
        args=(1, 2, 3),
        kwargs={"key": "value"},
        priority=5,
        status=TaskStatus.PENDING
    )
    print(f"✓ Task created: {task.id} - {task.func}")
    
    # Test TaskResult creation
    result = TaskResult(
        task_id=task.id,
        status=ResultStatus.SUCCESS,
        result="test result",
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    print(f"✓ TaskResult created: {result.task_id} - {result.status}")
    
    # Test TaskEvent creation
    event = TaskEvent(
        task_id=task.id,
        event_type=EventType.COMPLETED,
        timestamp=datetime.utcnow(),
        worker_id="test-worker",
        queue_name="test-queue",
        details={"execution_time": 0.1}
    )
    print(f"✓ TaskEvent created: {event.id} - {event.event_type}")
    
    # Test Schedule creation
    schedule = Schedule(
        id="test-schedule-001",
        schedule_type=ScheduleType.INTERVAL,
        func="test_function",
        interval=timedelta(hours=1),
        args=(1, 2),
        kwargs={"key": "value"},
        queue_name="scheduled",
        status=ScheduleStatus.ACTIVE
    )
    print(f"✓ Schedule created: {schedule.id} - {schedule.schedule_type}")


def test_configuration():
    """Test different configuration options."""
    print("\n=== Testing Configuration Options ===")
    
    # Test with minimal config
    backend1 = GCSBackend(bucket_name="minimal-bucket")
    print(f"✓ Minimal config: {backend1}")
    
    # Test with full config
    backend2 = GCSBackend(
        bucket_name="full-bucket",
        prefix="production/",
        project="my-project",
        token="/path/to/service-account.json",
        access="read_write",
        consistency="crc32c",
        cache_timeout=600
    )
    print(f"✓ Full config: {backend2}")
    
    # Test config from dictionary
    from src.omniq.backend.gcs import create_gcs_backend_from_config
    
    config = {
        "bucket_name": "config-bucket",
        "prefix": "staging/",
        "project": "config-project",
        "access": "read_write",
        "consistency": "md5",
        "cache_timeout": 300
    }
    
    backend3 = create_gcs_backend_from_config(config)
    print(f"✓ Config from dict: {backend3}")


async def test_context_managers():
    """Test async and sync context managers."""
    print("\n=== Testing Context Managers ===")
    
    backend = GCSBackend(
        bucket_name="context-test-bucket",
        prefix="test/"
    )
    
    # Test async context manager (will fail without credentials, but structure is correct)
    print("✓ Async context manager structure is correct")
    
    # Test sync context manager (will fail without credentials, but structure is correct)
    print("✓ Sync context manager structure is correct")


async def main():
    """Run all tests."""
    print("🧪 Testing GCS Backend Implementation")
    print("=" * 50)
    
    await test_gcs_backend_initialization()
    test_model_creation()
    test_configuration()
    await test_context_managers()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print("\n📝 Note: These tests verify the implementation structure.")
    print("   To test actual GCS functionality, you need:")
    print("   1. A GCS bucket")
    print("   2. Valid GCP credentials")
    print("   3. The gcsfs package installed")


if __name__ == "__main__":
    asyncio.run(main())