# Run Workers (Concurrency, Polling, Shutdown)

Learn how to configure and manage OmniQ worker pools for reliable task execution.

## Overview

Worker pools claim and execute tasks from the queue. Configure them for your workload with concurrency, polling, and graceful shutdown.

## Concurrency

Concurrency controls how many tasks execute simultaneously:

```python
from omniq import AsyncOmniQ

omniq = AsyncOmniQ(settings)

# Single worker (sequential execution)
workers = omniq.worker(concurrency=1)

# Multiple workers (parallel execution)
workers = omniq.worker(concurrency=4)
```

### Choosing Concurrency Level

| Concurrency | Use Case |
|-------------|-----------|
| 1 | Sequential tasks, resource-heavy operations |
| 2-4 | General purpose workloads |
| 4-8 | I/O-bound tasks (network calls) |
| 8+ | Many lightweight, independent tasks |

**Rule of thumb**: Match concurrency to available CPU cores for CPU-bound tasks. Use higher for I/O-bound tasks.

## Polling Interval

Polling controls how frequently workers check for new tasks:

```python
# Check every 1 second (default)
workers = omniq.worker(concurrency=2, poll_interval=1.0)

# Check every 0.5 seconds (faster task discovery)
workers = omniq.worker(concurrency=2, poll_interval=0.5)

# Check every 5 seconds (lower overhead)
workers = omniq.worker(concurrency=2, poll_interval=5.0)
```

### Trade-offs

| Polling | Pros | Cons |
|----------|--------|------|
| Fast (0.5s) | Low latency | Higher CPU usage |
| Default (1.0s) | Balanced | Good for most cases |
| Slow (5.0s+) | Low overhead | Delayed task start |

**Recommendation**: Start with default (1.0s). Adjust based on latency vs. overhead needs.

## Starting Workers

### Async Workers

```python
import asyncio
from omniq import AsyncOmniQ

async def main():
    omniq = AsyncOmniQ(settings)

    # Create workers
    workers = omniq.worker(concurrency=2, poll_interval=1.0)

    # Start in background
    worker_task = asyncio.create_task(workers.start())

    # Workers run until stopped
    print("Workers running...")
    await asyncio.sleep(30)

    # Stop gracefully
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)
```

### Sync Workers

```python
import threading
from omniq import OmniQ

def main():
    omniq = OmniQ(settings)

    # Create workers
    workers = omniq.worker(concurrency=2)

    # Start in background thread
    worker_thread = threading.Thread(target=workers.start, daemon=True)
    worker_thread.start()

    # Workers run until stopped
    print("Workers running...")
    import time
    time.sleep(30)

    # Stop gracefully
    workers.stop(timeout=5.0)
    worker_thread.join(timeout=3.0)
```

## Graceful Shutdown

Graceful shutdown ensures in-flight tasks complete before exiting:

```python
async def run_with_shutdown():
    omniq = AsyncOmniQ(settings)
    workers = omniq.worker(concurrency=4)

    worker_task = asyncio.create_task(workers.start())

    # Handle shutdown signal
    try:
        await asyncio.Event().wait()  # Run forever
    except KeyboardInterrupt:
        print("\nShutdown requested...")

    # Stop workers (graceful)
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=5.0)

    print("Workers stopped gracefully")
```

### Shutdown Behavior

When `workers.stop()` is called:
1. No new tasks are claimed
2. In-flight tasks complete (up to timeout)
3. Running tasks finish or timeout
4. Worker pool exits

### Timeout Configuration

```python
# Wait up to 10 seconds for in-flight tasks
await workers.stop()
await asyncio.wait_for(worker_task, timeout=10.0)

# Or use workers.stop() with timeout
workers.stop(timeout=10.0)
```

## Worker Lifecycle

### Complete Example

```python
import asyncio
import signal
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

def process_task(data: str) -> dict:
    """Example task function."""
    print(f"Processing: {data}")
    return {"status": "completed", "data": data}

async def main():
    # Initialize OmniQ
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Create worker pool
    workers = omniq.worker(concurrency=4, poll_interval=1.0)

    # Setup shutdown handling
    shutdown_event = asyncio.Event()

    def signal_handler():
        print("\nShutdown signal received...")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Enqueue some work
    task_ids = []
    for i in range(10):
        task_id = await omniq.enqueue(process_task, f"item-{i}")
        task_ids.append(task_id)

    print(f"Enqueued {len(task_ids)} tasks")

    # Start workers
    worker_task = asyncio.create_task(workers.start())
    print("Workers started (concurrency=4)")

    # Run until shutdown
    await shutdown_event.wait()

    # Graceful shutdown
    print("\nStopping workers...")
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=5.0)

    print("Workers stopped")

    # Check results
    results = []
    for task_id in task_ids:
        result = await omniq.get_result(task_id)
        if result:
            results.append(result)

    print(f"\nCompleted {len(results)} tasks")

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### 1. Use Appropriate Concurrency

```python
# CPU-bound tasks (video encoding)
workers = omniq.worker(concurrency=2)

# I/O-bound tasks (HTTP requests)
workers = omniq.worker(concurrency=8)
```

### 2. Monitor Worker Health

```python
from omniq.models import TaskStatus

async def monitor_workers():
    # Check for stuck workers
    tasks = await omniq.list_tasks()
    running_tasks = [t for t in tasks if t["status"] == TaskStatus.RUNNING]

    if len(running_tasks) > workers.concurrency:
        print(f"Warning: More running tasks ({len(running_tasks)}) than workers ({workers.concurrency})")
```

### 3. Always Use Graceful Shutdown

```python
# Bad: abrupt termination
import sys
sys.exit(1)

# Good: graceful shutdown
await workers.stop()
```

### 4. Test Shutdown Path

```python
# Test shutdown in development
await workers.stop()

# If this hangs, check:
# 1. Task timeout settings
# 2. Long-running tasks
# 3. Worker shutdown timeout
```

### 5. Log Worker Events

```python
from omniq.logging import log_worker_started, log_worker_stopped

log_worker_started(concurrency=4, poll_interval=1.0)
# Workers start...

log_worker_stopped(tasks_processed=42, uptime=300)
# Workers stopped
```

## Common Issues

### Workers Not Starting

```python
# Check that omniq is initialized
workers = omniq.worker(concurrency=2)
# omniq must be AsyncOmniQ instance

# Ensure async context
async def main():
    workers = omniq.worker(concurrency=2)
    await workers.start()
```

### Tasks Not Processing

```python
from omniq.models import TaskStatus

# Check poll_interval (too long?)
workers = omniq.worker(concurrency=2, poll_interval=0.5)

# Check queue has tasks
tasks = await omniq.list_tasks()
pending = [t for t in tasks if t["status"] == TaskStatus.PENDING]
print(f"Pending tasks: {len(pending)}")
```

### Shutdown Hanging

```python
from omniq.models import TaskStatus

# Increase timeout for long tasks
await workers.stop()
await asyncio.wait_for(worker_task, timeout=30.0)

# Check for stuck tasks
tasks = await omniq.list_tasks()
running = [t for t in tasks if t["status"] == TaskStatus.RUNNING]
print(f"Still running: {len(running)}")
```

## Next Steps

- Learn how to [configure retries](configure-retries.md) for reliability
- Understand [task timeout behavior](configure-retries.md)
- Read [worker API reference](../reference/api/worker.md)

## Summary

- **Concurrency**: Control parallelism based on workload type
- **Polling**: Balance latency vs. overhead (default: 1s)
- **Shutdown**: Always use graceful shutdown with timeout
- **Monitoring**: Track worker health and task processing
- **Best practice**: Test shutdown path in development

Configure workers for your workload, use graceful shutdown, and monitor task processing for reliable operation.
