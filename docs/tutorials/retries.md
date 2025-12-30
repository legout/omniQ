# Retries and Task Errors

This tutorial explains how OmniQ handles task failures, automatic retries, and how to work with error information. You'll learn about:

- **Automatic retry behavior**: How tasks are retried on failure
- **Retry budget semantics**: `max_retries` and attempt counting
- **Exponential backoff**: Retry delays with jitter
- **TaskError model**: Inspecting error details

## Prerequisites

Complete [async quickstart](quickstart.md) tutorial first.

## Understanding Retry Behavior

When a task fails during execution, OmniQ automatically attempts to retry it based on your retry configuration. This happens automatically - no extra code needed.

### Retry Budget

The retry budget controls how many total executions are allowed:

```python
task_id = await omniq.enqueue(
    my_task,
    data,
    max_retries=3  # Allows 4 total executions
)
```

**Key concept**: `max_retries=3` means the task can execute **4 times total**:
- 1 initial execution
- Up to 3 retries if failed

### Attempt Counting

OmniQ counts attempts each time a task transitions from PENDING to RUNNING:

```python
# Execution flow with max_retries=3:
# 1. Initial: attempts=0 → becomes 1 (PENDING→RUNNING)
#    Fails → retry scheduled
# 2. Retry 1: attempts=1 → becomes 2
#    Fails → retry scheduled
# 3. Retry 2: attempts=2 → becomes 3
#    Fails → retry scheduled
# 4. Retry 3: attempts=3 → becomes 4
#    Fails → no more retries (attempts >= max_retries)
#    Task marked FAILED
```

The retry decision uses: `attempts < max_retries`

## Exponential Backoff with Jitter

OmniQ uses exponential backoff with random jitter to retry tasks:

| Retry | Base Delay | With Jitter (±25%) |
|--------|-------------|---------------------|
| 1      | 1 second    | 0.75 - 1.25 seconds  |
| 2      | 2 seconds    | 1.5 - 2.5 seconds   |
| 3      | 4 seconds    | 3 - 5 seconds       |
| 4      | 8 seconds    | 6 - 10 seconds      |
| 5      | 16 seconds   | 12 - 20 seconds     |
| 6      | 32 seconds   | 24 - 40 seconds     |
| 7+     | 60 seconds   | 45 - 75 seconds     |

**Why jitter?** Random variation prevents "thundering herd" - many tasks retrying simultaneously and overwhelming your system.

## Step 1: Configure Retry Limits

Set `max_retries` when enqueuing tasks:

```python
from omniq import AsyncOmniQ
from omniq.config import Settings

async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Task with 3 retry attempts (4 total executions)
    task_id = await omniq.enqueue(
        process_data,
        data,
        max_retries=3
    )
```

Common retry limits:
- **max_retries=0**: No retries, fail immediately
- **max_retries=3** (default): Balanced retry behavior
- **max_retries=5+**: For unreliable external services

## Step 2: Understand Task Error Metadata

When tasks fail, OmniQ stores error information in the task:

```python
result = await omniq.get_result(task_id)

if isinstance(result, dict):
    error = result.get("error")
    attempts = result.get("attempts")
    status = result.get("status")
```

The error metadata includes:
- `error_type`: Type of error (e.g., "timeout", "network")
- `message`: Human-readable error message
- `retry_count`: How many retries were attempted
- `timestamp`: When the error occurred

## Step 3: Handle Transient vs. Permanent Errors

Design your task functions to handle different error types appropriately:

```python
import requests
from typing import Any

def fetch_data(url: str) -> dict:
    """Fetch data from external API."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        # Transient error - let OmniQ retry
        raise  # Will be retried up to max_retries

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            # Permanent error - don't retry
            raise ValueError(f"Resource not found: {url}")

        # 5xx errors - transient, let it retry
        raise

    except requests.ConnectionError:
        # Network issue - transient, retry
        raise
```

**Transient errors** (retried):
- Network timeouts
- Rate limiting (429 Too Many Requests)
- Temporary service unavailability (503 Service Unavailable)

**Permanent errors** (not retried):
- Invalid input (400 Bad Request)
- Not found (404 Not Found)
- Permission denied (403 Forbidden)

## Step 4: Inspect Failed Tasks

After task execution (successful or failed), inspect the results:

```python
async def main():
    # ... (enqueue task and run workers)

    # Get final result
    result = await omniq.get_result(task_id)

    if result:
        # Extract fields based on format
        if isinstance(result, dict):
            status = result.get("status")
            attempts = result.get("attempts", 0)
            error = result.get("error")
            task_result = result.get("result")
        else:
            status = result.status
            attempts = result.attempts
            error = result.error
            task_result = result.result

        print(f"Task status: {status}")
        print(f"Total attempts: {attempts}")

        if status == "FAILED":
            print(f"Error: {error}")
        else:
            print(f"Result: {task_result}")
```

## Complete Example

Here's a complete working example with a flaky task:

```python
import asyncio
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

class CallTracker:
    """Track how many times a task is called."""
    def __init__(self):
        self.call_count = 0

tracker = CallTracker()

def flaky_task(data: str) -> str:
    """Task that fails twice, then succeeds."""
    tracker.call_count += 1
    attempt = tracker.call_count

    print(f"Attempt {attempt}: processing '{data}'")

    if attempt <= 2:
        # Fail first 2 attempts
        raise RuntimeError(f"Simulated failure (attempt {attempt}/2)")

    # Succeed on 3rd attempt
    return f"Success: {data} (attempt {attempt})"

async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Enqueue task with retry budget
    print("Enqueuing flaky task (max_retries=3)...")
    task_id = await omniq.enqueue(flaky_task, "test-data", max_retries=3)
    print(f"Task ID: {task_id}")
    print()

    # Run workers
    print("Starting workers...")
    workers = omniq.worker(concurrency=1)
    worker_task = asyncio.create_task(workers.start())

    # Let workers process task
    await asyncio.sleep(5)

    # Stop workers
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)

    # Check result
    print()
    print("Checking task result...")
    result = await omniq.get_result(task_id)

    if result:
        if isinstance(result, dict):
            status = result.get("status")
            attempts = result.get("attempts")
            error = result.get("error")
            task_result = result.get("result")
        else:
            status = result.status
            attempts = result.attempts
            error = result.error
            task_result = result.result

        print(f"Final status: {status}")
        print(f"Total attempts: {attempts}")

        if error:
            print(f"Error: {error}")
        if task_result:
            print(f"Result: {task_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

Expected output:
```
Enqueuing flaky task (max_retries=3)...
Task ID: task-xxx

Starting workers...
Attempt 1: processing 'test-data'
Attempt 2: processing 'test-data'
Attempt 3: processing 'test-data'

Checking task result...
Final status: COMPLETED
Total attempts: 3
Result: Success: test-data (attempt 3)
```

## Best Practices

### 1. Use Appropriate Retry Limits

```python
# Network operations - more retries
await omniq.enqueue(call_api, max_retries=5)

# Database operations - fewer retries
await omniq.enqueue(update_record, max_retries=2)

# File operations - minimal retries
await omniq.enqueue(process_file, max_retries=1)
```

### 2. Make Tasks Idempotent

A task should be safe to run multiple times:

```python
def send_email(user_id: int, message: str):
    """Idempotent email sending."""
    # Check if email already sent
    if already_sent(user_id, message):
        return {"status": "already_sent"}

    # Send email
    send(user_id, message)
    mark_sent(user_id, message)

    return {"status": "sent"}
```

### 3. Monitor Retry Patterns

Track which tasks fail frequently:

```python
async def monitor_retries():
    tasks = await omniq.list_tasks()

    for task in tasks:
        attempts = task.get("attempts", 0)
        if attempts > 2:
            print(f"Frequent retries: {task['func_path']} ({attempts} attempts)")
```

## Next Steps

- Learn how to [configure logging](logging.md) to track retry behavior
- Understand [worker configuration](../how-to/run-workers.md) for concurrency
- Read [retry explanation](../explanation/retry_mechanism.md) for deeper details

## Run Example

A complete runnable example is available in the repository:

```bash
cd examples
python 03_retries_and_task_errors.py
```

This example demonstrates retry behavior with a deterministic flaky task.
