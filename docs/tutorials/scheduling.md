# Scheduling with ETA and Interval

This tutorial shows how to schedule tasks for delayed execution and create repeating tasks that run at regular intervals. You'll learn about:

- **ETA (Estimated Time of Arrival)**: Delay task execution to a specific time
- **Interval tasks**: Automatically reschedule tasks after completion
- **Worker polling behavior**: How workers discover and execute scheduled tasks

## Prerequisites

Complete the [async quickstart](quickstart.md) tutorial first.

## What is ETA?

ETA (Estimated Time of Arrival) lets you schedule a task to run at a specific future time. This is useful for:

- Delayed processing (e.g., "run this report tomorrow at 9 AM")
- Staggering task execution to spread load
- Coordinating tasks across multiple systems

## What are Interval Tasks?

Interval tasks automatically reschedule themselves after completion. Each execution creates a **new task** with the same interval setting. Use interval tasks for:

- Periodic maintenance jobs
- Health checks
- Data synchronization
- Regular cleanup operations

## Step 1: Schedule a Task with ETA

Use the `eta` parameter to delay execution:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Schedule task to run 5 minutes from now
    eta_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    task_id = await omniq.enqueue(
        my_task,
        "data",
        eta=eta_time
    )

    print(f"Task scheduled: {task_id}")
    print(f"Will execute at: {eta_time}")

async def my_task(data: str) -> str:
    return f"Processed: {data}"
```

**Important**: Always use timezone-aware datetimes. The example uses `datetime.now(timezone.utc)`.

## Step 2: Create an Interval Task

Use the `interval` parameter for repeating tasks. You can specify intervals in two ways:

### Using timedelta (recommended)

```python
from datetime import timedelta

# Task repeats every 30 minutes
task_id = await omniq.enqueue(
    cleanup_task,
    interval=timedelta(minutes=30)
)
```

### Using integers (milliseconds)

```python
# Task repeats every 500 milliseconds
task_id = await omniq.enqueue(
    heartbeat_task,
    interval=500
)
```

**Note**: Integer values are interpreted as **milliseconds**.

## Step 3: Understanding Interval Task Behavior

Interval tasks create a **new task** after each execution:

```python
async def monitor_task():
    """This will run every 10 seconds."""
    print("Running monitor check...")
    return {"status": "ok", "timestamp": datetime.now()}

# Initial task created
initial_id = await omniq.enqueue(monitor_task, interval=timedelta(seconds=10))

# After first execution:
# - New task created with same interval (10 seconds)
# - New task gets different ID
# - Pattern repeats for each execution
```

This means:
- Each execution is independent
- Failed executions don't stop future executions
- You can cancel interval tasks by deleting pending tasks

## Step 4: Combined ETA and Interval

You can combine ETA with interval for delayed recurring tasks:

```python
# Start tomorrow, repeat every hour
start_time = datetime.now(timezone.utc) + timedelta(days=1)

task_id = await omniq.enqueue(
    daily_report_task,
    interval=timedelta(hours=1),
    eta=start_time
)
```

The task will:
1. Wait until `start_time`
2. Execute the task
3. Reschedule with same `interval` (hourly)

## Step 5: Worker Polling for Scheduled Tasks

Workers automatically poll for tasks that are due for execution:

```python
async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Schedule tasks...
    await omniq.enqueue(my_task, eta=...)
    await omniq.enqueue(cleanup_task, interval=...)

    # Workers automatically discover scheduled tasks
    workers = omniq.worker(concurrency=1, poll_interval=1.0)

    worker_task = asyncio.create_task(workers.start())

    # Workers will:
    # 1. Check for tasks due now (eta <= current time)
    # 2. Check for tasks ready to execute
    # 3. Execute tasks when due

    await asyncio.sleep(30)  # Run for 30 seconds

    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)
```

The `poll_interval` setting controls how frequently workers check for new tasks (default: 1.0 seconds).

## Complete Example

Here's a complete working example:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

def process_item(item_id: str) -> dict:
    """Example task."""
    print(f"Processing item: {item_id}")
    return {"item_id": item_id, "status": "completed"}

async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Schedule delayed task (ETA)
    print("Scheduling delayed task (5 seconds)...")
    eta_task_id = await omniq.enqueue(
        process_item,
        "delayed-item",
        eta=datetime.now(timezone.utc) + timedelta(seconds=5)
    )

    # Schedule interval task (every 2 seconds)
    print("Scheduling interval task (every 2 seconds)...")
    interval_task_id = await omniq.enqueue(
        process_item,
        "interval-item",
        interval=timedelta(seconds=2)
    )

    # Start workers
    print("Starting workers...")
    workers = omniq.worker(concurrency=1)
    worker_task = asyncio.create_task(workers.start())

    # Let tasks run for 10 seconds
    await asyncio.sleep(10)

    # Stop workers
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
```

Expected output:
```
Scheduling delayed task (5 seconds)...
Scheduling interval task (every 2 seconds)...
Starting workers...
Processing item: interval-item      # t=2s
Processing item: interval-item      # t=4s
Processing item: interval-item      # t=6s
Processing item: interval-item      # t=8s
Processing item: delayed-item      # t=5s (original ETA task)
Processing item: interval-item      # t=10s
Done!
```

## Best Practices

### 1. Use Timezone-Aware Datetimes

❌ **Bad** (timezone-naive):
```python
eta = datetime(2025, 1, 1, 12, 0)
```

✅ **Good** (timezone-aware):
```python
eta = datetime.now(timezone.utc) + timedelta(days=1)
```

### 2. Choose Appropriate Intervals

- **Frequent (seconds)**: Health checks, heartbeats
- **Moderate (minutes)**: Data sync, cache invalidation
- **Infrequent (hours/days)**: Reports, cleanup, backups

### 3. Monitor Interval Tasks

Track interval task execution to detect issues:

```python
from omniq.models import TaskStatus

# Check for stuck or failing interval tasks
tasks = await omniq.list_tasks()
interval_tasks = [t for t in tasks if t.get("interval")]

for task in interval_tasks:
    if task["status"] == TaskStatus.FAILED:
        print(f"Failed interval task: {task['id']}")
```

## Next Steps

- Learn about [retry behavior](retries.md) when scheduled tasks fail
- Understand how to [choose a storage backend](../how-to/choose-backend.md)
- Read the [scheduling explanation](../explanation/scheduling.md) for deeper semantics

## Run Example

A complete runnable example is available in the repository:

```bash
cd examples
python 02_scheduling_eta_and_interval.py
```

This example demonstrates ETA tasks and interval tasks with worker polling behavior.
