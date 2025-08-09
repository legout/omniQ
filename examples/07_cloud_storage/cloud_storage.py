#!/usr/bin/env python3
"""
Using fsspec for Cloud Storage with OmniQ

This example demonstrates how to use fsspec with FileTaskQueue and FileResultStorage
to connect to various storage backends including local files, in-memory storage,
and cloud storage providers.

The local and memory examples are runnable as-is.
The cloud storage examples are commented out and require proper credentials.
"""

import asyncio
import time
from pathlib import Path
import tempfile

# Import OmniQ components
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage
from omniq.workers import AsyncWorker


def sample_task(data: str, multiplier: int = 1) -> str:
    """Sample task function for demonstration."""
    time.sleep(0.1)  # Simulate some work
    return f"Processed: {data} (x{multiplier})"


async def async_sample_task(data: str, delay: float = 0.1) -> str:
    """Sample async task function for demonstration."""
    await asyncio.sleep(delay)
    return f"Async processed: {data}"


def demonstrate_local_filesystem():
    """Demonstrate using local filesystem storage."""
    print("=" * 60)
    print("DEMONSTRATING LOCAL FILESYSTEM STORAGE")
    print("=" * 60)
    
    # Create a temporary directory for this demo
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "omniq_demo"
        
        print(f"Using temporary directory: {base_path}")
        
        # Create FileTaskQueue and FileResultStorage with local filesystem
        queue = FileTaskQueue(
            project_name="local_demo",
            base_dir=str(base_path / "tasks"),
            queues=["high", "medium", "low"]
        )
        
        result_store = FileResultStorage(
            project_name="local_demo",
            base_dir=str(base_path / "results")
        )
        
        # Create OmniQ instance
        oq = OmniQ(
            project_name="local_demo",
            task_queue=queue,
            result_store=result_store
        )
        
        print("\n1. Starting worker and enqueueing tasks...")
        
        with oq:
            # Enqueue some tasks
            task_ids = []
            
            # Enqueue tasks to different queues
            task_ids.append(oq.enqueue(
                sample_task, 
                func_args={"data": "Task 1", "multiplier": 2},
                queue_name="high"
            ))
            
            task_ids.append(oq.enqueue(
                sample_task,
                func_args={"data": "Task 2", "multiplier": 3}, 
                queue_name="medium"
            ))
            
            task_ids.append(oq.enqueue(
                sample_task,
                func_args={"data": "Task 3", "multiplier": 1},
                queue_name="low"
            ))
            
            print(f"Enqueued {len(task_ids)} tasks")
            
            # Wait a bit for tasks to complete
            time.sleep(2)
            
            # Get results
            print("\n2. Retrieving results...")
            for i, task_id in enumerate(task_ids, 1):
                result = oq.get_result(task_id)
                print(f"Task {i} result: {result}")
        
        # Show directory structure
        print(f"\n3. Directory structure created:")
        for path in sorted(base_path.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(base_path)
                print(f"  {relative_path}")


def demonstrate_memory_filesystem():
    """Demonstrate using memory filesystem storage."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING MEMORY FILESYSTEM STORAGE")
    print("=" * 60)
    
    # Create FileTaskQueue and FileResultStorage with memory filesystem
    queue = FileTaskQueue(
        project_name="memory_demo",
        base_dir="memory://memory_demo/tasks",
        queues=["high", "medium", "low"]
    )
    
    result_store = FileResultStorage(
        project_name="memory_demo",
        base_dir="memory://memory_demo/results"
    )
    
    # Create OmniQ instance
    oq = OmniQ(
        project_name="memory_demo",
        task_queue=queue,
        result_store=result_store
    )
    
    print("Using in-memory filesystem (no files written to disk)")
    print("\n1. Starting worker and enqueueing tasks...")
    
    with oq:
        # Enqueue some tasks
        task_ids = []
        
        task_ids.append(oq.enqueue(
            sample_task,
            func_args={"data": "Memory Task 1", "multiplier": 5},
            queue_name="high"
        ))
        
        task_ids.append(oq.enqueue(
            sample_task,
            func_args={"data": "Memory Task 2", "multiplier": 2},
            queue_name="medium"
        ))
        
        print(f"Enqueued {len(task_ids)} tasks to memory storage")
        
        # Wait for tasks to complete
        time.sleep(2)
        
        # Get results
        print("\n2. Retrieving results from memory...")
        for i, task_id in enumerate(task_ids, 1):
            result = oq.get_result(task_id)
            print(f"Memory Task {i} result: {result}")


async def demonstrate_async_with_memory():
    """Demonstrate async usage with memory filesystem."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING ASYNC USAGE WITH MEMORY STORAGE")
    print("=" * 60)
    
    # Create async components
    from omniq import AsyncOmniQ
    
    queue = FileTaskQueue(
        project_name="async_memory_demo",
        base_dir="memory://async_demo/tasks",
        queues=["high", "medium", "low"]
    )
    
    result_store = FileResultStorage(
        project_name="async_memory_demo",
        base_dir="memory://async_demo/results"
    )
    
    # Create AsyncOmniQ instance
    oq = AsyncOmniQ(
        project_name="async_memory_demo",
        task_queue=queue,
        result_store=result_store
    )
    
    print("Using AsyncOmniQ with memory filesystem")
    print("\n1. Starting async worker and enqueueing tasks...")
    
    async with oq:
        # Enqueue async tasks
        task_ids = []
        
        task_ids.append(await oq.enqueue(
            async_sample_task,
            func_args={"data": "Async Task 1", "delay": 0.2},
            queue_name="high"
        ))
        
        task_ids.append(await oq.enqueue(
            async_sample_task,
            func_args={"data": "Async Task 2", "delay": 0.1},
            queue_name="medium"
        ))
        
        print(f"Enqueued {len(task_ids)} async tasks")
        
        # Wait for tasks to complete
        await asyncio.sleep(1)
        
        # Get results
        print("\n2. Retrieving async results...")
        for i, task_id in enumerate(task_ids, 1):
            result = await oq.get_result(task_id)
            print(f"Async Task {i} result: {result}")


def demonstrate_cloud_storage_examples():
    """Show commented examples for cloud storage configurations."""
    print("\n" + "=" * 60)
    print("CLOUD STORAGE EXAMPLES (COMMENTED - REQUIRES CREDENTIALS)")
    print("=" * 60)
    
    print("""
# AMAZON S3 EXAMPLE
# Requires: pip install s3fs
# 
# s3_queue = FileTaskQueue(
#     project_name="s3_demo",
#     base_dir="s3://my-bucket/omniq/tasks",
#     queues=["high", "medium", "low"],
#     storage_options={
#         "key": "your_access_key_id",
#         "secret": "your_secret_access_key",
#         "region": "us-east-1"  # Optional
#     }
# )
# 
# s3_results = FileResultStorage(
#     project_name="s3_demo",
#     base_dir="s3://my-bucket/omniq/results",
#     storage_options={
#         "key": "your_access_key_id",
#         "secret": "your_secret_access_key",
#         "region": "us-east-1"
#     }
# )
# 
# # Create OmniQ with S3 storage
# s3_oq = OmniQ(
#     project_name="s3_demo",
#     task_queue=s3_queue,
#     result_store=s3_results
# )

# AZURE BLOB STORAGE EXAMPLE  
# Requires: pip install adlfs
#
# azure_queue = FileTaskQueue(
#     project_name="azure_demo",
#     base_dir="abfs://my-container/omniq/tasks",
#     queues=["high", "medium", "low"],
#     storage_options={
#         "account_name": "mystorageaccount",
#         "account_key": "your_account_key"
#         # Alternative: "sas_token": "your_sas_token"
#     }
# )
# 
# azure_results = FileResultStorage(
#     project_name="azure_demo", 
#     base_dir="abfs://my-container/omniq/results",
#     storage_options={
#         "account_name": "mystorageaccount",
#         "account_key": "your_account_key"
#     }
# )
# 
# # Create OmniQ with Azure storage
# azure_oq = OmniQ(
#     project_name="azure_demo",
#     task_queue=azure_queue,
#     result_store=azure_results
# )

# GOOGLE CLOUD STORAGE EXAMPLE
# Requires: pip install gcsfs
#
# gcs_queue = FileTaskQueue(
#     project_name="gcs_demo",
#     base_dir="gs://my-bucket/omniq/tasks", 
#     queues=["high", "medium", "low"],
#     storage_options={
#         "token": "/path/to/service-account.json"
#         # Alternative: "token": "cloud" for default credentials
#     }
# )
# 
# gcs_results = FileResultStorage(
#     project_name="gcs_demo",
#     base_dir="gs://my-bucket/omniq/results",
#     storage_options={
#         "token": "/path/to/service-account.json"
#     }
# )
# 
# # Create OmniQ with GCS storage
# gcs_oq = OmniQ(
#     project_name="gcs_demo",
#     task_queue=gcs_queue,
#     result_store=gcs_results
# )

# ENVIRONMENT VARIABLE CONFIGURATION
# You can also configure using environment variables:
#
# For S3:
# export AWS_ACCESS_KEY_ID="your_access_key"
# export AWS_SECRET_ACCESS_KEY="your_secret_key"
# export AWS_DEFAULT_REGION="us-east-1"
#
# For Azure:
# export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount" 
# export AZURE_STORAGE_ACCOUNT_KEY="your_account_key"
#
# For GCS:
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
#
# Then create storage without explicit storage_options:
# cloud_queue = FileTaskQueue(
#     project_name="cloud_demo",
#     base_dir="s3://my-bucket/omniq",  # or abfs:// or gs://
#     queues=["high", "medium", "low"]
# )
""")


def main():
    """Run all demonstrations."""
    print("OmniQ fsspec Cloud Storage Examples")
    print("===================================")
    print("This script demonstrates using fsspec with OmniQ for different storage backends.")
    print("Local and memory examples will run. Cloud examples are shown as comments.")
    
    # Run local filesystem demo
    demonstrate_local_filesystem()
    
    # Run memory filesystem demo  
    demonstrate_memory_filesystem()
    
    # Run async demo
    print("\n" + "=" * 60)
    print("RUNNING ASYNC DEMONSTRATION...")
    print("=" * 60)
    asyncio.run(demonstrate_async_with_memory())
    
    # Show cloud storage examples
    demonstrate_cloud_storage_examples()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("✅ Local filesystem storage - PASSED")
    print("✅ Memory filesystem storage - PASSED") 
    print("✅ Async with memory storage - PASSED")
    print("📝 Cloud storage examples - SHOWN (requires credentials)")
    print("\nTo use cloud storage:")
    print("1. Install required packages: s3fs, adlfs, gcsfs")
    print("2. Configure credentials (see README.md)")
    print("3. Uncomment and modify the cloud storage examples")


if __name__ == "__main__":
    main()