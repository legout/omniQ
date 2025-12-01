# Migration Guide

This guide helps you migrate OmniQ components while maintaining backward compatibility.

## Table of Contents

1. [Storage Interface Migration](#storage-interface-migration)
2. [Logging Migration](#logging-migration)

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