# Migration Guide: From Standard Logging to Loguru

This guide helps you migrate from the standard Python `logging` module to Loguru in the context of OmniQ.

## Overview

OmniQ has upgraded its logging system from Python's standard `logging` module to [Loguru](https://github.com/Delgan/loguru) for better performance, structured logging, and enhanced features.

## What Changed

- **Backend**: Standard `logging` → Loguru
- **Enhanced Features**: Structured logging, better exception handling, automatic formatting
- **Backward Compatibility**: All existing function calls continue to work
- **New Capabilities**: Context management, file rotation, compression

## Environment Variables

### Old vs New

Both old and new environment variables are supported for backward compatibility:

| Old Variable | New Variable | Status |
|--------------|--------------|--------|
| `OMNIQ_LOG_LEVEL` | `LOGURU_LEVEL` | Both supported |
| N/A | `OMNIQ_LOG_FORMAT` | New (Loguru format strings) |
| N/A | `OMNIQ_LOG_ROTATION` | New (file rotation) |

### Migration Steps

```bash
# Old way (still works)
export OMNIQ_LOG_LEVEL=DEBUG

# New way (recommended)
export LOGURU_LEVEL=DEBUG
export OMNIQ_LOG_FORMAT="{time} | {level} | {message}"
export OMNIQ_LOG_ROTATION="10 MB"
```

## Code Migration

### Basic Logging

**Before (still works):**
```python
import logging
from omniq.logging import get_logger

logger = get_logger()
logger.info("Task completed")
logger.error("Something went wrong")
```

**After (recommended):**
```python
from omniq.logging import log_structured

# Structured logging with context
log_structured("info", "Task completed", 
    task_id="task-123", 
    duration=1.5, 
    status="success")

log_structured("error", "Something went wrong",
    error_type="ValueError",
    task_id="task-123")
```

### Exception Handling

**Before:**
```python
import logging
import traceback

try:
    risky_operation()
except Exception as e:
    logger = get_logger()
    logger.error(f"Operation failed: {e}")
    logger.error(traceback.format_exc())
```

**After:**
```python
from omniq.logging import log_exception

try:
    risky_operation()
except Exception as e:
    log_exception("Operation failed", 
        operation="risky_operation",
        user_id="user-123")
    # Automatically includes full traceback
```

### Configuration

**Before:**
```python
from omniq.logging import configure_logging

configure_logging(level="DEBUG")
```

**After (enhanced):**
```python
from omniq.logging import configure_logging

configure_logging(
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    rotation="10 MB",
    retention="1 week",
    compression="gz"
)
```

## New Features

### 1. Structured Logging

Add contextual data to your logs:

```python
from omniq.logging import add_structured_context, log_structured

# Add context to all subsequent logs
add_structured_context(
    service="my-app",
    environment="production",
    version="1.0.0"
)

# All logs will now include this context
log_structured("info", "User logged in", user_id="123", ip="192.168.1.1")
```

### 2. Better Exception Formatting

Loguru automatically formats exceptions with color and context:

```python
from omniq.logging import log_exception

try:
    # Some complex nested code
    process_data(data)
except Exception:
    log_exception("Data processing failed")
    # Output includes:
    # - Full traceback with syntax highlighting
    # - Variable values in traceback
    # - File paths and line numbers
```

### 3. File Rotation and Compression

Automatic log file management:

```python
from omniq.logging import configure_logging

configure_logging(
    level="INFO",
    log_file="app.log",
    rotation="10 MB",        # Rotate when file reaches 10MB
    retention="1 week",      # Keep logs for 1 week
    compression="gz"         # Compress old logs
)
```

### 4. Custom Formatting

Powerful format strings with built-in variables:

```python
configure_logging(
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
)
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

# These all work exactly as before
log_task_enqueued("task-123", "module.function")
log_task_started("task-123", 1)
log_task_completed("task-123", 1)
log_task_failed("task-123", "Error message", will_retry=True)
```

### What's Enhanced

These functions now automatically include structured data when using Loguru:

```python
# Before: Simple string message
# "Task enqueued: task-123 -> module.function"

# After: Structured log with context
# "Task enqueued" task_id="task-123" func_path="module.function"
```

## Performance Considerations

### Loguru Benefits

- **Faster**: Loguru is optimized for performance
- **Less Boilerplate**: No need to configure handlers and formatters
- **Memory Efficient**: Automatic log rotation prevents memory issues
- **Thread Safe**: Built-in thread safety for concurrent applications

### Migration Impact

- **Zero Downtime**: Backward compatibility ensures smooth transition
- **Gradual Adoption**: Can migrate to new features incrementally
- **Performance Improvement**: Should see better logging performance

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Loguru is installed (`pip install loguru`)
2. **Format Strings**: Use Loguru format syntax, not logging module syntax
3. **File Permissions**: Ensure write permissions for log files with rotation

### Getting Help

```python
from omniq.logging import LOGURU_AVAILABLE

if not LOGURU_AVAILABLE:
    print("Loguru not available, falling back to standard logging")
```

## Best Practices

### 1. Use Structured Logging

```python
# Good
log_structured("info", "API request completed", 
    method="POST", 
    endpoint="/api/tasks", 
    status_code=200, 
    duration_ms=150)

# Avoid
log_structured("info", f"API request completed: POST /api/tasks -> 200 in 150ms")
```

### 2. Add Context Early

```python
# At application startup
add_structured_context(
    service="omniq-worker",
    environment=os.getenv("ENV", "development"),
    version="1.0.0"
)
```

### 3. Use Appropriate Log Levels

```python
log_structured("trace", "Detailed debugging info")     # Very verbose
log_structured("debug", "Development debugging")       # Debug info
log_structured("info", "Normal application flow")      # General info
log_structured("warning", "Unexpected but recoverable") # Issues
log_structured("error", "Error conditions")            # Errors
log_structured("critical", "Critical failures")       # Critical
```

### 4. Leverage Exception Logging

```python
try:
    process_task(task)
except Exception:
    log_exception("Task processing failed", 
        task_id=task.id,
        task_type=task.func_path)
    # Don't re-raise if you've logged the exception properly
```

## Complete Example

Here's a complete example of a migrated application:

```python
import os
from omniq import AsyncOmniQ
from omniq.config import Settings
from omniq.logging import configure_logging, add_structured_context, log_structured

async def main():
    # Configure logging with Loguru
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="{time} | {level} | {message}",
        rotation="10 MB",
        retention="1 week"
    )
    
    # Add structured context
    add_structured_context(
        service="task-processor",
        environment=os.getenv("ENV", "development")
    )
    
    # Initialize OmniQ
    settings = Settings(backend="sqlite")
    omniq = AsyncOmniQ(settings)
    
    log_structured("info", "Application started", 
        backend=settings.backend.value,
        log_level=os.getenv("LOG_LEVEL", "INFO"))
    
    # Process tasks
    async with omniq.worker_pool() as workers:
        await workers.process_tasks(duration=300)
    
    log_structured("info", "Application shutdown complete")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Conclusion

The migration to Loguru provides enhanced logging capabilities while maintaining full backward compatibility. You can:

1. **Continue using existing code** without changes
2. **Gradually adopt new features** like structured logging
3. **Benefit from improved performance** and better formatting
4. **Use advanced features** like file rotation and compression

The migration is designed to be seamless, allowing you to upgrade at your own pace.