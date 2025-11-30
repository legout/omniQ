# OmniQ Task Queue Library

A modern, async-first task queue library for Python with support for multiple storage backends and structured logging.

## Features

- **Async-first design**: Built for Python's async/await
- **Multiple storage backends**: File-based and SQLite storage
- **Structured logging**: Powered by Loguru with enhanced capabilities
- **Task scheduling**: Support for delayed execution with ETA
- **Retry mechanisms**: Configurable retry policies
- **Worker pools**: Concurrent task execution
- **Type safety**: Full type annotations throughout

## Installation

```bash
pip install omniq
```

## Quick Start

```python
import asyncio
from omniq import AsyncOmniQ
from omniq.config import Settings

async def main():
    # Initialize with default settings
    omniq = AsyncOmniQ(Settings())
    
    # Enqueue a task
    task_id = await omniq.enqueue("my_module.my_function", args=[1, 2])
    
    # Process tasks with worker
    async with omniq.worker_pool() as workers:
        await workers.process_tasks(limit=10)

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Basic Configuration

```python
from omniq.config import Settings

# Use SQLite backend
settings = Settings(
    backend="sqlite",
    base_dir="/path/to/data"
)

# Use file backend
settings = Settings(
    backend="file", 
    base_dir="/path/to/data"
)
```

### Logging Configuration

OmniQ uses Loguru for enhanced logging capabilities. You can configure logging in several ways:

#### Basic Configuration

```python
from omniq.logging import configure_logging

# Basic configuration
configure_logging(level="INFO")

# Custom format
configure_logging(
    level="DEBUG",
    format="{time} | {level} | {message}"
)

# File logging with rotation
configure_logging(
    level="INFO",
    rotation="10 MB",
    retention="1 week",
    log_file="omniq.log"
)
```

#### Environment Variables

```bash
# Set log level using either variable
export OMNIQ_LOG_LEVEL=DEBUG
export LOGURU_LEVEL=INFO

# The library checks both variables for compatibility
```

#### Structured Logging

```python
from omniq.logging import log_structured, add_structured_context

# Add context to all subsequent logs
add_structured_context(service="my-app", environment="production")

# Log structured data
log_structured("info", "Task processed", 
    task_id="task-123", 
    duration=1.5, 
    status="success"
)

# Log exceptions with full traceback
log_exception("Task failed", 
    task_id="task-123", 
    error_type="ValueError"
)
```

## Storage Backends

### File Storage

Simple file-based storage using JSON serialization:

```python
from omniq.config import Settings

settings = Settings(
    backend="file",
    base_dir="./omniq_data"
)
```

### SQLite Storage

Transactional SQLite storage with proper indexing:

```python
from omniq.config import Settings

settings = Settings(
    backend="sqlite",
    base_dir="./omniq_data"  # Will create omniq.db
)
```

## Task Management

### Creating Tasks

```python
# Simple task
task_id = await omniq.enqueue("my_module.process_data", args=[data])

# Task with options
task_id = await omniq.enqueue(
    "my_module.process_data",
    args=[data],
    kwargs={"option": True},
    max_retries=3,
    timeout=30.0,
    eta=datetime.now() + timedelta(minutes=5)  # Delayed execution
)
```

### Task Functions

Your task functions should be async and accept the parameters you specify:

```python
# my_module.py
async def process_data(data, option=False):
    """Process some data asynchronously."""
    result = await some_async_operation(data)
    if option:
        result = apply_option(result)
    return result
```

## Worker Management

### Basic Worker

```python
async with omniq.worker_pool() as workers:
    # Process tasks for 60 seconds
    await workers.process_tasks(duration=60)
    
    # Or process a specific number of tasks
    await workers.process_tasks(limit=100)
```

### Advanced Worker Configuration

```python
from omniq.worker import AsyncWorkerPool

# Custom worker configuration
workers = AsyncWorkerPool(
    storage=storage,
    serializer=serializer,
    concurrency=4,  # Number of concurrent workers
    poll_interval=1.0,  # Seconds between task polls
    max_retries=3,  # Default retry policy
    default_timeout=30.0  # Default task timeout
)

async with workers:
    await workers.process_tasks(duration=300)
```

## Logging

OmniQ provides structured logging out of the box:

### Task Events

```python
from omniq.logging import (
    log_task_enqueued, log_task_started, 
    log_task_completed, log_task_failed
)

# These are called automatically by the library
# but you can use them for custom logging too
log_task_enqueued("task-123", "my_module.my_function")
log_task_started("task-123", 1)
log_task_completed("task-123", 1)
log_task_failed("task-123", "Error message", will_retry=True)
```

### Worker Events

```python
from omniq.logging import log_worker_started, log_worker_stopped

log_worker_started(concurrency=4)
log_worker_stopped()
```

### Error Logging

```python
from omniq.logging import log_storage_error, log_serialization_error

log_storage_error("enqueue", "Database connection failed")
log_serialization_error("deserialize", "Invalid JSON format")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OMNIQ_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO |
| `LOGURU_LEVEL` | Alternative log level name (for Loguru compatibility) | INFO |

## Migration from Standard Logging

If you're migrating from the standard Python `logging` module:

1. **Environment Variables**: Both `OMNIQ_LOG_LEVEL` (old) and `LOGURU_LEVEL` (new) are supported
2. **Function Calls**: All existing logging function calls remain the same
3. **Enhanced Features**: You can now use structured logging and better exception handling

```python
# Old way (still works)
import logging
logger = logging.getLogger("omniq")
logger.info("Task completed")

# New way (recommended)
from omniq.logging import log_structured
log_structured("info", "Task completed", task_id="task-123", duration=1.5)
```

## API Reference

### Core Classes

- `AsyncOmniQ`: Main async interface for task queue operations
- `AsyncWorkerPool`: Worker pool for concurrent task execution
- `Settings`: Configuration settings for the queue system

### Storage Classes

- `FileStorage`: File-based storage backend
- `SQLiteStorage`: SQLite-based storage backend
- `BaseStorage`: Abstract base class for storage implementations

### Logging Functions

- `configure_logging()`: Configure logging behavior
- `log_structured()`: Log structured messages with context
- `log_exception()`: Log exceptions with full traceback
- Task-specific logging functions: `log_task_*()`, `log_worker_*()`, etc.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run specific test files
python test_logging.py
python test_sqlite_storage.py
```

### Project Structure

```
omniq/
├── src/omniq/
│   ├── __init__.py
│   ├── core.py          # Main queue implementation
│   ├── config.py        # Configuration management
│   ├── models.py        # Task and result models
│   ├── logging.py       # Logging configuration
│   ├── serialization.py # Task serialization
│   ├── worker.py        # Worker implementation
│   └── storage/         # Storage backends
│       ├── __init__.py
│       ├── base.py      # Abstract storage interface
│       ├── file.py      # File-based storage
│       └── sqlite.py    # SQLite storage
├── tests/               # Test files
└── docs/               # Documentation
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]