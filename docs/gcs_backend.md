# Google Cloud Storage Backend for OmniQ

The Google Cloud Storage (GCS) Backend provides a cloud-based storage solution for OmniQ using Google Cloud Storage through `fsspec` and `gcsfs`. This backend supports all OmniQ storage types: task queue, result storage, event storage, and schedule storage.

## Features

- **Cloud-Native Storage**: Leverages Google Cloud Storage for scalable, durable storage
- **Async-First Design**: Built with async/await patterns for high performance
- **Sync Compatibility**: Provides synchronous wrappers for all operations
- **Bucket Organization**: Uses bucket-based structure with configurable prefixes
- **GCS-Specific Features**: Supports GCS consistency models and access controls
- **Authentication Flexibility**: Multiple authentication methods supported
- **fsspec Integration**: Built on fsspec for consistent file system abstraction

## Installation

Install the required dependencies:

```bash
pip install gcsfs
```

## Quick Start

### Basic Usage

```python
from omniq.backend.gcs import GCSBackend

# Initialize the backend
backend = GCSBackend(
    bucket_name="my-omniq-bucket",
    prefix="production/",
    project="my-gcp-project"
)

# Use with async context manager
async with backend:
    # Access async storage components
    task_storage = backend.async_task_storage
    result_storage = backend.async_result_storage
    event_storage = backend.async_event_storage
    schedule_storage = backend.async_schedule_storage
    
    # Your async operations here...

# Use with sync context manager
with backend:
    # Access sync storage components
    task_storage = backend.task_storage
    result_storage = backend.result_storage
    event_storage = backend.event_storage
    schedule_storage = backend.schedule_storage
    
    # Your sync operations here...
```

### Configuration Options

```python
backend = GCSBackend(
    bucket_name="my-omniq-bucket",
    prefix="omniq/",                    # Optional prefix for all keys
    project="my-gcp-project",           # GCP project ID
    token="/path/to/service-account.json",  # Service account JSON file
    access="read_write",                # Access mode
    consistency="md5",                  # Consistency mode
    cache_timeout=300,                  # Cache timeout in seconds
    # Additional gcsfs options
    block_size=5*1024*1024,            # 5MB blocks
)
```

## Configuration

### Authentication

The GCS backend supports multiple authentication methods:

1. **Service Account JSON File**:
   ```python
   backend = GCSBackend(
       bucket_name="my-bucket",
       token="/path/to/service-account.json"
   )
   ```

2. **Environment Variables**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   ```
   ```python
   backend = GCSBackend(bucket_name="my-bucket")
   ```

3. **Default Credentials** (when running on GCP):
   ```python
   backend = GCSBackend(bucket_name="my-bucket")
   ```

### Access Modes

- `read_only`: Read-only access to the bucket
- `read_write`: Read and write access (default)
- `full_control`: Full control over bucket and objects

### Consistency Models

- `md5`: MD5 hash-based consistency (default)
- `crc32c`: CRC32C checksum-based consistency
- `size`: Size-based consistency
- `none`: No consistency checking

### Configuration from Dictionary

```python
from omniq.backend.gcs import create_gcs_backend_from_config

config = {
    "bucket_name": "my-omniq-bucket",
    "prefix": "production/",
    "project": "my-gcp-project",
    "token": "/path/to/service-account.json",
    "access": "read_write",
    "consistency": "md5",
    "cache_timeout": 300,
    "gcs_kwargs": {
        "block_size": 5 * 1024 * 1024,
        "cache_type": "readahead",
    }
}

backend = create_gcs_backend_from_config(config)
```

## Storage Structure

The GCS backend organizes data in the following structure:

```
bucket-name/
├── prefix/
│   ├── tasks/
│   │   ├── task-id-1.json
│   │   ├── task-id-2.json
│   │   └── ...
│   ├── queues/
│   │   ├── queue-name-1/
│   │   │   ├── task-id-1.json
│   │   │   └── task-id-2.json
│   │   └── queue-name-2/
│   │       └── ...
│   ├── results/
│   │   ├── task-id-1.json
│   │   ├── task-id-2.json
│   │   └── ...
│   ├── events/
│   │   ├── event-id-1.json
│   │   ├── event-id-2.json
│   │   └── ...
│   └── schedules/
│       ├── schedule-id-1.json
│       ├── schedule-id-2.json
│       └── ...
```

## Storage Components

### AsyncGCSQueue / GCSQueue

Handles task queue operations with support for multiple named queues.

**Key Features:**
- Priority-based task ordering
- Queue-specific task organization
- Task TTL and expiration handling
- Atomic task status updates

**Example:**
```python
# Async usage
async with backend:
    queue = backend.async_task_storage
    
    # Enqueue a task
    task_id = await queue.enqueue(task)
    
    # Dequeue from multiple queues
    task = await queue.dequeue(["high-priority", "default"])
    
    # Get queue size
    size = await queue.get_queue_size("default")

# Sync usage
with backend:
    queue = backend.task_storage
    
    # Enqueue a task
    task_id = queue.enqueue_sync(task)
    
    # Dequeue from multiple queues
    task = queue.dequeue_sync(["high-priority", "default"])
```

### AsyncGCSResultStorage / GCSResultStorage

Manages task execution results with metadata.

**Key Features:**
- Result persistence with metadata
- Status-based filtering
- Automatic expiration handling
- Efficient result retrieval

**Example:**
```python
# Async usage
async with backend:
    storage = backend.async_result_storage
    
    # Store a result
    await storage.set(result)
    
    # Retrieve a result
    result = await storage.get(task_id)
    
    # List results with filtering
    results = await storage.list_results(status="success", limit=10)

# Sync usage
with backend:
    storage = backend.result_storage
    
    # Store a result
    storage.set_sync(result)
    
    # Retrieve a result
    result = storage.get_sync(task_id)
```

### AsyncGCSEventStorage / GCSEventStorage

Provides event logging for task lifecycle tracking.

**Key Features:**
- Structured event logging
- Time-based event filtering
- Task-specific event retrieval
- Automatic event cleanup

**Example:**
```python
# Async usage
async with backend:
    storage = backend.async_event_storage
    
    # Log an event
    await storage.log_event(event)
    
    # Get events for a task
    events = await storage.get_events(task_id=task_id)
    
    # Get events by type and time range
    events = await storage.get_events(
        event_type="completed",
        start_time=start_time,
        end_time=end_time
    )

# Sync usage
with backend:
    storage = backend.event_storage
    
    # Log an event
    storage.log_event_sync(event)
    
    # Get events
    events = storage.get_events_sync(task_id=task_id)
```

### AsyncGCSScheduleStorage / GCSScheduleStorage

Manages scheduled tasks with pause/resume capabilities.

**Key Features:**
- Cron and interval-based scheduling
- Schedule state management
- Ready-to-run schedule detection
- Schedule lifecycle tracking

**Example:**
```python
# Async usage
async with backend:
    storage = backend.async_schedule_storage
    
    # Save a schedule
    await storage.save_schedule(schedule)
    
    # Get ready schedules
    ready = await storage.get_ready_schedules()
    
    # List all schedules
    schedules = await storage.list_schedules(status="active")

# Sync usage
with backend:
    storage = backend.schedule_storage
    
    # Save a schedule
    storage.save_schedule_sync(schedule)
    
    # Get ready schedules
    ready = storage.get_ready_schedules_sync()
```

## Error Handling

The GCS backend handles various error conditions:

```python
try:
    async with backend:
        # Your operations here
        pass
except ImportError:
    print("gcsfs not installed. Run: pip install gcsfs")
except Exception as e:
    print(f"GCS operation failed: {e}")
    # Handle authentication, network, or permission errors
```

## Performance Considerations

### Optimization Tips

1. **Batch Operations**: Use bulk operations when possible
2. **Connection Pooling**: Reuse backend instances
3. **Caching**: Configure appropriate cache timeouts
4. **Block Size**: Adjust block size for your workload
5. **Consistency**: Choose appropriate consistency model

### Monitoring

Monitor these metrics for optimal performance:

- Request latency and throughput
- Error rates and types
- Storage costs and usage
- Cache hit rates

## Best Practices

1. **Bucket Organization**: Use meaningful prefixes for different environments
2. **Authentication**: Use service accounts with minimal required permissions
3. **Error Handling**: Implement proper retry logic for transient failures
4. **Monitoring**: Set up alerts for storage operations
5. **Cleanup**: Implement TTL policies for temporary data
6. **Security**: Use IAM roles and bucket policies appropriately

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify service account credentials
   - Check IAM permissions
   - Ensure project ID is correct

2. **Permission Errors**:
   - Verify bucket access permissions
   - Check object-level permissions
   - Review IAM roles

3. **Network Issues**:
   - Check network connectivity
   - Verify firewall rules
   - Consider regional proximity

4. **Performance Issues**:
   - Adjust block size and cache settings
   - Monitor request patterns
   - Consider bucket location

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your GCS backend operations
```

## Integration with OmniQ

The GCS backend integrates seamlessly with OmniQ's core functionality:

```python
from omniq import OmniQ
from omniq.backend.gcs import GCSBackend

# Initialize OmniQ with GCS backend
backend = GCSBackend(
    bucket_name="my-omniq-bucket",
    project="my-gcp-project"
)

omniq = OmniQ(backend=backend)

# Use OmniQ normally
@omniq.task
def my_task(x, y):
    return x + y

# Enqueue and process tasks
result = omniq.enqueue(my_task, 1, 2)
```

## See Also

- [OmniQ Documentation](../README.md)
- [Storage Backends Overview](../README.md#storage-backends)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [gcsfs Documentation](https://gcsfs.readthedocs.io/)