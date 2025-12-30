# Inspect Task Results and Errors

Learn how to retrieve task results, inspect error information, and handle task metadata.

## Overview

OmniQ stores task results and errors after execution. Use `get_result()` to retrieve them and inspect metadata for debugging and monitoring.

## Retrieve Task Results

Get the final result of a task:

```python
from omniq import AsyncOmniQ

omniq = AsyncOmniQ(settings)
task_id = await omniq.enqueue(my_task, data)

# Get result (blocking)
result = await omniq.get_result(task_id, wait=True, timeout=30.0)
```

### Non-Blocking Retrieval

```python
# Check if result available (non-blocking)
result = await omniq.get_result(task_id)

if result is None:
    print("Task not complete yet")
else:
    print(f"Result: {result}")
```

### Blocking Retrieval with Timeout

```python
# Wait up to 30 seconds for completion
result = await omniq.get_result(task_id, wait=True, timeout=30.0)

if result is None:
    print("Task did not complete within timeout")
else:
    print(f"Result: {result}")
```

## Result Structure

Results can be different formats depending on task status:

### Successful Task

```python
{
    "id": "task-abc123",
    "status": "COMPLETED",
    "result": "Task result value",
    "attempts": 1,
    "enqueued_at": "2025-12-01T10:00:00Z",
    "completed_at": "2025-12-01T10:00:02Z",
    "error": null
}
```

### Failed Task

```python
{
    "id": "task-def456",
    "status": "FAILED",
    "result": null,
    "attempts": 3,
    "enqueued_at": "2025-12-01T10:00:00Z",
    "failed_at": "2025-12-01T10:00:05Z",
    "error": {
        "error_type": "runtime",
        "message": "Connection timeout",
        "traceback": "Traceback...",
        "retry_count": 2,
        "timestamp": "2025-12-01T10:00:05Z"
    }
}
```

### Running Task

```python
{
    "id": "task-ghi789",
    "status": "RUNNING",
    "result": null,
    "attempts": 1,
    "enqueued_at": "2025-12-01T10:00:00Z",
    "started_at": "2025-12-01T10:00:01Z",
    "error": null
}
```

## Inspect Task Metadata

Access task metadata fields:

```python
result = await omniq.get_result(task_id)

if result:
    # Handle dict format
    if isinstance(result, dict):
        task_id = result.get("id")
        status = result.get("status")
        task_result = result.get("result")
        attempts = result.get("attempts", 0)
        error = result.get("error")
    else:
        # Handle object format (if using sync API)
        task_id = result.id
        status = result.status
        task_result = result.result
        attempts = result.attempts
        error = result.error

    print(f"Task ID: {task_id}")
    print(f"Status: {status}")
    print(f"Attempts: {attempts}")

    if status == "COMPLETED":
        print(f"Result: {task_result}")
    elif status == "FAILED":
        print(f"Error: {error}")
```

## Error Metadata

When tasks fail, error metadata provides debugging information:

```python
result = await omniq.get_result(task_id)

if result and result.get("error"):
    error = result["error"]

    # Error type classification
    error_type = error.get("error_type")
    print(f"Error type: {error_type}")

    # Human-readable message
    message = error.get("message")
    print(f"Message: {message}")

    # Retry information
    retry_count = error.get("retry_count", 0)
    print(f"Retries attempted: {retry_count}")

    # Full traceback (if available)
    traceback = error.get("traceback")
    if traceback:
        print(f"Traceback:\n{traceback}")
```

### Error Types

Common error types you'll encounter:

- `runtime`: Python exception during task execution
- `timeout`: Task exceeded configured timeout
- `serialization`: Failed to serialize/deserialize task arguments
- `storage`: Storage backend operation failed

## List and Filter Tasks

Retrieve multiple tasks and filter by status:

```python
from omniq.models import TaskStatus

# List all tasks
tasks = await omniq.list_tasks()
print(f"Total tasks: {len(tasks)}")

# Filter by status
pending_tasks = [t for t in tasks if t["status"] == TaskStatus.PENDING]
running_tasks = [t for t in tasks if t["status"] == TaskStatus.RUNNING]
completed_tasks = [t for t in tasks if t["status"] == TaskStatus.SUCCESS]
failed_tasks = [t for t in tasks if t["status"] == TaskStatus.FAILED]

print(f"Pending: {len(pending_tasks)}")
print(f"Running: {len(running_tasks)}")
print(f"Completed: {len(completed_tasks)}")
print(f"Failed: {len(failed_tasks)}")
```

## Check Task Status

Quickly check task status without full result:

```python
from omniq.models import TaskStatus

async def check_task(task_id: str):
    """Check task status and provide summary."""
    result = await omniq.get_result(task_id)

    if result is None:
        print("Task not found")
        return

    if isinstance(result, dict):
        status = result.get("status")
        attempts = result.get("attempts", 0)
    else:
        status = result.status
        attempts = result.attempts

    print(f"Status: {status}")

    if status == TaskStatus.PENDING:
        print("Task waiting to be claimed")
    elif status == TaskStatus.RUNNING:
        print(f"Task in progress (attempt {attempts})")
    elif status == TaskStatus.COMPLETED:
        print("Task completed successfully")
    elif status == TaskStatus.FAILED:
        print(f"Task failed after {attempts} attempts")

    if isinstance(result, dict) and result.get("error"):
        print(f"Error: {result['error'].get('message')}")
```

## Monitor Task Health

Build monitoring dashboards using task metadata:

```python
from omniq.models import TaskStatus

async def monitor_dashboard():
    """Show task health summary."""
    tasks = await omniq.list_tasks()

    total = len(tasks)
    pending = len([t for t in tasks if t["status"] == TaskStatus.PENDING])
    running = len([t for t in tasks if t["status"] == TaskStatus.RUNNING])
    completed = len([t for t in tasks if t["status"] == TaskStatus.SUCCESS])
    failed = len([t for t in tasks if t["status"] == TaskStatus.FAILED])

    success_rate = (completed / total * 100) if total > 0 else 0

    print(f"""
    Task Health Dashboard
    ==================
    Total:      {total:6}
    Pending:     {pending:6}
    Running:     {running:6}
    Completed:   {completed:6}
    Failed:      {failed:6}
    Success Rate: {success_rate:.1f}%
    """)

    # Show failing tasks
    if failed > 0:
        print("\nFailed Tasks:")
        for task in tasks:
            if task["status"] == TaskStatus.FAILED:
                error = task.get("error", {})
                print(f"  - {task['id']}: {error.get('message', 'Unknown')}")

## Debug Failed Tasks

Inspect failed tasks to identify patterns:

```python
from omniq.models import TaskStatus

async def debug_failures():
    """Analyze failed tasks for patterns."""
    tasks = await omniq.list_tasks()
    failed_tasks = [t for t in tasks if t["status"] == TaskStatus.FAILED]
    # Group by error type
    error_types = {}
    for task in failed_tasks:
        error = task.get("error", {})
        error_type = error.get("error_type", "unknown")
        error_types[error_type] = error_types.get(error_type, 0) + 1

    print("Error Type Distribution:")
    for error_type, count in error_types.items():
        print(f"  {error_type}: {count}")

    # Show tasks with high retry counts
    high_retry = [t for t in failed_tasks if t.get("attempts", 0) > 2]

    if high_retry:
        print("\nTasks with >2 retries:")
        for task in high_retry:
            print(f"  - {task['id']}: {task.get('attempts')} attempts")

    # Show recent failures
    from datetime import datetime, timedelta, timezone
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    recent_failures = [
        t for t in failed_tasks
        if t.get("failed_at")
        and t.get("failed_at") > recent_time
    ]

    if recent_failures:
        print("\nRecent failures (last 10 minutes):")
        for task in recent_failures:
            print(f"  - {task['id']}: {task.get('failed_at')}")
```

## Best Practices

### 1. Always Handle None Results

```python
result = await omniq.get_result(task_id)

if result is None:
    # Task not found or not complete
    print("Task not ready")
    return
```

### 2. Use Type Checking for Result Format

```python
result = await omniq.get_result(task_id)

if isinstance(result, dict):
    # Dict format (async API)
    status = result.get("status")
elif hasattr(result, 'status'):
    # Object format (sync API or Task object)
    status = result.status
else:
    # Unknown format
    print("Unknown result format")
    return
```

### 3. Extract Error Information Safely

```python
error = result.get("error") if isinstance(result, dict) else result.error

if error:
    # Handle dict error
    if isinstance(error, dict):
        message = error.get("message", "Unknown error")
        error_type = error.get("error_type", "unknown")
    # Handle string error
    elif isinstance(error, str):
        message = error
        error_type = "unknown"
    # Handle TaskError object
    else:
        message = error.message if hasattr(error, 'message') else str(error)
        error_type = error.error_type if hasattr(error, 'error_type') else "unknown"

    print(f"{error_type}: {message}")
```

### 4. Monitor Task Patterns

```python
# Track success rates over time
success_tasks = [t for t in tasks if t.get("status") == "COMPLETED"]
failed_tasks = [t for t in tasks if t.get("status") == "FAILED"]

success_rate = len(success_tasks) / (len(success_tasks) + len(failed_tasks)) * 100

if success_rate < 90:
    print(f"Warning: Low success rate ({success_rate:.1f}%)")
```

### 5. Log Result Retrieval

```python
from omniq.logging import bind_task

logger = bind_task("result-checker", task_id=task_id)

result = await omniq.get_result(task_id)
logger.info(f"Retrieved result with status: {result.get('status')}")
```

## Next Steps

- Learn how to [configure retries](configure-retries.md) based on error patterns
- Read [TaskError API reference](../reference/api/models.md) for full details
- Understand [retry budget semantics](../explanation/retry_mechanism.md)

## Summary

- **get_result()**: Retrieve task results (blocking or non-blocking)
- **Result format**: Dict with status, result, error, attempts, timestamps
- **Error metadata**: error_type, message, retry_count, traceback
- **Monitoring**: Filter tasks, check status, analyze patterns
- **Best practice**: Handle None results, type-check format, extract errors safely

Inspect task results and errors to understand task execution, debug failures, and build monitoring dashboards.
