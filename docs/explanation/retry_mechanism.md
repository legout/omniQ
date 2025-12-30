# Retry Mechanism Documentation

## Overview

OmniQ provides a robust retry mechanism that automatically handles task failures with exponential backoff and jitter. This feature is built into the `AsyncTaskQueue` and works seamlessly with all storage backends.

## Key Features

- **Automatic Retry**: Tasks are automatically retried on failure up to `max_retries` times
- **Exponential Backoff**: Retry delays increase exponentially (1s, 2s, 4s, 8s, 16s, 32s, 60s max)
- **Jitter**: Random variation (±25%) prevents thundering herd problems
- **Storage Integration**: Uses storage backend's `get_task()` and `reschedule()` methods
- **Interval Task Support**: Works correctly with recurring/interval tasks

## How It Works

### 1. Task Failure Detection

When a task execution fails, the worker calls `AsyncTaskQueue.fail_task()`:

```python
await queue.fail_task(
    task_id="task-123",
    error="Connection timeout",
    exception_type="TimeoutError",
    traceback="Full traceback here..."
)
```

### 2. Retry Logic

The queue determines if a task should be retried:

```python
def _should_retry(self, task: Task, attempts: int) -> bool:
    max_retries = task.get("max_retries", 3)
    return attempts < max_retries
```

### 3. Delay Calculation

Retry delay uses exponential backoff with jitter:

```python
def _calculate_retry_delay(self, retry_count: int) -> float:
    # Base delay: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
    base_delay = min(2 ** (retry_count - 1), 60)
    
    # Add jitter: ±25% random variation
    jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
    delay = base_delay * jitter_factor
    
    return delay
```

### 4. Task Rescheduling

The task is rescheduled using the storage backend:

```python
retry_eta = datetime.now(timezone.utc) + timedelta(seconds=delay)
await self.storage.reschedule(task_id, retry_eta)
await self.storage.mark_failed(task_id, error, will_retry=True)
```

## Configuration

### Max Retries

Set the maximum number of retry attempts when enqueuing:

```python
task_id = await queue.enqueue(
    func_path="my_module.flaky_function",
    args=[],
    kwargs={},
    max_retries=5,  # Retry up to 5 times (default: 3)
    timeout=30
)
```

### Retry Behavior

- **Default**: 3 retry attempts (4 total attempts including initial)
- **No Retries**: Set `max_retries=0`
- **Unlimited**: Set `max_retries=None` (not recommended for production)

## Storage Backend Requirements

Storage backends must implement two methods for retry support:

### `get_task(task_id: str) -> Optional[Task]`

Retrieves a task by ID for retry logic:

```python
async def get_task(self, task_id: str) -> Optional[Task]:
    """Retrieve a task by ID."""
    # Implementation varies by backend
    pass
```

### `reschedule(task_id: str, new_eta: datetime) -> None`

Updates a task's ETA for retry execution:

```python
async def reschedule(self, task_id: str, new_eta: datetime) -> None:
    """Update task ETA for retry execution."""
    # Implementation varies by backend
    pass
```

## Usage Examples

### Basic Retry

```python
from omniq.queue import AsyncTaskQueue
from omniq.storage.sqlite import SQLiteStorage

storage = SQLiteStorage("tasks.db")
queue = AsyncTaskQueue(storage)

# Enqueue task with retry configuration
task_id = await queue.enqueue(
    func_path="my_module.process_data",
    args=[data],
    kwargs={"timeout": 30},
    max_retries=3,
    timeout=60
)

# Worker execution (simplified)
try:
    task = await queue.dequeue()
    if task:
        result = await execute_task(task)
        await queue.complete_task(task["id"], result, task=task)
except Exception as e:
    await queue.fail_task(task["id"], str(e), task=task)
```

### Custom Retry Logic

```python
# Override retry behavior if needed
class CustomQueue(AsyncTaskQueue):
    def _should_retry(self, task: Task, attempts: int) -> bool:
        # Custom logic: don't retry certain errors
        if "fatal" in task.get("last_error", ""):
            return False
        return super()._should_retry(task, attempts)
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        # Custom delay calculation
        return min(retry_count * 5, 300)  # 5s, 10s, 15s, max 5min
```

### Monitoring Retries

```python
# Check task retry status
task = await queue.get_task(task_id)
attempts = task.get("attempts", 0)
max_retries = task.get("max_retries", 3)

if attempts > 0:
    print(f"Task has been retried {attempts} times")
    print(f"Max retries: {max_retries}")
    print(f"Remaining retries: {max_retries - attempts}")
```

## Best Practices

### 1. Idempotent Tasks

Design tasks to be idempotent (safe to retry):

```python
async def process_payment(payment_id: str):
    # Check if already processed
    if await is_payment_processed(payment_id):
        return {"status": "already_processed"}
    
    # Process payment
    result = await charge_payment(payment_id)
    await mark_payment_processed(payment_id)
    return result
```

### 2. Appropriate Retry Limits

Set retry limits based on task characteristics:

```python
# Network operations - more retries
await queue.enqueue(
    func_path="api_client.call_endpoint",
    max_retries=5
)

# Database operations - fewer retries
await queue.enqueue(
    func_path="database.update_record",
    max_retries=2
)

# File operations - minimal retries
await queue.enqueue(
    func_path="file_processor.process_file",
    max_retries=1
)
```

### 3. Error Classification

Handle different error types appropriately:

```python
try:
    result = await execute_task(task)
except TemporaryError as e:
    # Retry these
    await queue.fail_task(task["id"], str(e), task=task)
except PermanentError as e:
    # Don't retry these
    await queue.fail_task(task["id"], str(e), task=task)
    # Or mark as failed without retry
    await queue.storage.mark_failed(task["id"], str(e), will_retry=False)
```

### 4. Monitoring and Alerting

Monitor retry patterns for issues:

```python
# Track retry metrics
retry_counts = {}
failed_tasks = []

async def monitor_retries():
    tasks = await get_all_tasks()
    for task in tasks:
        attempts = task.get("attempts", 0)
        if attempts > 0:
            retry_counts[task["func_path"]] = retry_counts.get(task["func_path"], 0) + 1
        
        if task["status"] == TaskStatus.FAILED:
            failed_tasks.append(task["id"])
    
    # Alert on high retry rates
    for func_path, count in retry_counts.items():
        if count > 10:  # Threshold
            send_alert(f"High retry rate for {func_path}: {count}")
```

## Troubleshooting

### Common Issues

1. **Tasks Not Retrying**
   - Check `max_retries` configuration
   - Verify storage backend implements `get_task()` and `reschedule()`
   - Check error handling in worker code

2. **Too Many Retries**
   - Review task idempotency
   - Check for permanent errors being retried
   - Adjust `max_retries` limits

3. **Retry Delays Too Long**
   - Monitor backoff calculation
   - Consider custom delay logic
   - Check for stuck tasks

### Debug Information

Enable debug logging to trace retry behavior:

```python
import logging
logging.getLogger("omniq").setLevel(logging.DEBUG)

# Look for these log messages:
# "Task retry scheduled: task-123 (attempt 2) in 4.0s"
# "Task failed permanently: task-123 after 4 attempts"
```

## Integration with Interval Tasks

Retry mechanism works seamlessly with interval tasks:

```python
# Interval task with retry support
task_id = await queue.enqueue(
    func_path="monitor.check_system",
    args=[],
    kwargs={},
    interval=300,  # Every 5 minutes
    max_retries=3   # Retry failed checks
)

# If a check fails, it will be retried
# If all retries fail, the next scheduled execution still happens
```

This ensures that temporary failures in interval tasks don't disrupt the overall schedule.