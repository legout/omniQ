# Migration Guide

This guide helps you migrate OmniQ components while maintaining backward compatibility.

## Table of Contents

1. [Storage Interface Migration](#storage-interface-migration)
2. [Logging Migration](#logging-migration)
3. [Task Interval Type Migration](#task-interval-type-migration)
4. [TaskError Model Migration](#taskerror-migration)
5. [Worker Compatibility Migration](#worker-compatibility-migration)
---

## Storage Interface Migration

This section covers migration for storage backend implementations due to the new retry and interval task support.

### Overview

The BaseStorage interface has been enhanced with two new abstract methods to support proper retry and interval task functionality:

- `get_task(task_id: str) -> Optional[Task]`
- `reschedule(task_id: str, new_eta: datetime) -> None`

### What Changed

- **New Required Methods**: Storage backends must implement `get_task()` and `reschedule()`
- **Removed Fallbacks**: AsyncTaskQueue no longer uses fallback `_get_task_by_id()` that returned `None`
- **Enhanced Retry Logic**: Tasks can now be properly retrieved and retried
- **Interval Task Support**: Recurring tasks work correctly with proper rescheduling

### Migration Steps for Storage Backend Developers

If you have a custom storage backend, follow these steps:

#### 1. Implement `get_task()` Method

```python
async def get_task(self, task_id: str) -> Optional[Task]:
    """
    Retrieve a task by ID.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        Task if found, None otherwise
        
    Raises:
        StorageError: If retrieval fails
    """
    # Your implementation here
    pass
```

**Example for Redis Storage:**
```python
async def get_task(self, task_id: str) -> Optional[Task]:
    try:
        data = await self.redis.get(f"task:{task_id}")
        if data is None:
            return None
        return self.serializer.decode_task(data)
    except Exception as e:
        raise StorageError(f"Failed to retrieve task {task_id}: {e}")
```

#### 2. Implement `reschedule()` Method

```python
async def reschedule(self, task_id: str, new_eta: datetime) -> None:
    """
    Update a task's ETA for retry or interval rescheduling.
    
    Args:
        task_id: Unique task identifier
        new_eta: New execution time
        
    Raises:
        NotFoundError: If task doesn't exist
        StorageError: If update fails
    """
    # Your implementation here
    pass
```

**Example for Redis Storage:**
```python
async def reschedule(self, task_id: str, new_eta: datetime) -> None:
    try:
        # Get existing task
        data = await self.redis.get(f"task:{task_id}")
        if data is None:
            raise NotFoundError(f"Task {task_id} not found")
        
        task = self.serializer.decode_task(data)
        
        # Update ETA and status
        task["schedule"]["eta"] = new_eta
        task["status"] = TaskStatus.PENDING
        task["updated_at"] = datetime.now(timezone.utc)
        
        # Save updated task
        await self.redis.set(
            f"task:{task_id}", 
            self.serializer.encode_task(task)
        )
        
        # Update scheduling queue
        await self.redis.zadd(
            "schedule",
            {task_id: new_eta.timestamp()}
        )
        
    except Exception as e:
        raise StorageError(f"Failed to reschedule task {task_id}: {e}")
```

#### 3. Update Method Signatures

Ensure your storage class inherits from the updated BaseStorage:

```python
from omniq.storage.base import BaseStorage

class MyStorage(BaseStorage):
    async def get_task(self, task_id: str) -> Optional[Task]:
        # Implementation
        pass
    
    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        # Implementation
        pass
    
    # ... other existing methods
```

### Backward Compatibility

- **Existing Code**: All existing code continues to work without changes
- **No Breaking Changes**: Only additions to the interface
- **Graceful Degradation**: Old backends will fail clearly with NotImplementedError

### Testing Your Implementation

Use the provided test files as templates:

```bash
# Test your storage implementation
python test_storage_interface.py

# Test retry functionality
python test_queue_retry.py

# Test interval tasks
python test_interval_tasks.py
```

### Validation Checklist

- [ ] `get_task()` returns correct task for valid IDs
- [ ] `get_task()` returns `None` for non-existent IDs
- [ ] `get_task()` raises `StorageError` on retrieval failures
- [ ] `reschedule()` updates task ETA correctly
- [ ] `reschedule()` sets task status to `PENDING`
- [ ] `reschedule()` raises `NotFoundError` for missing tasks
- [ ] `reschedule()` raises `StorageError` on update failures
- [ ] Retry logic works with your storage backend
- [ ] Interval tasks reschedule correctly
- [ ] All existing functionality still works

---

## Logging Migration

This section helps you migrate from standard Python logging back to enhanced Loguru-based logging while maintaining v1 compliance.

## Overview

OmniQ has restored Loguru for enhanced logging capabilities while maintaining a simple 4-function API for v1 compliance. This provides production-ready features like correlation IDs, structured output, and log rotation.

## What Changed

- **Backend**: Standard Python `logging` → Enhanced Loguru
- **Enhanced Features**: Added correlation IDs, structured logging, file rotation
- **Backward Compatibility**: All existing logging functions continue to work
- **Smart Defaults**: Automatic configuration for DEV/PROD environments
- **Performance**: Async logging with minimal overhead (<5%)

## Environment Variables

### Enhanced Configuration

| Variable | Purpose | Default | Valid Values |
|----------|---------|---------|--------------|
| `OMNIQ_LOG_LEVEL` | Set logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `OMNIQ_LOG_MODE` | Environment mode | `DEV` | `DEV`, `PROD` |
| `OMNIQ_LOG_FILE` | Log file path (PROD mode) | `logs/omniq.log` | Any valid file path |
| `OMNIQ_LOG_ROTATION` | Log rotation size | `100 MB` | Size strings like `"10 MB"`, `"1 GB"` |
| `OMNIQ_LOG_RETENTION` | Log retention period | `30 days` | Time strings like `"7 days"`, `"1 week"` |

### Migration Steps

```bash
# Old way (still supported)
export OMNIQ_LOG_LEVEL=DEBUG

# New enhanced way
export OMNIQ_LOG_LEVEL=DEBUG
export OMNIQ_LOG_MODE=PROD
export OMNIQ_LOG_FILE=/var/log/omniq/app.log
export OMNIQ_LOG_ROTATION="50 MB"
export OMNIQ_LOG_RETENTION="7 days"
```

## Code Migration

### Basic Logging

**Before (standard logging):**
```python
from omniq.logging import configure_logging, get_logger

# Standard logging
configure_logging(level="DEBUG")
logger = get_logger()
logger.info("Task completed: task-123")
```

**After (enhanced Loguru - current):**
```python
from omniq.logging import configure, get_logger

# Enhanced logging with smart defaults
configure(level="DEBUG")
logger = get_logger()
logger.info("Task completed: task-123")
```

### Task Context Logging

**New Feature - Not available before:**
```python
from omniq.logging import task_context, bind_task

# Automatic correlation ID and timing
with task_context("task-123", "process") as task_logger:
    task_logger.info("Processing data")
    # All logs include correlation_id, operation, timing

# Manual context binding
logger = bind_task("task-456", worker="worker-1", operation="enqueue")
logger.info("Task enqueued with context")
```

### Configuration

**Before (standard logging):**
```python
from omniq.logging import configure_logging

# Basic configuration only
configure_logging(level="DEBUG")
```

**After (enhanced Loguru):**
```python
from omniq.logging import configure

# Enhanced configuration with production features
configure(
    level="DEBUG",
    rotation="50 MB",
    retention="7 days",
    compression="gz"
)
```

## Enhanced Features

### 1. Task Correlation and Timing

```python
from omniq.logging import task_context

# Automatic correlation ID and execution timing
with task_context("task-123", "process_data") as logger:
    logger.info("Starting data processing")
    result = await process_data(data)
    logger.info(f"Processed {len(data)} records")
# Automatic: correlation_id, operation, start_time, duration, error handling
```

### 2. Structured Context Binding

```python
from omniq.logging import bind_task

# Bind additional context to all log messages
logger = bind_task(
    "task-456", 
    worker="worker-1",
    user_id="user-123",
    session="session-abc"
)

logger.info("Task started")
# Output includes: task_id, worker, user_id, session, correlation_id
```

### 3. Environment-Based Output

**DEV Mode (default):**
```
2025-12-01 10:30:45 | INFO     | omniq.core:123 | Task execution started
└── task_id: abc-123 | operation: process_task | worker: worker-1
```

**PROD Mode:**
```json
{
  "timestamp": "2025-12-01T10:30:45.123Z",
  "level": "INFO",
  "logger": "omniq.core",
  "message": "Task execution started",
  "task_id": "abc-123",
  "operation": "process_task",
  "worker": "worker-1",
  "correlation_id": "abc-123"
}
```

### 4. Production Features

```python
# Automatic log rotation and compression
configure(
    level="INFO",
    rotation="100 MB",     # Rotate when file reaches 100MB
    retention="30 days",   # Keep logs for 30 days
    compression="gz"        # Compress rotated files
)

# In PROD mode, logs automatically go to file with JSON format
# In DEV mode, logs go to console with colors
```

## Backward Compatibility

### What Still Works

All existing OmniQ logging functions continue to work unchanged:

```python
from omniq.logging import (
    log_task_enqueued, log_task_started, log_task_completed,
    log_task_failed, log_worker_started, log_worker_stopped,
    log_storage_error, log_serialization_error
)

# These all work exactly as before, now with enhanced output
log_task_enqueued("task-123", "module.function")
log_task_started("task-123", 1)
log_task_completed("task-123", 1)
log_task_failed("task-123", "Error message", will_retry=True)
```

### What's Enhanced

These functions now include structured data and correlation:

```python
# Before: Standard logging format
# "2024-01-01 12:00:00 - omniq - INFO - Task enqueued: task-123 -> module.function"

# After: Enhanced format with structured data
# DEV: "2025-12-01 10:30:45 | INFO | omniq.logging:189 | Task enqueued: task-123 -> test_module.test_function"
# PROD: {"timestamp": "...", "level": "INFO", "task_id": "task-123", "func_path": "module.function", ...}
```

## Performance Considerations

### Enhanced Logging Benefits

- **Async Logging**: Non-blocking, <5% performance overhead
- **Smart Defaults**: Zero configuration required for most use cases
- **Production Ready**: Log rotation, compression, structured output
- **Correlation IDs**: Automatic task tracing across distributed systems
- **Thread-Safe**: Works correctly with concurrent workers

### Migration Impact

- **Enhanced Features**: Correlation IDs, structured logging, rotation
- **Better Performance**: Async logging with minimal overhead
- **Production Features**: JSON output, file management
- **Same API**: All existing code continues to work

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Loguru is installed (`pip install loguru`)
2. **Performance**: Use appropriate log levels (DEBUG can be verbose)
3. **File Permissions**: Ensure log directory is writable in PROD mode
4. **Disk Space**: Monitor log rotation settings in production

### Getting Help

```python
from omniq.logging import configure, get_logger

# Test basic functionality
configure()
logger = get_logger()
logger.info("Enhanced Loguru logging is working")

# Test task context
with task_context("test-123", "test") as task_logger:
    task_logger.info("Task context working")
```

## Best Practices

### 1. Use Task Context for Operations

```python
# Good - automatic correlation and timing
with task_context(task_id, "process") as logger:
    result = await process_data(data)
    logger.info("Processing complete")

# Avoid - manual correlation
logger.info(f"Processing task {task_id}")
# ... later ...
logger.info(f"Task {task_id} completed")
```

### 2. Bind Context for Long-Running Operations

```python
# Good - persistent context
worker_logger = bind_task(worker_id=worker_id, node=node_name)
worker_logger.info("Worker started")

# Throughout worker lifecycle
worker_logger.info("Processing task %s", task_id)
worker_logger.error("Task failed: %s", error)
```

### 3. Use Appropriate Log Levels

```python
logger.debug("Detailed debugging info: %s", debug_data)      # Development only
logger.info("Normal application flow: %s", event)          # General info
logger.warning("Unexpected but recoverable: %s", issue)     # Issues
logger.error("Error conditions: %s", error)                  # Errors
logger.critical("Critical failures: %s", critical)           # Critical
```

### 4. Configure for Environment

```python
# Development
configure(level="DEBUG")  # Verbose output, console only

# Production
configure(
    level="INFO",
    rotation="100 MB",
    retention="30 days",
    compression="gz"
)  # Structured output, file management
```

### 5. Handle Exceptions in Context

```python
# Task context automatically handles exceptions and timing
with task_context("task-123", "process") as logger:
    try:
        result = await risky_operation()
        logger.info("Operation successful")
    except Exception as e:
        logger.error("Operation failed: %s", e)
        # Context manager automatically logs timing and failure
        raise
```

## Complete Example

Here's a complete example using enhanced logging:

```python
import os
import asyncio
from omniq import AsyncOmniQ
from omniq.config import Settings
from omniq.logging import configure, get_logger, task_context, bind_task

async def main():
    # Configure enhanced logging
    log_mode = os.getenv("OMNIQ_LOG_MODE", "DEV")
    log_level = os.getenv("OMNIQ_LOG_LEVEL", "INFO")
    
    if log_mode == "PROD":
        configure(
            level=log_level,
            rotation="100 MB",
            retention="30 days",
            compression="gz"
        )
    else:
        configure(level=log_level)
    
    logger = get_logger()
    logger.info("Application started in %s mode", log_mode)
    
    # Initialize OmniQ
    settings = Settings(backend="sqlite")
    omniq = AsyncOmniQ(settings)
    
    # Worker with persistent context
    worker_logger = bind_task(worker_id="worker-1", node="production-1")
    worker_logger.info("Worker initialized")
    
    # Process tasks with correlation
    async with omniq.worker_pool() as workers:
        worker_logger.info("Starting task processing")
        
        # Process individual tasks with context
        for i in range(10):
            task_id = f"task-{i}"
            
            with task_context(task_id, "process") as task_logger:
                task_logger.info("Processing task %d", i)
                # Simulate work
                await asyncio.sleep(0.1)
                task_logger.info("Task %d completed", i)
    
    worker_logger.info("Worker shutdown complete")
    logger.info("Application shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusion

The migration to enhanced Loguru logging provides:

1. **Production Readiness**: Log rotation, compression, structured output
2. **Task Observability**: Correlation IDs, execution timing, error tracing
3. **Developer Experience**: Better debugging, colored output, smart defaults
4. **v1 Compliance**: Simple 4-function API with optional advanced features
5. **Performance**: Async logging with <5% overhead

The migration adds powerful features while maintaining simplicity and backward compatibility.

---

## Task Interval Type Migration

This section covers the migration from `int` to `timedelta` for task interval fields to achieve v1 spec compliance.

### Overview

The Task model's `interval` field has been updated from `int` (seconds) to `timedelta | None` to comply with the v1 specification. This change provides better type safety and more expressive interval definitions while maintaining backward compatibility.

### What Changed

- **Field Type**: `interval: int = 0` → `interval: timedelta | None = None`
- **Location**: Interval field moved from task level to `schedule.interval`
- **Backward Compatibility**: `int` values are automatically converted to `timedelta(seconds=int)`
- **Serialization**: Enhanced serialization supports `timedelta` objects
- **API**: All APIs accept both `timedelta` and `int` for intervals

### Migration Steps

#### 1. Update Task Creation (Recommended)

**Before (int seconds):**
```python
# Old way - still works for backward compatibility
task_id = await omniq.enqueue(
    "my_module.cleanup_task",
    interval=3600  # int seconds
)
```

**After (timedelta - recommended):**
```python
from datetime import timedelta

# New way - preferred approach
task_id = await omniq.enqueue(
    "my_module.cleanup_task",
    interval=timedelta(hours=1)  # More readable
)

# Complex intervals
task_id = await omniq.enqueue(
    "my_module.complex_task",
    interval=timedelta(days=1, hours=2, minutes=30)
)
```

#### 2. Update Task Model Usage

**Before:**
```python
# Direct int access
interval_seconds = task["interval"]
if interval_seconds > 0:
    # Handle interval task
```

**After:**
```python
# Access through schedule
interval = task["schedule"].get("interval")
if interval is not None:
    # interval is now a timedelta object
    interval_seconds = interval.total_seconds()
    # Handle interval task
```

#### 3. Update Serialization Code

If you have custom serialization, update it to handle `timedelta`:

```python
from omniq.serialization import serialize_timedelta, deserialize_timedelta

# Serialize timedelta
interval = timedelta(hours=1)
serialized = serialize_timedelta(interval)
# Result: {"type": "timedelta", "total_seconds": 3600.0}

# Deserialize timedelta
deserialized = deserialize_timedelta(serialized)
# Result: timedelta(hours=1)
```

### Backward Compatibility

All existing code continues to work without changes:

```python
# These all still work exactly as before
await omniq.enqueue("task", interval=60)  # int seconds
await omniq.enqueue("task", interval=timedelta(minutes=1))  # timedelta
```

### Benefits of Migration

1. **Type Safety**: `timedelta` provides better type checking
2. **Expressiveness**: More readable interval definitions
3. **Flexibility**: Support for complex intervals (days, hours, minutes, seconds)
4. **Spec Compliance**: Meets v1 specification requirements
5. **Future-Proof**: Extensible for additional time-based features

### Code Examples

#### Creating Different Interval Types

```python
from datetime import timedelta

# Simple intervals
await omniq.enqueue("task", interval=timedelta(seconds=30))
await omniq.enqueue("task", interval=timedelta(minutes=5))
await omniq.enqueue("task", interval=timedelta(hours=1))
await omniq.enqueue("task", interval=timedelta(days=1))

# Complex intervals
await omniq.enqueue("task", interval=timedelta(days=1, hours=2))
await omniq.enqueue("task", interval=timedelta(hours=1, minutes=30, seconds=45))

# Backward compatibility
await omniq.enqueue("task", interval=3600)  # Automatically converted to timedelta(seconds=3600)
```

#### Working with Interval Tasks

```python
# Get task with interval
task = await omniq.get_task(task_id)
interval = task["schedule"].get("interval")

if interval:
    print(f"Task repeats every {interval}")
    print(f"Interval in seconds: {interval.total_seconds()}")
    
    # Calculate next run time
    from datetime import datetime, timezone
    next_run = datetime.now(timezone.utc) + interval
    print(f"Next run: {next_run}")
```

### Validation Checklist

- [ ] Update task creation to use `timedelta` where possible
- [ ] Update task model access to use `task["schedule"].get("interval")`
- [ ] Update serialization code to handle `timedelta` objects
- [ ] Test backward compatibility with existing `int` intervals
- [ ] Verify interval tasks reschedule correctly
- [ ] Update any custom storage backends to handle `timedelta` serialization

### Troubleshooting

#### Common Issues

1. **Type Errors**: Ensure you're importing `timedelta` from `datetime`
2. **Access Errors**: Use `task["schedule"].get("interval")` instead of `task["interval"]`
3. **Serialization**: Use provided `serialize_timedelta()` and `deserialize_timedelta()` functions

#### Getting Help

```python
# Test interval conversion
from datetime import timedelta
from src.omniq.queue import AsyncTaskQueue

queue = AsyncTaskQueue(storage)

# Test conversion utilities
td = queue._convert_interval(timedelta(hours=1))
assert td == timedelta(hours=1)

int_converted = queue._convert_interval(3600)
assert int_converted == timedelta(seconds=3600)
```

### Performance Considerations

- **Conversion Overhead**: Minimal overhead for int → timedelta conversion
- **Memory**: `timedelta` objects have similar memory footprint to ints
- **Serialization**: Slightly larger serialized size, but more descriptive
- **Compatibility**: Zero breaking changes for existing code

### Complete Migration Example

```python
import asyncio
from datetime import datetime, timezone, timedelta
from omniq import AsyncOmniQ
from omniq.config import Settings

async def migrate_interval_tasks():
    """Example of migrating to timedelta intervals."""
    
    # Initialize OmniQ
    settings = Settings(backend="sqlite")
    omniq = AsyncOmniQ(settings)
    
    # Create tasks with new timedelta intervals
    cleanup_task = await omniq.enqueue(
        "maintenance.cleanup",
        interval=timedelta(hours=6)  # Every 6 hours
    )
    
    backup_task = await omniq.enqueue(
        "maintenance.backup",
        interval=timedelta(days=1, hours=2)  # Daily at 2 AM
    )
    
    # Backward compatibility - existing code still works
    legacy_task = await omniq.enqueue(
        "legacy.process",
        interval=1800  # 30 minutes (int seconds)
    )
    
    # Check task intervals
    for task_id in [cleanup_task, backup_task, legacy_task]:
        task = await omniq.get_task(task_id)
        interval = task["schedule"].get("interval")
        
        if interval:
            print(f"Task {task_id}: repeats every {interval}")
            print(f"  Total seconds: {interval.total_seconds()}")
            
            # Calculate next execution
            next_run = datetime.now(timezone.utc) + interval
            print(f"  Next run: {next_run.isoformat()}")
    
    print("Migration to timedelta intervals completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate_interval_tasks())
```

This migration provides better type safety and expressiveness while maintaining full backward compatibility with existing code.

---

## TaskError Model Migration

This section covers the addition of the `TaskError` model for structured error handling and v1 compliance.

### Overview

The TaskError model provides comprehensive error information for failed tasks, including error categorization, retry logic, and debugging context. This replaces ad-hoc error string handling with a structured approach.

### What Changed

- **New TaskError Model**: Added comprehensive error model with fields for error type, message, timestamp, traceback, retry information, and context
- **Task Model Enhancement**: Added optional `error` field to Task model for structured error storage
- **Enhanced Error Handling**: Worker and core components now use TaskError for consistent error management
- **Storage Serialization**: All storage backends support TaskError serialization/deserialization
- **Backward Compatibility**: Existing tasks without errors continue to work (error field defaults to None)

### Migration Steps

#### 1. Update Task Creation
**Before (error strings):**
```python
# Old way - still works for backward compatibility
task_id = await omniq.enqueue("my_module.function", args=[data])
# Error handling in worker used strings
```

**After (TaskError - recommended):**
```python
from omniq.models import TaskError, ErrorType

# In your Task function
async def my_function(data):
    try:
        result = await process_data(data)
        return result
    except Exception as e:
        # Create structured error
        error = TaskError.from_exception(
            exception=e,
            error_type=ErrorType.VALIDATION.value,
            is_retryable=False,
            context={"data_size": len(data)}
        )
        # Error will be automatically captured by worker
        raise
```

#### 2. Error Handling in Workers
**New TaskError-aware error handling:**
```python
from omniq.models import TaskError, has_error, is_failed, get_error_message

# Worker automatically creates TaskError from exceptions
# No changes needed in user code for basic error handling

# For custom error handling
error = TaskError(
    error_type="timeout",
    message="Operation timed out",
    is_retryable=True,
    max_retries=3,
    context={"timeout": 30}
)
```

#### 3. Task Error Checking
**New helper methods available:**
```python
from omniq.models import has_error, is_failed, get_error_message

task = await omniq.get_task(task_id)

# Check if task has error
if has_error(task):
    error = task["error"]
    print(f"Error type: {error.error_type}")
    print(f"Can retry: {error.can_retry()}")

# Check if task is failed
if is_failed(task):
    print("Task is in failed state")

# Get error message safely
error_msg = get_error_message(task)
if error_msg:
    print(f"Task failed: {error_msg}")
```

#### 4. Storage and Serialization
**Automatic TaskError handling:**
- All storage backends automatically serialize/deserialize TaskError
- No changes needed for existing code
- Backward compatibility maintained for tasks without errors

**Manual TaskError creation:**
```python
from omniq.models import TaskError, create_task

# Create task with error
error = TaskError(
    error_type="business",
    message="Invalid business logic",
    is_retryable=False,
    context={"rule": "validation_failed"}
)

task = create_task(
    func_path="my_module.function",
    args=[data],
    error=error  # Attach error to task
)
```

### Backward Compatibility

- **Existing Tasks**: Tasks without `error` field continue to work (defaults to None)
- **Error Strings**: Old string-based error handling still supported
- **Storage**: Existing serialized tasks deserialize without errors
- **API**: All existing code continues to work unchanged

### New TaskError Features

#### Error Classification
```python
from omniq.models import TaskError, ErrorType

# Standard error types
error = TaskError(
    error_type=ErrorType.TIMEOUT.value,  # "timeout"
    message="Task exceeded 30 second limit",
    is_retryable=True
)

# Auto-categorization
# error_type="timeout" → category="system"
# error_type="validation" → category="user"
# error_type="runtime" → category="application"
```

#### Retry Logic
```python
# Check if error can be retried
if error.can_retry():
    print("Task will be retried")
else:
    print("Task is permanently failed")

# Increment retry count
next_error = error.increment_retry()
print(f"Retry attempt: {next_error.retry_count}")
```

#### Context and Debugging
```python
# Rich error context
error = TaskError(
    error_type="resource",
    message="Database connection failed",
    context={
        "database": "postgres",
        "host": "db.example.com",
        "query": "SELECT * FROM users",
        "connection_pool_size": 10
    }
)

# Exception details automatically captured
error = TaskError.from_exception(
    exception=db_exception,
    context={"operation": "user_lookup"}
)
# Includes traceback, exception_type, timestamp
```

### Validation Checklist

- [ ] TaskError model creation works with all fields
- [ ] TaskError.from_exception() captures exception details
- [ ] TaskError serialization/deserialization roundtrip works
- [ ] Storage backends handle TaskError correctly
- [ ] Worker creates TaskError on exceptions
- [ ] Helper functions (has_error, is_failed, get_error_message) work
- [ ] Backward compatibility maintained for tasks without errors
- [ ] Error categorization works automatically
- [ ] Retry logic functions correctly with TaskError
- [ ] Context information preserved in storage
- [ ] Performance requirements met (<1ms creation, <1ms serialization)
- [ ] Type safety maintained with proper annotations

### Benefits of Migration

1. **Structured Error Handling**: Consistent error format across all components
2. **Enhanced Debugging**: Rich context information for troubleshooting
3. **Smart Retry Logic**: Automatic retry decisions based on error type and count
4. **Error Analytics**: Categorized errors for monitoring and analysis
5. **Type Safety**: Full type annotations and validation
6. **Backward Compatibility**: Zero breaking changes for existing code
7. **Production Ready**: Comprehensive error information for operations

### Troubleshooting

#### Common Issues

1. **TaskError Not Found**: 
   - Cause: Task created before TaskError implementation
   - Fix: Tasks automatically get error=None, no action needed

2. **Serialization Errors**:
   - Cause: Custom serializer not handling TaskError
   - Fix: Use built-in serializers or add TaskError.to_dict() support

3. **Type Errors**:
   - Cause: Passing error string instead of TaskError
   - Fix: Use TaskError.from_exception() or create TaskError objects

#### Performance Considerations

- **TaskError Creation**: <1ms average, includes exception processing
- **Serialization**: <1ms average, uses efficient JSON conversion
- **Storage Overhead**: Minimal, only stored when tasks fail
- **Memory Usage**: Similar to existing task objects

### Complete Example

```python
import asyncio
from datetime import timedelta
from omniq import AsyncOmniQ
from omniq.models import TaskError, ErrorType

async def process_with_comprehensive_errors(data):
    """Example function with comprehensive error handling."""
    try:
        # Simulate different error conditions
        if not data:
            raise ValueError("Data cannot be empty")
        
        if len(data) > 1000:
            raise TimeoutError("Data too large to process")
            
        # Simulate processing
        await asyncio.sleep(0.1)
        return {"processed": len(data)}
        
    except ValueError as e:
        # Non-retryable validation error
        raise TaskError.from_exception(
            e,
            error_type=ErrorType.VALIDATION.value,
            is_retryable=False,
            context={"data_length": len(data) if data else 0}
        )
        
    except TimeoutError as e:
        # Retryable timeout error
        raise TaskError.from_exception(
            e,
            error_type=ErrorType.TIMEOUT.value,
            is_retryable=True,
            max_retries=3,
            context={"data_length": len(data) if data else 0}
        )

async def main():
    omniq = AsyncOmniQ()
    
    # Enqueue task that might fail
    task_id = await omniq.enqueue(
        process_with_comprehensive_errors,
        args=[{"large_data": "x" * 2000}],  # Will cause timeout
        max_retries=3
    )
    
    # Process with worker
    async with omniq.worker_pool() as workers:
        await workers.process_tasks(limit=10)
    
    # Check result
    result = await omniq.get_result(task_id, wait=True)
    if result and result.get("error"):
        error = result["error"]
        print(f"Final error: {error.error_type}")
        print(f"Error message: {error.message}")
        print(f"Context: {error.context}")

if __name__ == "__main__":
    asyncio.run(main())
```

This migration provides comprehensive error handling while maintaining full backward compatibility and adding powerful new debugging and monitoring capabilities.

---

## Worker Compatibility Migration

This section covers migration for AsyncWorkerPool constructor to restore backward compatibility while encouraging migration to the new queue-based interface.

### Overview

The AsyncWorkerPool constructor has been updated to support both the new `queue` parameter and the legacy `storage` parameter, maintaining backward compatibility while providing a clear migration path to the new interface.

### What Changed

- **Dual Interface Support**: Constructor now accepts both `queue` and `storage` parameters
- **Backward Compatibility**: Existing code using `storage` parameter continues to work
- **Deprecation Warnings**: Legacy `storage` parameter triggers deprecation warnings
- **Internal Queue Creation**: When `storage` is provided, AsyncTaskQueue is created automatically
- **Parameter Validation**: Clear error messages for invalid parameter combinations

### Migration Steps

#### 1. Immediate (No Changes Required)

**Existing code continues to work:**
```python
from omniq.worker import AsyncWorkerPool
from omniq.storage.file import FileStorage

# Legacy interface - still works with deprecation warning
storage = FileStorage("./data", JSONSerializer())
worker = AsyncWorkerPool(storage=storage, concurrency=4)
```

#### 2. Recommended Migration

**Migrate to new queue interface:**
```python
from omniq.worker import AsyncWorkerPool
from omniq.queue import AsyncTaskQueue
from omniq.storage.file import FileStorage

# New recommended interface
storage = FileStorage("./data", JSONSerializer())
queue = AsyncTaskQueue(storage=storage)
worker = AsyncWorkerPool(queue=queue, concurrency=4)
```

#### 3. Best Practice (AsyncOmniQ)

**Use AsyncOmniQ for automatic setup:**
```python
from omniq import AsyncOmniQ
from omniq.config import Settings

# Recommended - AsyncOmniQ handles everything
settings = Settings()
omniq = AsyncOmniQ(settings=settings)
worker = omniq.worker(concurrency=4)  # Queue and storage created automatically
```

### Constructor Changes

#### New Signature

```python
def __init__(
    self,
    queue: Optional[AsyncTaskQueue] = None,        # New parameter (recommended)
    storage: Optional[BaseStorage] = None,           # Legacy parameter (deprecated)
    concurrency: int = 1,
    poll_interval: float = 1.0,
    logger: Optional[Logger] = None,
):
```

#### Parameter Validation

```python
# Valid combinations
AsyncWorkerPool(queue=queue)                    # New interface
AsyncWorkerPool(storage=storage)                # Legacy interface (with warning)
AsyncWorkerPool(queue=queue, logger=custom)     # New interface with logger

# Invalid combinations
AsyncWorkerPool()                               # Error: no parameters
AsyncWorkerPool(queue=queue, storage=storage)   # Error: both parameters
AsyncWorkerPool(queue="invalid")                # Error: wrong type
AsyncWorkerPool(storage="invalid")               # Error: wrong type
```

### Deprecation Warnings

#### Warning Message

```
DeprecationWarning: Passing 'storage' to AsyncWorkerPool is deprecated. 
Use 'queue' parameter instead: AsyncWorkerPool(queue=AsyncTaskQueue(storage=storage))
```

#### Capturing Warnings

```python
import warnings

# Capture deprecation warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    worker = AsyncWorkerPool(storage=storage)
    
    if w:
        print(f"Deprecation warning: {w[0].message}")
        print(f"Stack level: {w[0].lineno}")
```

### Migration Examples

#### Basic Worker Creation

**Before (legacy):**
```python
from omniq.worker import AsyncWorkerPool
from omniq.storage.sqlite import SQLiteStorage

storage = SQLiteStorage("tasks.db")
worker = AsyncWorkerPool(storage=storage, concurrency=2)
```

**After (new interface):**
```python
from omniq.worker import AsyncWorkerPool
from omniq.queue import AsyncTaskQueue
from omniq.storage.sqlite import SQLiteStorage

storage = SQLiteStorage("tasks.db")
queue = AsyncTaskQueue(storage=storage)
worker = AsyncWorkerPool(queue=queue, concurrency=2)
```

#### Worker with Custom Logger

**Before (legacy):**
```python
import logging
from omniq.worker import AsyncWorkerPool

custom_logger = logging.getLogger("my_worker")
worker = AsyncWorkerPool(storage=storage, logger=custom_logger)
```

**After (new interface):**
```python
import logging
from omniq.worker import AsyncWorkerPool

custom_logger = logging.getLogger("my_worker")
worker = AsyncWorkerPool(queue=queue, logger=custom_logger)
```

#### WorkerPool (Sync Wrapper)

**Before (legacy):**
```python
from omniq.worker import WorkerPool

worker = WorkerPool(storage=storage, concurrency=4)
```

**After (new interface):**
```python
from omniq.worker import WorkerPool

worker = WorkerPool(queue=queue, concurrency=4)
```

### AsyncOmniQ Integration

The AsyncOmniQ class has been updated to use the new interface internally:

```python
from omniq import AsyncOmniQ

# AsyncOmniQ automatically uses new interface
omniq = AsyncOmniQ()
worker = omniq.worker(concurrency=2)

# Internally equivalent to:
# queue = AsyncTaskQueue(storage=omniq._storage)
# worker = AsyncWorkerPool(queue=queue, concurrency=2)
```

### Benefits of Migration

1. **Clear Separation**: Queue handles task operations, worker handles execution
2. **Better Architecture**: More explicit dependency injection
3. **Future-Proof**: New features will be queue-focused
4. **Type Safety**: Better type hints and validation
5. **Testing**: Easier to mock and test components separately

### Validation Checklist

- [ ] Update worker creation to use `queue` parameter
- [ ] Update WorkerPool creation to use `queue` parameter  
- [ ] Verify deprecation warnings appear for legacy usage
- [ ] Test parameter validation error messages
- [ ] Confirm AsyncOmniQ integration works
- [ ] Update any custom worker subclasses
- [ ] Update documentation and examples
- [ ] Test both interfaces work correctly

### Troubleshooting

#### Common Issues

1. **Deprecation Warnings**: 
   - **Cause**: Using legacy `storage` parameter
   - **Fix**: Migrate to `queue` parameter

2. **Parameter Validation Errors**:
   - **Cause**: Providing both `queue` and `storage` or neither
   - **Fix**: Provide exactly one parameter

3. **Type Errors**:
   - **Cause**: Passing wrong types to parameters
   - **Fix**: Ensure `queue` is AsyncTaskQueue, `storage` is BaseStorage

#### Getting Help

```python
# Test both interfaces
from omniq.worker import AsyncWorkerPool
from omniq.queue import AsyncTaskQueue
from omniq.storage.file import FileStorage
import warnings

storage = FileStorage("./test", JSONSerializer())

# Test new interface
queue = AsyncTaskQueue(storage=storage)
worker_new = AsyncWorkerPool(queue=queue)
print("New interface works")

# Test legacy interface with warning
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    worker_legacy = AsyncWorkerPool(storage=storage)
    print(f"Legacy interface works with {len(w)} warning(s)")
```

### Performance Considerations

- **Queue Creation**: Minimal overhead when creating queue from storage
- **Memory**: Similar memory footprint for both interfaces
- **Performance**: No performance difference after initialization
- **Migration**: Zero runtime performance impact

### Complete Migration Example

```python
import asyncio
import warnings
from omniq import AsyncOmniQ
from omniq.worker import AsyncWorkerPool
from omniq.queue import AsyncTaskQueue
from omniq.storage.file import FileStorage
from omniq.serialization import JSONSerializer

async def migrate_worker_creation():
    """Example of migrating worker creation patterns."""
    
    print("=== Worker Compatibility Migration Example ===\n")
    
    # 1. Legacy interface (still works with warning)
    print("1. Testing legacy interface...")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        storage = FileStorage("./legacy_data", JSONSerializer())
        legacy_worker = AsyncWorkerPool(storage=storage, concurrency=2)
        
        if w:
            print(f"   Deprecation warning: {w[0].message}")
        print("   ✓ Legacy interface works\n")
    
    # 2. New interface (recommended)
    print("2. Testing new interface...")
    storage = FileStorage("./new_data", JSONSerializer())
    queue = AsyncTaskQueue(storage=storage)
    new_worker = AsyncWorkerPool(queue=queue, concurrency=2)
    print("   ✓ New interface works without warnings\n")
    
    # 3. AsyncOmniQ integration (best practice)
    print("3. Testing AsyncOmniQ integration...")
    omniq = AsyncOmniQ()
    omniq_worker = omniq.worker(concurrency=2)
    print("   ✓ AsyncOmniQ integration works\n")
    
    # 4. Error handling
    print("4. Testing error handling...")
    
    try:
        AsyncWorkerPool()  # No parameters
    except ValueError as e:
        print(f"   ✓ No parameters error: {e}")
    
    try:
        AsyncWorkerPool(queue=queue, storage=storage)  # Both parameters
    except ValueError as e:
        print(f"   ✓ Both parameters error: {e}")
    
    try:
        AsyncWorkerPool(queue="invalid")  # Wrong type
    except TypeError as e:
        print(f"   ✓ Type error: {e}")
    
    print("\n=== Migration Complete ===")
    print("Recommendation: Use AsyncOmniQ for automatic setup,")
    print("or migrate to queue parameter for explicit control.")

if __name__ == "__main__":
    asyncio.run(migrate_worker_creation())
```

### Timeline

- **v1.x**: Legacy interface supported with deprecation warnings
- **v2.0**: Legacy interface will be removed (breaking change)
- **Migration Period**: Extended support for legacy interface during v1.x lifecycle

This migration ensures backward compatibility while providing a clear path forward to the improved queue-based architecture.