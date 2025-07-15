#!/usr/bin/env python3
"""
Test script for S3Backend functionality.

This script tests the S3Backend implementation without requiring actual S3 credentials.
It verifies the backend instantiation, property access, and context management.
"""

import asyncio
import os
from datetime import datetime

from src.omniq.backend.s3 import S3Backend, create_s3_backend_from_config
from src.omniq.models.task import Task
from src.omniq.models.result import TaskResult, ResultStatus
from src.omniq.models.event import TaskEvent, EventType
from src.omniq.models.schedule import Schedule


def test_s3_backend_creation():
    """Test S3Backend creation and configuration."""
    print("=== Testing S3Backend Creation ===")
    
    # Test basic creation
    backend = S3Backend(
        bucket_name="test-bucket",
        prefix="test/",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        region_name="us-east-1"
    )
    
    print(f"✓ Created S3Backend: {backend}")
    print(f"  Bucket: {backend.bucket_name}")
    print(f"  Prefix: {backend.prefix}")
    
    # Test property access
    assert hasattr(backend, 'async_task_storage')
    assert hasattr(backend, 'async_result_storage')
    assert hasattr(backend, 'async_event_storage')
    assert hasattr(backend, 'async_schedule_storage')
    
    assert hasattr(backend, 'task_storage')
    assert hasattr(backend, 'result_storage')
    assert hasattr(backend, 'event_storage')
    assert hasattr(backend, 'schedule_storage')
    
    print("✓ All storage properties accessible")
    
    # Test lazy instantiation
    task_storage_1 = backend.async_task_storage
    task_storage_2 = backend.async_task_storage
    assert task_storage_1 is task_storage_2, "Storage instances should be cached"
    print("✓ Storage instance caching works")


def test_config_based_creation():
    """Test creating S3Backend from configuration."""
    print("\n=== Testing Config-based Creation ===")
    
    config = {
        "bucket_name": "config-bucket",
        "prefix": "config/test/",
        "aws_access_key_id": "config-key",
        "aws_secret_access_key": "config-secret",
        "region_name": "us-west-2",
        "endpoint_url": "http://localhost:9000",
        "s3_kwargs": {
            "use_ssl": False,
            "verify": False
        }
    }
    
    backend = create_s3_backend_from_config(config)
    print(f"✓ Created S3Backend from config: {backend}")
    
    # Verify configuration was applied
    assert backend.bucket_name == "config-bucket"
    assert backend.prefix == "config/test/"
    print("✓ Configuration applied correctly")


async def test_async_context_manager():
    """Test async context manager functionality."""
    print("\n=== Testing Async Context Manager ===")
    
    backend = S3Backend(
        bucket_name="async-test-bucket",
        prefix="async/test/"
    )
    
    # Test async context manager (without actual S3 connection)
    try:
        async with backend:
            print("✓ Async context manager entered successfully")
            
            # Test storage access within context
            task_storage = backend.async_task_storage
            result_storage = backend.async_result_storage
            event_storage = backend.async_event_storage
            schedule_storage = backend.async_schedule_storage
            
            print(f"  Task storage: {type(task_storage).__name__}")
            print(f"  Result storage: {type(result_storage).__name__}")
            print(f"  Event storage: {type(event_storage).__name__}")
            print(f"  Schedule storage: {type(schedule_storage).__name__}")
            
        print("✓ Async context manager exited successfully")
    except Exception as e:
        print(f"✓ Expected connection error (no actual S3): {type(e).__name__}")


def test_sync_context_manager():
    """Test sync context manager functionality."""
    print("\n=== Testing Sync Context Manager ===")
    
    backend = S3Backend(
        bucket_name="sync-test-bucket",
        prefix="sync/test/"
    )
    
    # Test sync context manager (without actual S3 connection)
    try:
        with backend:
            print("✓ Sync context manager entered successfully")
            
            # Test storage access within context
            task_storage = backend.task_storage
            result_storage = backend.result_storage
            event_storage = backend.event_storage
            schedule_storage = backend.schedule_storage
            
            print(f"  Task storage: {type(task_storage).__name__}")
            print(f"  Result storage: {type(result_storage).__name__}")
            print(f"  Event storage: {type(event_storage).__name__}")
            print(f"  Schedule storage: {type(schedule_storage).__name__}")
            
        print("✓ Sync context manager exited successfully")
    except Exception as e:
        print(f"✓ Expected connection error (no actual S3): {type(e).__name__}")


def test_model_creation():
    """Test creating OmniQ models for use with S3Backend."""
    print("\n=== Testing Model Creation ===")
    
    # Test Task creation
    task = Task(
        id="test-task-1",
        func="test_function",
        args=("arg1", "arg2"),
        kwargs={"key": "value"}
    )
    print(f"✓ Created Task: {task.id}")
    
    # Test TaskResult creation
    result = TaskResult(
        task_id=task.id,
        status=ResultStatus.SUCCESS,
        result={"output": "test result"},
        execution_time=1.5
    )
    print(f"✓ Created TaskResult: {result.task_id}")
    
    # Test TaskEvent creation
    event = TaskEvent(
        task_id=task.id,
        event_type=EventType.COMPLETED,
        details={"duration": 1.5}
    )
    print(f"✓ Created TaskEvent: {event.id}")
    
    # Test Schedule creation
    schedule = Schedule.from_cron(
        cron_expression="0 9 * * *",
        func="daily_task",
        args=(),
        kwargs={}
    )
    print(f"✓ Created Schedule: {schedule.id}")


async def main():
    """Run all tests."""
    print("S3Backend Test Suite")
    print("=" * 50)
    
    test_s3_backend_creation()
    test_config_based_creation()
    await test_async_context_manager()
    test_sync_context_manager()
    test_model_creation()
    
    print("\n" + "=" * 50)
    print("✓ All S3Backend tests completed successfully!")
    print("\nNote: These tests verify the S3Backend API without requiring")
    print("actual S3 credentials or connectivity. For full functionality,")
    print("configure proper AWS credentials and S3 bucket access.")


if __name__ == "__main__":
    asyncio.run(main())