# Logging, Sync API, and Environment Configuration

This tutorial covers using OmniQ in synchronous code, configuring via environment variables, and setting up enhanced logging with correlation tracking. You'll learn about:

- **Sync façade**: Using `OmniQ` in synchronous code
- **Environment configuration**: Setting up via `Settings.from_env()`
- **Enhanced logging**: Loguru-based logging with task correlation
- **Task correlation**: Binding context to log messages

## Prerequisites

Complete [async quickstart](quickstart.md) tutorial first.

## Why Use the Sync API?

While `AsyncOmniQ` is recommended for most applications, `OmniQ` (sync) is useful when:

- Working with synchronous frameworks (e.g., Flask, Django without async)
- Migrating from sync task queue libraries
- Writing scripts that don't use asyncio
- You prefer simpler synchronous code

## Step 1: Configure via Environment Variables

Use environment variables to configure OmniQ without hardcoding values:

```python
import os
from omniq import OmniQ
from omniq.config import Settings

# Set environment variables
os.environ["OMNIQ_BACKEND"] = "file"
os.environ["OMNIQ_BASE_DIR"] = "./omniq_data"
os.environ["OMNIQ_SERIALIZER"] = "json"

# Initialize from environment
omniq = OmniQ.from_env()
```

Available environment variables:

| Variable | Description | Example |
|-----------|-------------|----------|
| `OMNIQ_BACKEND` | Storage backend | `file` or `sqlite` |
| `OMNIQ_BASE_DIR` | Directory for storage | `/var/lib/omniq` |
| `OMNIQ_SERIALIZER` | Serialization format | `json` or `pickle` |
| `OMNIQ_DB_PATH` | SQLite database path (sqlite backend) | `./tasks.db` |

### Environment Variable Priority

Environment variables override defaults but can be combined:

```python
# Mix environment and code
os.environ["OMNIQ_BACKEND"] = "sqlite"

settings = Settings(
    backend=None,  # Uses OMNIQ_BACKEND
    serializer="json"  # Explicitly set
)

omniq = OmniQ(settings)
```

## Step 2: Configure Enhanced Logging

OmniQ uses Loguru for enhanced logging with correlation IDs:

```python
from omniq.logging import configure, get_logger

# Basic configuration
configure(level="INFO")

# Get logger instance
logger = get_logger()
logger.info("Application started")
logger.debug("Debug information")
logger.error("Something went wrong")
```

### Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error conditions
- `CRITICAL`: Critical failures

## Step 3: Task Correlation with Context Binding

Bind task-related context to log messages for traceability:

```python
from omniq.logging import bind_task

# Create logger with task context
logger = bind_task(
    task_id="task-123",
    operation="enqueue",
    worker="worker-1"
)

# All logs include correlation context
logger.info("Task enqueued successfully")
# Output: 2025-12-01 10:30:45 | INFO | ... | Task enqueued successfully
#         └── task_id: task-123 | operation: enqueue | worker: worker-1
```

### Context Manager for Task Execution

Use `task_context()` for automatic correlation:

```python
from omniq.logging import task_context

async def process_with_logging(task_id: str, data: str):
    with task_context(task_id, "process") as logger:
        logger.info(f"Processing: {data}")

        # Simulate work
        await asyncio.sleep(0.1)

        logger.info("Processing complete")
        return {"status": "success"}
```

The context manager automatically:
- Adds `task_id` to all logs
- Tracks execution timing
- Handles errors with proper logging

## Step 4: Using the Sync API

The `OmniQ` class provides the same interface as `AsyncOmniQ` but with synchronous methods:

```python
from omniq import OmniQ
from omniq.config import Settings

# Initialize sync façade
settings = Settings(backend="file", base_dir="./omniq_data")
omniq = OmniQ(settings)

# Enqueue tasks (sync)
task_id = omniq.enqueue(process_data, "data-1")

# Get results (sync)
result = omniq.get_result(task_id)

# Create workers (sync)
workers = omniq.worker(concurrency=2)
workers.start()  # Runs in background thread

# Stop workers
workers.stop(timeout=5.0)
```

### Sync vs. Async API Comparison

| Operation | Async API | Sync API |
|-----------|-----------|-----------|
| Enqueue task | `await omniq.enqueue()` | `omniq.enqueue()` |
| Get result | `await omniq.get_result()` | `omniq.get_result()` |
| Create worker | `omniq.worker()` | `omniq.worker()` |
| Start worker | `await workers.start()` | `workers.start()` (thread) |
| Stop worker | `await workers.stop()` | `workers.stop()` |

## Step 5: Configure Logging for DEV vs. PROD

Use environment variables to control logging behavior:

### Development Mode (DEV)

```python
import os

os.environ["OMNIQ_LOG_MODE"] = "DEV"
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"

configure()  # Reads OMNIQ_LOG_* from environment
```

DEV mode features:
- Colored console output
- Detailed formatting
- No file output
- Human-readable timestamps

### Production Mode (PROD)

```python
import os

os.environ["OMNIQ_LOG_MODE"] = "PROD"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
os.environ["OMNIQ_LOG_FILE"] = "/var/log/omniq/app.log"
os.environ["OMNIQ_LOG_ROTATION"] = "100 MB"
os.environ["OMNIQ_LOG_RETENTION"] = "30 days"

configure()  # Configures for production
```

PROD mode features:
- JSON structured output
- File-based logging
- Automatic log rotation
- Machine-parseable format

### All Environment Variables for Logging

| Variable | Description | Default |
|-----------|-------------|----------|
| `OMNIQ_LOG_MODE` | Environment mode | `DEV` |
| `OMNIQ_LOG_LEVEL` | Log level | `INFO` |
| `OMNIQ_LOG_FILE` | Log file path (PROD) | `logs/omniq.log` |
| `OMNIQ_LOG_ROTATION` | Rotation size | `100 MB` |
| `OMNIQ_LOG_RETENTION` | Retention period | `30 days` |

## Complete Example

Here's a complete example using sync API, environment config, and logging:

```python
import os
from pathlib import Path
from omniq import OmniQ
from omniq.logging import configure, bind_task

# Configure via environment
os.environ["OMNIQ_BACKEND"] = "file"
os.environ["OMNIQ_BASE_DIR"] = "./omniq_data"
os.environ["OMNIQ_LOG_MODE"] = "DEV"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"

# Initialize from environment
configure(level="INFO")
omniq = OmniQ.from_env()

print("Initialized OmniQ from environment")

# Use logging with task correlation
logger = bind_task("main", operation="enqueue")
logger.info("Enqueuing tasks...")

# Define task
def process_item(item_id: int, data: str) -> dict:
    """Simple processing task."""
    print(f"Processing item {item_id}: {data}")
    return {"item_id": item_id, "status": "processed", "data": data}

# Enqueue tasks (sync)
task1_id = omniq.enqueue(process_item, 1, "data-1")
task2_id = omniq.enqueue(process_item, 2, "data-2")

print(f"Enqueued tasks: {task1_id}, {task2_id}")

# Create and run sync worker pool
logger = bind_task("worker", operation="execute")
logger.info("Starting worker pool...")

workers = omniq.worker(concurrency=2)

# Start worker in separate thread
import threading

worker_thread = threading.Thread(target=workers.start, daemon=True)
worker_thread.start()

# Wait for tasks to complete
import time

time.sleep(2)

# Stop workers
workers.stop(timeout=2.0)
worker_thread.join(timeout=3.0)

logger.info("Workers stopped")

# Get results with correlated logging
logger = bind_task("results", operation="retrieve")
logger.info("Retrieving results...")

result1 = omniq.get_result(task1_id)
result2 = omniq.get_result(task2_id)

print("\nResults:")
if result1:
    print(f"  Task 1: {result1}")
if result2:
    print(f"  Task 2: {result2}")

print("\nDone!")
```

Expected output (with correlation context in logs):
```
Initialized OmniQ from environment
Enqueued tasks: task-xxx, task-yyy

[INFO] Task enqueued successfully
  └── task_id: main | operation: enqueue

[INFO] Worker pool started
  └── task_id: worker | operation: execute

Processing item 1: data-1
Processing item 2: data-2

[INFO] Workers stopped
  └── task_id: worker | operation: execute

[INFO] Retrieving results...
  └── task_id: results | operation: retrieve

Results:
  Task 1: {'item_id': 1, 'status': 'processed', 'data': 'data-1'}
  Task 2: {'item_id': 2, 'status': 'processed', 'data': 'data-2'}

Done!
```

## Best Practices

### 1. Use Environment for Deployment

❌ **Bad** (hardcoded):
```python
settings = Settings(backend="file", base_dir="/var/lib/omniq")
```

✅ **Good** (environment-based):
```python
omniq = OmniQ.from_env()  # Reads OMNIQ_* variables
```

### 2. Correlate All Logs

❌ **Bad** (no context):
```python
logger.info("Task failed")
```

✅ **Good** (with context):
```python
logger = bind_task(task_id="task-123", operation="execute")
logger.info("Task failed")
```

### 3. Choose Appropriate Log Levels

```python
# Development: detailed logging
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"

# Production: essential logging only
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
```

### 4. Use Structured Logging in Production

```python
# Production environments benefit from JSON output
os.environ["OMNIQ_LOG_MODE"] = "PROD"

# Enables log aggregation and analysis tools
```

## Next Steps

- Learn how to [choose a storage backend](../how-to/choose-backend.md)
- Understand [retry behavior](retries.md) with error handling
- Read [logging reference](../reference/api/logging.md) for all logging functions

## Run Example

A complete runnable example is available in the repository:

```bash
cd examples
python 04_sync_api_logging_and_env.py
```

This example demonstrates sync API usage, environment configuration, and logging with task correlation.
