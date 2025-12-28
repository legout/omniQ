# OmniQ Task Queue Library

A modern, async-first task queue library for Python with support for multiple storage backends, enhanced logging, and a clean separation of concerns between task queue, worker, and storage layers.

## Features

- **Async-first design**: Built for Python's async/await
- **Core task queue engine**: `AsyncTaskQueue` class handles enqueue/dequeue logic, scheduling, and retries
- **Clean architecture**: Separation of concerns between queue, worker, and storage layers
- **Multiple storage backends**: File-based and SQLite storage
- **Enhanced logging**: Loguru-based logging with correlation IDs and structured output
- **Task scheduling**: Support for delayed execution with ETA and interval tasks
- **Retry mechanisms**: Configurable retry policies with exponential backoff with jitter
- **Worker pools**: Concurrent task execution with proper task lifecycle management
- **Type safety**: Full type annotations throughout
- **Interval tasks**: Repeating tasks with timedelta or int seconds support

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

### Enhanced Logging Configuration

OmniQ uses Loguru for enhanced logging with correlation IDs, structured output, and production-ready features.

#### Basic Configuration

```python
from omniq.logging import configure, get_logger

# Configure with smart defaults
configure(level="INFO")

# Get logger for custom logging
logger = get_logger()
logger.info("Application started")
```

#### Task Context Logging

```python
from omniq.logging import task_context, bind_task

# Automatic correlation ID and timing
with task_context("task-123", "process") as logger:
    logger.info("Processing task")
    # All logs include correlation_id and timing

# Manual context binding
logger = bind_task("task-456", worker="worker-1")
logger.info("Task enqueued")
```

#### Environment Variables

```bash
# Basic configuration
export OMNIQ_LOG_LEVEL=DEBUG          # DEBUG, INFO, WARNING, ERROR
export OMNIQ_LOG_MODE=PROD           # DEV (default) or PROD

# Production features
export OMNIQ_LOG_FILE=/var/log/omniq/app.log
export OMNIQ_LOG_ROTATION="100 MB"
export OMNIQ_LOG_RETENTION="30 days"
```

#### Task and Worker Events

```python
from omniq.logging import (
    log_task_enqueued, log_task_started, 
    log_task_completed, log_task_failed,
    log_worker_started, log_worker_stopped
)

# These are called automatically by the library
# but you can use them for custom logging too
log_task_enqueued("task-123", "my_module.my_function")
log_task_started("task-123", 1)
log_task_completed("task-123", 1)
log_task_failed("task-123", "Error message", will_retry=True)
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

# Interval task (repeating)
task_id = await omniq.enqueue(
    "my_module.cleanup_task",
    interval=timedelta(hours=1)  # Run every hour
)

# Interval task with int seconds (backward compatibility)
task_id = await omniq.enqueue(
    "my_module.cleanup_task", 
    interval=3600  # Run every hour (int seconds)
)
```

### Task Error Handling

OmniQ provides comprehensive error handling with the `TaskError` model:

```python
from omniq.models import TaskError, TaskStatus

# Creating TaskError from exception
try:
    result = await some_operation()
except Exception as e:
    error = TaskError.from_exception(
        exception=e,
        error_type="runtime",
        is_retryable=True,
    )
    # Error will be stored with task and used for retry logic

# Checking task errors
task = await omniq.get_task(task_id)
if task.get("error"):
    error = task["error"]
    print(f"Error type: {error.error_type}")
    print(f"Error message: {error.message}")
    print(f"Can retry: {error.can_retry()}")
    print(f"Retry count: {error.retry_count}")

# Task error helper methods
from omniq.models import has_error, is_failed, get_error_message

if has_error(task):
    print(f"Task has error: {get_error_message(task)}")

if is_failed(task):
    print("Task is in failed state")

# TaskError retry logic
if error.can_retry():
    next_error = error.increment_retry()
    # Use next_error for retry attempt
```

### Interval Tasks

Interval tasks are repeating tasks that run automatically at specified intervals:

```python
from datetime import timedelta

# Create an interval task that runs every 30 minutes
task_id = await omniq.enqueue(
    "my_module.maintenance_task",
    interval=timedelta(minutes=30)
)

# Interval tasks automatically reschedule after completion
# Each execution creates a new task with the same interval
```

**Important**: Interval tasks use `timedelta` objects for the interval field. For backward compatibility, you can also pass integers (seconds), which will be automatically converted to `timedelta`.

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

## AsyncTaskQueue Architecture

OmniQ features a clean separation of concerns with the `AsyncTaskQueue` at its core:

### Core Components

- **AsyncTaskQueue**: Handles all task queue logic including enqueue/dequeue, scheduling, retries, and interval task management
- **AsyncWorkerPool**: Manages concurrent task execution and communicates with AsyncTaskQueue
- **Storage Backends**: Provide persistence (File, SQLite) and are abstracted from queue logic

### Benefits

- **Modularity**: Each component has a single responsibility
- **Testability**: Queue logic can be tested independently of workers and storage
- **Maintainability**: Changes to retry logic or scheduling don't affect worker implementation
- **Extensibility**: New storage backends can be added without modifying queue or worker code

### AsyncTaskQueue Key Methods

```python
from omniq.queue import AsyncTaskQueue
from omniq.storage.sqlite import SQLiteStorage

# Initialize with storage backend
storage = SQLiteStorage("path/to/db")
queue = AsyncTaskQueue(storage)

# Enqueue task with scheduling
task_id = await queue.enqueue(
    func_path="my_module.my_function",
    args=[1, 2],
    kwargs={"option": True},
    eta=datetime.now() + timedelta(minutes=5),  # Delayed execution
    interval=timedelta(hours=1),  # Repeating task
    max_retries=3,
    timeout=30
)

# Dequeue next due task (FIFO ordering)
task = await queue.dequeue()

# Complete task (handles interval rescheduling)
await queue.complete_task(task_id, result="success", task=task)

# Fail task with retry logic (exponential backoff with jitter)
await queue.fail_task(task_id, error="Something went wrong", task=task)
```

## Retry Budget Semantics

OmniQ uses a clear retry budget model to control task retry behavior:

### Key Concepts

- **`attempts`**: Number of times a task has been claimed for execution (starts at 0, increments on each `PENDING → RUNNING` transition)
- **`max_retries`**: Maximum total executions allowed for a task
- **Retry predicate**: `attempts < max_retries` (not `<=` - this allows exactly `max_retries` total executions)

### Retry Behavior

1. **Task execution**: Each time a task transitions from `PENDING` to `RUNNING`, the `attempts` counter increments
2. **Retry decision**: After a failure, the queue checks `attempts < max_retries` to determine if retry is allowed
3. **Retry scheduling**: If retry is allowed, queue calculates exponential backoff delay with jitter and reschedules task
4. **Final failure**: When `attempts >= max_retries`, task is marked as permanently failed

### Example

```python
from omniq.models import create_task

# Create task with max_retries=3
task = create_task(
    func_path="my_module.my_function",
    max_retries=3,  # Allow 4 total executions (initial + 3 retries)
)

# Execution flow:
# 1. First execution: attempts=0, on PENDING→RUNNING becomes attempts=1, fails → retry
# 2. First retry: attempts=1, becomes attempts=2, fails → retry
# 3. Second retry: attempts=2, becomes attempts=3, fails → retry
# 4. Third retry: attempts=3, becomes attempts=4, fails → no retry (attempts >= max_retries)
# 5. Task marked as permanently failed
```

### Retry Delay Calculation

The queue computes retry delays using exponential backoff with jitter:

- **Base delay**: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
- **Jitter**: ±25% random variation to prevent thundering herd
- **Worker delegation**: Worker does NOT calculate delays - queue owns retry policy

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

## Enhanced Logging

OmniQ provides enhanced logging with Loguru, featuring correlation IDs, structured output, and production-ready features:

### Core API (4 Functions)

```python
from omniq.logging import configure, get_logger, task_context, bind_task

# 1. Configure logging with smart defaults
configure(level="INFO", rotation="100 MB", retention="30 days")

# 2. Get logger instance
logger = get_logger()
logger.info("Application started")

# 3. Task context with automatic correlation
with task_context("task-123", "process") as task_logger:
    task_logger.info("Processing data")
    # Automatic correlation_id, timing, and error handling

# 4. Manual context binding
bound_logger = bind_task("task-456", worker="worker-1", operation="enqueue")
bound_logger.info("Task enqueued with context")
```

### Environment-Based Configuration

```bash
# Development mode (default)
# Colored console output, detailed formatting
export OMNIQ_LOG_MODE=DEV
export OMNIQ_LOG_LEVEL=DEBUG

# Production mode
# JSON structured output, file rotation, compression
export OMNIQ_LOG_MODE=PROD
export OMNIQ_LOG_LEVEL=INFO
export OMNIQ_LOG_FILE=/var/log/omniq/app.log
export OMNIQ_LOG_ROTATION="100 MB"
export OMNIQ_LOG_RETENTION="30 days"
```

### Log Output Examples

#### DEV Mode (Colored Console)
```
2025-12-01 10:30:45 | INFO     | omniq.core:123 | Task execution started
└── task_id: abc-123 | operation: process_task | worker: worker-1
```

#### PROD Mode (JSON Structured)
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

### Task and Worker Events

```python
from omniq.logging import (
    log_task_enqueued, log_task_started, 
    log_task_completed, log_task_failed,
    log_worker_started, log_worker_stopped
)

# These are called automatically by the library
# but you can use them for custom logging too
log_task_enqueued("task-123", "my_module.my_function")
log_task_started("task-123", 1)
log_task_completed("task-123", 1)
log_task_failed("task-123", "Error message", will_retry=True)
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
| `OMNIQ_LOG_MODE` | Environment mode (DEV, PROD) | DEV |
| `OMNIQ_LOG_FILE` | Log file path (PROD mode) | logs/omniq.log |
| `OMNIQ_LOG_ROTATION` | Log rotation size | 100 MB |
| `OMNIQ_LOG_RETENTION` | Log retention period | 30 days |

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/integration/  # Integration tests
pytest tests/api/  # API tests

# Run with verbose output
pytest tests/ -v

# Run specific test
pytest tests/integration/test_contract_invariants.py::TestAtomicClaim::test_sqlite_atomic_claim
```

The test suite includes:

- **Integration tests**: Contract invariants, retry logic, concurrency, atomic claims
- **API tests**: Public API functionality
- **Contract tests**: Atomic claim semantics, attempt counting, retry budget enforcement

All tests use pytest fixtures for setup and teardown, ensuring clean test isolation.

## Enhanced Logging API

OmniQ provides enhanced logging using Loguru with a simple 4-function API:

### Core Functions

```python
from omniq.logging import configure, get_logger, task_context, bind_task

# 1. Configure logging with smart defaults
configure(level="INFO", rotation="100 MB", retention="30 days")

# 2. Get logger instance
logger = get_logger()
logger.info("Custom log message")

# 3. Task context with correlation
with task_context("task-123", "process") as task_logger:
    task_logger.info("Processing with correlation")

# 4. Manual context binding
bound_logger = bind_task("task-456", worker="worker-1")
bound_logger.info("Manual context binding")
```

### Legacy Functions (Backward Compatible)

```python
from omniq.logging import (
    log_task_enqueued, log_task_started, 
    log_task_completed, log_task_failed,
    log_worker_started, log_worker_stopped,
    log_storage_error, log_serialization_error
)

# All existing functions work exactly as before
log_task_enqueued("task-123", "my_module.my_function")
```

## API Reference

### Core Classes

- `AsyncOmniQ`: Main async interface for task queue operations
- `AsyncTaskQueue`: Core task queue engine that handles enqueue/dequeue logic, scheduling, and retries
- `AsyncWorkerPool`: Worker pool for concurrent task execution
- `Settings`: Configuration settings for the queue system

### Storage Classes

- `FileStorage`: File-based storage backend
- `SQLiteStorage`: SQLite-based storage backend
- `BaseStorage`: Abstract base class for storage implementations

### Logging Functions

- `configure()`: Configure enhanced logging with smart defaults
- `get_logger()`: Get Loguru logger instance with context binding
- `task_context()`: Context manager for task correlation and timing
- `bind_task()`: Bind correlation ID and additional context to logger
- Legacy functions: `log_task_*()`, `log_worker_*()`, etc. (backward compatible)

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
│   ├── core.py          # Main AsyncOmniQ interface
│   ├── queue.py         # AsyncTaskQueue - Core task queue engine
│   ├── config.py        # Configuration management
│   ├── models.py        # Task and result models
│   ├── logging.py       # Logging configuration
│   ├── serialization.py # Task serialization
│   ├── worker.py        # AsyncWorkerPool implementation
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