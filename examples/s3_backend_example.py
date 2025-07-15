#!/usr/bin/env python3
"""
S3 Backend Example for OmniQ

This example demonstrates how to use the S3 backend for OmniQ, which provides
S3-compatible storage for tasks, results, events, and schedules using fsspec/s3fs.

Requirements:
- boto3 (for AWS S3 authentication)
- s3fs (for S3 filesystem operations)
- fsspec (filesystem abstraction)

Install with: pip install boto3 s3fs fsspec

Usage:
    python examples/s3_backend_example.py
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from omniq.backend.s3 import S3Backend, create_s3_backend_from_config
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType


async def basic_s3_backend_example():
    """Basic example of using S3Backend directly."""
    print("=== Basic S3Backend Example ===")
    
    # Create S3 backend instance
    backend = S3Backend(
        bucket_name="my-omniq-bucket",
        prefix="omniq/dev/",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )
    
    print(f"Created S3Backend: {backend}")
    
    # Access storage components
    print(f"Task storage: {type(backend.async_task_storage).__name__}")
    print(f"Result storage: {type(backend.async_result_storage).__name__}")
    print(f"Event storage: {type(backend.async_event_storage).__name__}")
    print(f"Schedule storage: {type(backend.async_schedule_storage).__name__}")
    
    # Use async context manager
    async with backend:
        print("✓ S3Backend async context entered successfully")
        
        # Example task operations (would require actual S3 credentials)
        task = Task(
            id="example-task-1",
            func="process_data",
            args=("data.csv",),
            kwargs={"format": "csv"}
        )
        
        print(f"Created example task: {task.id}")
        
        # Example result
        result = TaskResult(
            task_id=task.id,
            status=ResultStatus.SUCCESS,
            result={"processed_rows": 1000},
            execution_time=2.5
        )
        
        print(f"Created example result: {result.task_id}")
        
        # Example event
        event = TaskEvent(
            task_id=task.id,
            event_type=EventType.COMPLETED,
            details={"duration": 2.5}
        )
        
        print(f"Created example event: {event.id}")
        
        # Example schedule
        schedule = Schedule.from_cron(
            cron_expression="0 9 * * *",  # Daily at 9 AM
            func="process_data",
            args=("data.csv",),
            kwargs={"format": "csv"}
        )
        
        print(f"Created example schedule: {schedule.id}")
    
    print("✓ S3Backend async context exited successfully")


def config_based_s3_backend_example():
    """Example of creating S3Backend from configuration."""
    print("\n=== Config-based S3Backend Example ===")
    
    # Configuration dictionary
    config = {
        "bucket_name": "my-omniq-bucket",
        "prefix": "omniq/prod/",
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region_name": "us-west-2",
        "endpoint_url": None,  # Use default AWS S3
        "s3_kwargs": {
            "use_ssl": True,
            "verify": True
        }
    }
    
    # Create backend from config
    backend = create_s3_backend_from_config(config)
    print(f"Created S3Backend from config: {backend}")
    
    # Use sync context manager
    with backend:
        print("✓ S3Backend sync context entered successfully")
        
        # Access sync storage components
        print(f"Sync task storage: {type(backend.task_storage).__name__}")
        print(f"Sync result storage: {type(backend.result_storage).__name__}")
        print(f"Sync event storage: {type(backend.event_storage).__name__}")
        print(f"Sync schedule storage: {type(backend.schedule_storage).__name__}")
    
    print("✓ S3Backend sync context exited successfully")


def s3_compatible_storage_example():
    """Example of using S3Backend with S3-compatible storage (MinIO, etc.)."""
    print("\n=== S3-Compatible Storage Example ===")
    
    # Configuration for MinIO or other S3-compatible storage
    backend = S3Backend(
        bucket_name="omniq-bucket",
        prefix="test/",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
        endpoint_url="http://localhost:9000",  # MinIO endpoint
        use_ssl=False,
        verify=False
    )
    
    print(f"Created S3Backend for MinIO: {backend}")
    
    # Storage configuration details
    storage_kwargs = backend._get_storage_kwargs()
    print("Storage configuration:")
    for key, value in storage_kwargs.items():
        if 'secret' in key.lower():
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")


async def advanced_s3_backend_example():
    """Advanced example showing S3Backend features."""
    print("\n=== Advanced S3Backend Example ===")
    
    # Create backend with custom configuration
    backend = S3Backend(
        bucket_name="advanced-omniq-bucket",
        prefix="omniq/advanced/",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="eu-west-1",
        # Custom S3 configuration
        multipart_threshold=64 * 1024 * 1024,  # 64MB
        max_concurrency=10,
        use_threads=True
    )
    
    print(f"Advanced S3Backend: {backend}")
    
    async with backend:
        # Demonstrate lazy loading of storage instances
        print("Storage instances are created lazily:")
        
        # First access creates the instance
        task_storage = backend.async_task_storage
        print(f"✓ Task storage created: {type(task_storage).__name__}")
        
        # Second access returns the same instance
        task_storage_2 = backend.async_task_storage
        assert task_storage is task_storage_2
        print("✓ Storage instance caching works correctly")
        
        # Access all storage types
        storages = {
            "task": backend.async_task_storage,
            "result": backend.async_result_storage,
            "event": backend.async_event_storage,
            "schedule": backend.async_schedule_storage
        }
        
        print("All async storage instances:")
        for name, storage in storages.items():
            print(f"  {name}: {type(storage).__name__}")
        
        # Sync storage instances
        sync_storages = {
            "task": backend.task_storage,
            "result": backend.result_storage,
            "event": backend.event_storage,
            "schedule": backend.schedule_storage
        }
        
        print("All sync storage instances:")
        for name, storage in sync_storages.items():
            print(f"  {name}: {type(storage).__name__}")


def environment_configuration_example():
    """Example of configuring S3Backend using environment variables."""
    print("\n=== Environment Configuration Example ===")
    
    # Set environment variables (in practice, these would be set externally)
    env_config = {
        "OMNIQ_S3_BUCKET": "env-omniq-bucket",
        "OMNIQ_S3_PREFIX": "omniq/env/",
        "AWS_ACCESS_KEY_ID": "your-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret-key",
        "AWS_DEFAULT_REGION": "us-east-1"
    }
    
    print("Environment configuration:")
    for key, value in env_config.items():
        if 'SECRET' in key:
            print(f"  {key}={'*' * len(value)}")
        else:
            print(f"  {key}={value}")
    
    # Create backend using environment variables
    backend = S3Backend(
        bucket_name=env_config.get("OMNIQ_S3_BUCKET", "default-bucket"),
        prefix=env_config.get("OMNIQ_S3_PREFIX", "omniq/"),
        aws_access_key_id=env_config.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=env_config.get("AWS_SECRET_ACCESS_KEY"),
        region_name=env_config.get("AWS_DEFAULT_REGION", "us-east-1")
    )
    
    print(f"Environment-configured S3Backend: {backend}")


async def main():
    """Run all S3Backend examples."""
    print("S3 Backend Examples for OmniQ")
    print("=" * 50)
    
    try:
        # Basic example
        await basic_s3_backend_example()
        
        # Config-based example
        config_based_s3_backend_example()
        
        # S3-compatible storage example
        s3_compatible_storage_example()
        
        # Advanced example
        await advanced_s3_backend_example()
        
        # Environment configuration example
        environment_configuration_example()
        
        print("\n" + "=" * 50)
        print("All S3Backend examples completed successfully!")
        print("\nNote: These examples demonstrate the S3Backend API.")
        print("To actually use S3 storage, you need:")
        print("1. Valid AWS credentials or S3-compatible storage access")
        print("2. An existing S3 bucket")
        print("3. Proper network connectivity to S3")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())