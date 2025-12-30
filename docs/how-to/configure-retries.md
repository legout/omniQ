# Configure Retries and Timeouts Safely

Learn how to configure retry limits, timeouts, and design idempotent tasks for reliable task execution.

## Overview

OmniQ provides automatic retries with exponential backoff. Configure retry limits and timeouts based on task characteristics and ensure tasks are idempotent.

## Configure Retry Limits

Set `max_retries` when enqueuing tasks:

```python
# No retries
task_id = await omniq.enqueue(my_task, data, max_retries=0)

# Default retry behavior (3 retries = 4 total executions)
task_id = await omniq.enqueue(my_task, data, max_retries=3)

# High retry count for unreliable services
task_id = await omniq.enqueue(call_api, url, max_retries=5)
```

### Retry Budget Model

```python
# max_retries=3 allows 4 total executions:
# 1. Initial execution (attempts=0 → 1)
# 2. Retry 1 (attempts=1 → 2)
# 3. Retry 2 (attempts=2 → 3)
# 4. Retry 3 (attempts=3 → 4)
# 5. If still failed → task marked FAILED
```

**Key**: Predicate is `attempts < max_retries`, not `attempts <= max_retries`.

## Configure Task Timeout

Set `timeout` to prevent tasks from running forever:

```python
# 30 second timeout
task_id = await omniq.enqueue(
    process_file,
    filepath,
    max_retries=3,
    timeout=30.0
)
```

### Timeout Behavior

- Task is marked as FAILED if timeout exceeded
- No automatic retry on timeout (task failed)
- Worker claims next task

### Choosing Timeout Values

```python
# Quick operations (database updates)
await omniq.enqueue(update_record, data, timeout=5.0)

# Medium operations (HTTP requests)
await omniq.enqueue(fetch_data, url, timeout=30.0)

# Long operations (file processing)
await omniq.enqueue(process_video, file, timeout=300.0)
```

## Design Idempotent Tasks

Idempotent tasks produce the same result regardless of how many times they execute.

### Why Idempotency Matters

With retries, a task might execute multiple times:

```python
# Non-idempotent (bad)
def charge_credit_card(user_id: int, amount: float):
    """Bad: charges every time called."""
    bank.charge(user_id, amount)
    return {"status": "charged"}

# Idempotent (good)
def charge_credit_card(user_id: int, amount: float):
    """Good: checks if already charged."""
    if already_charged(user_id, amount):
        return {"status": "already_charged"}

    bank.charge(user_id, amount)
    mark_charged(user_id, amount)
    return {"status": "charged"}
```

### Idempotency Patterns

#### 1. Check-Before-Execute

```python
def send_notification(user_id: int, message: str):
    """Check if notification already sent."""
    if notification_sent(user_id, message):
        return {"status": "duplicate"}

    send(user_id, message)
    mark_notification_sent(user_id, message)
    return {"status": "sent"}
```

#### 2. Use Unique IDs

```python
def create_order(user_id: int, items: list):
    """Generate unique order ID."""
    order_id = generate_unique_id()

    if order_exists(order_id):
        return {"status": "exists", "order_id": order_id}

    # Create order
    create_order_in_db(order_id, user_id, items)
    return {"status": "created", "order_id": order_id}
```

#### 3. Use Idempotent Operations

```python
def update_user_profile(user_id: int, data: dict):
    """Use idempotent database operations."""
    # SQL UPDATE is idempotent (same result on rerun)
    query = "UPDATE users SET data=? WHERE id=?"
    db.execute(query, (json.dumps(data), user_id))

    return {"status": "updated"}
```

## Configure Retries by Error Type

Design tasks to handle transient vs. permanent errors:

```python
import requests
from typing import Any

def fetch_resource(url: str) -> dict:
    """Fetch with transient error detection."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        # Transient: retry
        raise

    except requests.ConnectionError:
        # Transient: retry
        raise

    except requests.HTTPError as e:
        if e.response.status_code in (429, 502, 503, 504):
            # Transient: retry
            raise

        # Permanent: don't retry
        if e.response.status_code == 404:
            raise ValueError(f"Not found: {url}")

        # Permanent: don't retry
        if e.response.status_code == 403:
            raise PermissionError(f"Access denied: {url}")

        # Unknown: let it retry
        raise
```

### Transient Errors (Retry)

- Network timeouts
- Connection errors
- Rate limiting (429 Too Many Requests)
- Service unavailable (503 Service Unavailable)
- Gateway timeout (504 Gateway Timeout)

### Permanent Errors (Don't Retry)

- Invalid input (400 Bad Request)
- Not found (404 Not Found)
- Permission denied (403 Forbidden)
- Authentication failure (401 Unauthorized)

## Best Practices

### 1. Match Retries to Task Type

```python
# External API calls: high retries
await omniq.enqueue(call_api, endpoint, max_retries=5, timeout=60)

# Database operations: low retries
await omniq.enqueue(update_db, data, max_retries=2, timeout=10)

# File operations: minimal retries
await omniq.enqueue(move_file, src, dst, max_retries=1, timeout=30)
```

### 2. Test Idempotency

```python
# Test that task produces same result on rerun
result1 = my_task(data)
result2 = my_task(data)

assert result1 == result2, "Task not idempotent!"
```

### 3. Monitor Retry Patterns

```python
from omniq.models import TaskStatus

async def monitor_retries():
    tasks = await omniq.list_tasks()

    for task in tasks:
        attempts = task.get("attempts", 0)

        if attempts > 3:
            print(f"High retry count: {task['func_path']} ({attempts} attempts)")

        if task["status"] == TaskStatus.FAILED:
            print(f"Failed task: {task['id']}")
```

### 4. Use Timeouts Appropriately

```python
# Too short: tasks timeout unnecessarily
await omniq.enqueue(process_data, data, timeout=1.0)  # Bad

# Appropriate: realistic timeout
await omniq.enqueue(process_data, data, timeout=30.0)  # Good
```

### 5. Document Retry Behavior

```python
def send_email(to: str, subject: str, body: str):
    """Send email (idempotent).

    Checks for duplicate messages using Message-ID header.
    Retries on timeout/connection errors.
    """
    message_id = generate_message_id(to, subject)

    if message_exists(message_id):
        return {"status": "duplicate", "message_id": message_id}

    send(to, subject, body, message_id)
    mark_sent(message_id)
    return {"status": "sent", "message_id": message_id}
```

## Example: Reliable Task

```python
import requests
from typing import Any

class TaskIdTracker:
    """Track task IDs for idempotency."""
    _seen_ids = set()

    @classmethod
    def seen(cls, task_id: str) -> bool:
        return task_id in cls._seen_ids

    @classmethod
    def mark(cls, task_id: str):
        cls._seen_ids.add(task_id)

def reliable_task(operation: str, data: dict) -> dict:
    """Reliable task with idempotency and error handling."""
    task_id = data.get("id", "unknown")

    # Check idempotency
    if TaskIdTracker.seen(task_id):
        print(f"Duplicate task: {task_id}")
        return {"status": "duplicate", "task_id": task_id}

    try:
        if operation == "fetch":
            result = fetch_data(data["url"])
        elif operation == "process":
            result = process_data(data["content"])
        else:
            raise ValueError(f"Unknown operation: {operation}")

        TaskIdTracker.mark(task_id)
        return {"status": "completed", "task_id": task_id, "result": result}

    except (requests.Timeout, requests.ConnectionError) as e:
        # Transient: retry
        print(f"Transient error for {task_id}: {e}")
        raise

    except ValueError as e:
        # Permanent: don't retry
        print(f"Permanent error for {task_id}: {e}")
        raise

async def main():
    from pathlib import Path
    from omniq import AsyncOmniQ
    from omniq.config import Settings

    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Enqueue with retry configuration
    task_id = await omniq.enqueue(
        reliable_task,
        {"operation": "fetch", "id": "task-123", "url": "https://api.example.com/data"},
        max_retries=3,
        timeout=30.0
    )

    print(f"Enqueued task: {task_id}")

    # Process with workers
    workers = omniq.worker(concurrency=1)
    worker_task = asyncio.create_task(workers.start())

    await asyncio.sleep(10)
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)

    result = await omniq.get_result(task_id)
    print(f"Result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Next Steps

- Learn how to [inspect task errors](inspect-errors.md) in detail
- Read [retry explanation](../explanation/retry_mechanism.md) for deeper understanding
- See [TaskError API reference](../reference/api/models.md)

## Summary

- **Retries**: Configure based on task reliability (network ops: high, DB ops: low)
- **Timeouts**: Prevent hanging tasks (realistic values based on workload)
- **Idempotency**: Design tasks to handle multiple executions safely
- **Error types**: Distinguish transient (retry) from permanent (fail fast)
- **Best practice**: Test idempotency and monitor retry patterns

Configure appropriate retry limits and timeouts, design idempotent tasks, and distinguish between transient and permanent errors for reliable task execution.
