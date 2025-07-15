# Azure Backend for OmniQ

The Azure backend provides persistent storage for OmniQ using Azure Blob Storage, implemented with `fsspec` and `adlfs` for cloud-native operations.

## Features

- **Persistent Storage**: All tasks, results, events, and schedules are stored in Azure Blob Storage
- **Multiple Authentication Methods**: Support for connection strings, account keys, SAS tokens, and service principal authentication
- **Async and Sync Support**: Both asynchronous and synchronous interfaces available
- **Scalable**: Leverages Azure's cloud infrastructure for high availability and scalability
- **Cost-Effective**: Pay-as-you-go pricing model with Azure Blob Storage

## Installation

Install the required dependencies:

```bash
pip install adlfs fsspec
```

## Quick Start

### Basic Usage with Connection String

```python
import os
from omniq.backend.azure import AzureBackend

# Create backend with connection string
backend = AzureBackend(
    container_name="omniq-prod",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)

# Use with context manager
with backend:
    # Get storage instances
    task_queue = backend.task_storage
    result_storage = backend.result_storage
    
    # Your application logic here
```

### Async Usage

```python
import asyncio
from omniq.backend.azure import AzureBackend

async def main():
    backend = AzureBackend(
        container_name="omniq-prod",
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    
    async with backend:
        # Get async storage instances
        task_queue = backend.async_task_storage
        result_storage = backend.async_result_storage
        
        # Your async application logic here

asyncio.run(main())
```

## Authentication Methods

### 1. Connection String (Recommended for Development)

```python
backend = AzureBackend(
    container_name="omniq-test",
    connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
)
```

### 2. Account Name and Key

```python
backend = AzureBackend(
    container_name="omniq-prod",
    account_name="mystorageaccount",
    account_key="myaccountkey"
)
```

### 3. Service Principal (Recommended for Production)

```python
backend = AzureBackend(
    container_name="omniq-prod",
    account_name="mystorageaccount",
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)
```

### 4. SAS Token

```python
backend = AzureBackend(
    container_name="omniq-prod",
    account_name="mystorageaccount",
    sas_token="?sv=2020-08-04&ss=bfqt&srt=sco&sp=rwdlacupx&se=2021-01-01T00:00:00Z&st=2020-01-01T00:00:00Z&spr=https&sig=signature"
)
```

## Configuration Options

### Basic Configuration

```python
backend = AzureBackend(
    container_name="omniq-prod",           # Required: Azure container name
    prefix="my-app/production/",           # Optional: Prefix for all keys (default: "omniq/")
    connection_string="...",               # Authentication method
)
```

### Advanced Configuration

```python
backend = AzureBackend(
    container_name="omniq-prod",
    prefix="my-app/production/",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    azure_additional_kwargs={
        "client_kwargs": {
            "connection_timeout": 30,      # Connection timeout in seconds
            "read_timeout": 60,            # Read timeout in seconds
        }
    }
)
```

## Storage Structure

The Azure backend organizes data in the following structure within your container:

```
container/
├── {prefix}/
│   ├── tasks/
│   │   ├── task-1.json
│   │   ├── task-2.json
│   │   └── ...
│   ├── queues/
│   │   ├── queue-name-1/
│   │   │   ├── task-1.json (reference)
│   │   │   └── task-2.json (reference)
│   │   └── queue-name-2/
│   │       └── ...
│   ├── results/
│   │   ├── task-1.json
│   │   ├── task-2.json
│   │   └── ...
│   ├── events/
│   │   ├── event-1.json
│   │   ├── event-2.json
│   │   └── ...
│   └── schedules/
│       ├── schedule-1.json
│       ├── schedule-2.json
│       └── ...
```

## API Reference

### AzureBackend Class

#### Constructor Parameters

- `container_name` (str): Azure container name for storing data
- `prefix` (str, optional): Base prefix for all keys (default: "omniq/")
- `connection_string` (str, optional): Azure storage connection string
- `account_name` (str, optional): Azure storage account name
- `account_key` (str, optional): Azure storage account key
- `sas_token` (str, optional): Azure SAS token
- `tenant_id` (str, optional): Azure tenant ID for service principal auth
- `client_id` (str, optional): Azure client ID for service principal auth
- `client_secret` (str, optional): Azure client secret for service principal auth
- `azure_additional_kwargs` (dict, optional): Additional arguments for adlfs

#### Properties

**Async Storage Properties:**
- `async_task_storage`: Returns `AsyncAzureQueue` instance
- `async_result_storage`: Returns `AsyncAzureResultStorage` instance
- `async_event_storage`: Returns `AsyncAzureEventStorage` instance
- `async_schedule_storage`: Returns `AsyncAzureScheduleStorage` instance

**Sync Storage Properties:**
- `task_storage`: Returns `AzureQueue` instance (sync wrapper)
- `result_storage`: Returns `AzureResultStorage` instance (sync wrapper)
- `event_storage`: Returns `AzureEventStorage` instance (sync wrapper)
- `schedule_storage`: Returns `AzureScheduleStorage` instance (sync wrapper)

### Storage Classes

#### AsyncAzureQueue / AzureQueue

Task queue operations:

```python
# Async methods
await task_queue.enqueue(task)
task = await task_queue.dequeue(["queue1", "queue2"])
await task_queue.update_task(task)
tasks = await task_queue.list_tasks(queue_name="math")
size = await task_queue.get_queue_size("math")

# Sync methods (AzureQueue only)
task_queue.enqueue_sync(task)
task = task_queue.dequeue_sync(["queue1", "queue2"])
task_queue.update_task_sync(task)
tasks = task_queue.list_tasks_sync(queue_name="math")
size = task_queue.get_queue_size_sync("math")
```

#### AsyncAzureResultStorage / AzureResultStorage

Result storage operations:

```python
# Async methods
await result_storage.set(result)
result = await result_storage.get(task_id)
await result_storage.delete(task_id)
results = await result_storage.list_results(status="SUCCESS")

# Sync methods (AzureResultStorage only)
result_storage.set_sync(result)
result = result_storage.get_sync(task_id)
result_storage.delete_sync(task_id)
results = result_storage.list_results_sync(status="SUCCESS")
```

#### AsyncAzureEventStorage / AzureEventStorage

Event logging operations:

```python
# Async methods
await event_storage.log_event(event)
events = await event_storage.get_events(task_id="task-1")
await event_storage.cleanup_old_events(older_than=datetime.utcnow() - timedelta(days=30))

# Sync methods (AzureEventStorage only)
event_storage.log_event_sync(event)
events = event_storage.get_events_sync(task_id="task-1")
event_storage.cleanup_old_events_sync(older_than=datetime.utcnow() - timedelta(days=30))
```

#### AsyncAzureScheduleStorage / AzureScheduleStorage

Schedule management operations:

```python
# Async methods
await schedule_storage.save_schedule(schedule)
schedule = await schedule_storage.get_schedule(schedule_id)
await schedule_storage.update_schedule(schedule)
schedules = await schedule_storage.list_schedules(status="ACTIVE")
ready = await schedule_storage.get_ready_schedules()

# Sync methods (AzureScheduleStorage only)
schedule_storage.save_schedule_sync(schedule)
schedule = schedule_storage.get_schedule_sync(schedule_id)
schedule_storage.update_schedule_sync(schedule)
schedules = schedule_storage.list_schedules_sync(status="ACTIVE")
ready = schedule_storage.get_ready_schedules_sync()
```

## Environment Variables

Set these environment variables for authentication:

```bash
# Connection string method
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"

# Account name and key method
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_STORAGE_ACCOUNT_KEY="myaccountkey"

# Service principal method
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

## Error Handling

The Azure backend handles common errors gracefully:

```python
try:
    async with backend:
        # Your operations here
        pass
except ImportError:
    print("adlfs is required. Install with: pip install adlfs")
except Exception as e:
    print(f"Azure operation failed: {e}")
```

## Performance Considerations

1. **Connection Pooling**: The backend reuses connections for better performance
2. **Batch Operations**: Use list operations to retrieve multiple items efficiently
3. **Prefixes**: Use meaningful prefixes to organize data and improve query performance
4. **Cleanup**: Regularly clean up expired tasks and results to maintain performance

## Security Best Practices

1. **Use Service Principal**: For production environments, use service principal authentication
2. **Rotate Keys**: Regularly rotate access keys and connection strings
3. **Least Privilege**: Grant only necessary permissions to the storage account
4. **Network Security**: Use private endpoints and firewall rules when possible
5. **Audit Logging**: Enable Azure Storage logging for security monitoring

## Troubleshooting

### Common Issues

1. **Import Error**: Install adlfs with `pip install adlfs`
2. **Authentication Failed**: Check your credentials and permissions
3. **Container Not Found**: Ensure the container exists or the account has create permissions
4. **Timeout Errors**: Increase timeout values in `azure_additional_kwargs`

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your Azure backend code here
```

## Examples

See `examples/azure_backend_example.py` for complete working examples demonstrating:

- Basic async and sync usage
- Different authentication methods
- Task lifecycle management
- Error handling patterns
- Configuration options

## Migration from Other Backends

When migrating from other backends (memory, SQLite), the API remains the same. Only the backend initialization changes:

```python
# Before (memory backend)
from omniq.backend.memory import MemoryBackend
backend = MemoryBackend()

# After (Azure backend)
from omniq.backend.azure import AzureBackend
backend = AzureBackend(
    container_name="omniq-prod",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)
```

All storage operations remain identical, ensuring smooth migration.