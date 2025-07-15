# File Storage Backend for OmniQ

The File Storage Backend provides a filesystem-based storage solution for OmniQ using `fsspec` with `DirFileSystem`. This backend supports both local and remote filesystems (S3, GCS, Azure, etc.) and provides async-first, sync-wrapped storage for tasks, results, events, and schedules.

## Features

- **Cross-platform file operations** using `fsspec`
- **Multiple filesystem support** (local, S3, GCS, Azure, etc.)
- **Async-first design** with sync wrappers
- **Directory-based organization** for different data types
- **High-performance serialization** with `msgspec`
- **Configurable storage options** via `FileConfig`
- **Context manager support** for resource management
- **Cleanup operations** for expired data

## Installation

The file storage backend requires the `fsspec` package:

```bash
pip install fsspec
```

For cloud storage support, install additional dependencies:

```bash
# For S3 support
pip install s3fs

# For Google Cloud Storage
pip install gcsfs

# For Azure Blob Storage
pip install adlfs
```

## Basic Usage

### Local File Storage

```python
import asyncio
from omniq.backend.file import FileBackend
from omniq.models.task import Task

async def main():
    # Create file backend with local storage
    backend = FileBackend(
        base_dir="./omniq_data",
        fs_protocol="file"
    )
    
    async with backend:
        # Get task queue
        task_queue = backend.get_task_queue()
        
        # Create and enqueue a task
        task = Task(
            func="my_function",
            args=(1, 2, 3),
            queue_name="default"
        )
        
        await task_queue.enqueue(task)
        
        # Dequeue and process
        dequeued_task = await task_queue.dequeue(["default"])
        print(f"Processing task: {dequeued_task.func}")

asyncio.run(main())
```

### Cloud Storage (S3 Example)

```python
from omniq.backend.file import FileBackend

# Create S3-backed storage
backend = FileBackend(
    base_dir="my-bucket/omniq-data",
    fs_protocol="s3",
    fs_kwargs={
        "key": "your-access-key",
        "secret": "your-secret-key",
        "endpoint_url": "https://s3.amazonaws.com"
    }
)

# Or use from_url for convenience
backend = FileBackend.from_url("s3://my-bucket/omniq-data")
```

## Configuration

### Using FileConfig

```python
from omniq.models.config import FileConfig
from omniq.backend.file import FileBackend

config = FileConfig(
    base_dir="./omniq_data",
    fsspec_uri="file://./omniq_data",
    storage_options={},
    tasks_dir="tasks",
    results_dir="results",
    events_dir="events",
    schedules_dir="schedules",
    serialization_format="json"
)

backend = FileBackend.from_config(config)
```

### Environment Variables

Configure via environment variables with `OMNIQ_` prefix:

```bash
export OMNIQ_BASE_DIR="./my_omniq_data"
export OMNIQ_FSSPEC_URI="s3://my-bucket/omniq"
```

## Storage Components

### Task Queue

```python
async with backend:
    task_queue = backend.get_task_queue()
    
    # Enqueue task
    task = Task(func="process_data", args=("data",))
    await task_queue.enqueue(task)
    
    # Dequeue task
    task = await task_queue.dequeue(["default", "high_priority"])
    
    # Get task by ID
    task = await task_queue.get_task("task_id")
    
    # List tasks
    tasks = await task_queue.list_tasks(queue_name="default")
    
    # Update task
    task.status = TaskStatus.RUNNING
    await task_queue.update_task(task)
```

### Result Storage

```python
async with backend:
    result_storage = backend.get_result_storage()
    
    # Store result
    result = TaskResult(
        task_id="task_123",
        status=ResultStatus.SUCCESS,
        result={"output": "processed_data"}
    )
    await result_storage.set(result)
    
    # Get result
    result = await result_storage.get("task_123")
    
    # List results
    results = await result_storage.list_results()
    
    # Delete result
    await result_storage.delete("task_123")
```

### Event Storage

```python
async with backend:
    event_storage = backend.get_event_storage()
    
    # Log event
    event = TaskEvent(
        task_id="task_123",
        event_type=EventType.COMPLETED,
        message="Task completed successfully"
    )
    await event_storage.log_event(event)
    
    # Get events
    events = await event_storage.get_events(task_id="task_123")
    
    # Get events by type
    events = await event_storage.get_events(event_type=EventType.FAILED)
```

### Schedule Storage

```python
async with backend:
    schedule_storage = backend.get_schedule_storage()
    
    # Save schedule
    schedule = Schedule(
        schedule_type=ScheduleType.CRON,
        func="daily_report",
        cron_expression="0 9 * * *"
    )
    await schedule_storage.save_schedule(schedule)
    
    # Get schedule
    schedule = await schedule_storage.get_schedule("schedule_id")
    
    # List schedules
    schedules = await schedule_storage.list_schedules()
    
    # Get ready schedules
    ready = await schedule_storage.get_ready_schedules()
```

## Synchronous Usage

```python
# Get sync versions of storage components
with backend:
    sync_task_queue = backend.get_task_queue(async_mode=False)
    sync_result_storage = backend.get_result_storage(async_mode=False)
    
    # Use sync methods (they internally use asyncio.run)
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        task = Task(func="sync_task", args=())
        loop.run_until_complete(sync_task_queue.enqueue(task))
    finally:
        loop.close()
```

## Directory Structure

The file backend organizes data in the following directory structure:

```
omniq_data/
├── tasks/
│   ├── default/
│   │   ├── pending/
│   │   ├── running/
│   │   └── completed/
│   └── high_priority/
├── results/
│   ├── success/
│   └── failed/
├── events/
│   └── 2024/
│       └── 01/
│           └── 15/
└── schedules/
    ├── active/
    ├── paused/
    └── completed/
```

## Cleanup Operations

```python
async with backend:
    # Clean up expired tasks, results, and events
    stats = await backend.cleanup_expired()
    print(f"Cleaned up: {stats}")
    
    # Manual cleanup for specific components
    expired_tasks = await backend.get_task_queue().cleanup_expired_tasks()
    expired_results = await backend.get_result_storage().cleanup_expired_results()
```

## Advanced Configuration

### Custom Filesystem Options

```python
backend = FileBackend(
    base_dir="./omniq_data",
    fs_protocol="file",
    fs_kwargs={
        "auto_mkdir": True,
        "cache_type": "mmap"
    }
)
```

### Multiple Backends

```python
# Separate backends for different purposes
task_backend = FileBackend(base_dir="./tasks", fs_protocol="file")
result_backend = FileBackend(base_dir="s3://results-bucket", fs_protocol="s3")

async with task_backend, result_backend:
    task_queue = task_backend.get_task_queue()
    result_storage = result_backend.get_result_storage()
    
    # Use different backends for different components
    task = Task(func="process", args=())
    await task_queue.enqueue(task)
    
    result = TaskResult(task_id=task.id, status=ResultStatus.SUCCESS)
    await result_storage.set(result)
```

## Error Handling

```python
from omniq.exceptions import StorageError

async with backend:
    try:
        task_queue = backend.get_task_queue()
        await task_queue.enqueue(task)
    except StorageError as e:
        print(f"Storage error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Performance Considerations

### Serialization Format

Choose the appropriate serialization format based on your needs:

```python
config = FileConfig(
    serialization_format="json",    # Human-readable, slower
    # serialization_format="msgpack", # Binary, faster
    # serialization_format="pickle",  # Python-specific, fastest
)
```

### Filesystem Caching

Enable filesystem caching for better performance:

```python
backend = FileBackend(
    fs_kwargs={
        "cache_type": "mmap",
        "cache_size": 100 * 1024 * 1024  # 100MB cache
    }
)
```

### Batch Operations

Process multiple items in batches:

```python
async with backend:
    task_queue = backend.get_task_queue()
    
    # Enqueue multiple tasks
    tasks = [Task(func="batch_task", args=(i,)) for i in range(100)]
    for task in tasks:
        await task_queue.enqueue(task)
    
    # Process in batches
    batch_size = 10
    while True:
        batch = []
        for _ in range(batch_size):
            task = await task_queue.dequeue(["default"], timeout=1.0)
            if task:
                batch.append(task)
            else:
                break
        
        if not batch:
            break
            
        # Process batch
        for task in batch:
            # Process task
            pass
```

## Monitoring and Debugging

### Enable Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("omniq.storage.file")
```

### Storage Statistics

```python
async with backend:
    task_queue = backend.get_task_queue()
    
    # Get queue sizes
    default_size = await task_queue.get_queue_size("default")
    print(f"Default queue size: {default_size}")
    
    # List all tasks
    all_tasks = await task_queue.list_tasks()
    print(f"Total tasks: {len(all_tasks)}")
```

## Migration from Other Backends

### From SQLite Backend

```python
from omniq.backend.sqlite import SQLiteBackend
from omniq.backend.file import FileBackend

# Source SQLite backend
sqlite_backend = SQLiteBackend("omniq.db")

# Target file backend
file_backend = FileBackend("./migrated_data")

async def migrate():
    async with sqlite_backend, file_backend:
        # Migrate tasks
        sqlite_queue = sqlite_backend.get_task_queue()
        file_queue = file_backend.get_task_queue()
        
        tasks = await sqlite_queue.list_tasks()
        for task in tasks:
            await file_queue.enqueue(task)
        
        # Migrate results
        sqlite_results = sqlite_backend.get_result_storage()
        file_results = file_backend.get_result_storage()
        
        results = await sqlite_results.list_results()
        for result in results:
            await file_results.set(result)

asyncio.run(migrate())
```

## Best Practices

1. **Use context managers** for proper resource cleanup
2. **Configure appropriate TTLs** for tasks and results
3. **Monitor disk usage** for local file storage
4. **Use cloud storage** for distributed deployments
5. **Enable compression** for large payloads
6. **Implement backup strategies** for critical data
7. **Use batch operations** for better performance
8. **Monitor filesystem permissions** and quotas

## Troubleshooting

### Common Issues

1. **Permission denied**: Check filesystem permissions
2. **Disk space full**: Monitor and clean up old data
3. **Network timeouts**: Configure appropriate timeouts for cloud storage
4. **Serialization errors**: Ensure data is serializable

### Debug Mode

```python
backend = FileBackend(
    base_dir="./debug_data",
    fs_kwargs={"debug": True}
)
```

This comprehensive file storage backend provides a robust, scalable solution for OmniQ's storage needs with support for both local and cloud filesystems.