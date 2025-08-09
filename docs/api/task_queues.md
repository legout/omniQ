# API - Task Queues

This section provides a detailed API reference for OmniQ's task queue components. Task queues are central to OmniQ, responsible for managing the flow of tasks from creation to execution.

## Task Queue Models

### `omniq.models.task.Task`

The core data model representing a single task.

*   **Attributes**:
    *   `id` (`str`): Unique identifier for the task. (Auto-generated if not provided)
    *   `func` (`Callable`): The callable function to be executed by the worker.
    *   `args` (`Tuple[Any, ...]`, optional): Positional arguments for the function.
    *   `kwargs` (`Dict[str, Any]`, optional): Keyword arguments for the function.
    *   `queue_name` (`str`, optional): The name of the queue the task belongs to. Defaults to "default".
    *   `priority` (`int`, optional): Task priority (higher value means higher priority). Defaults to `0`.
    *   `ttl` (`int`, optional): Time-To-Live for the task in seconds. After this duration, the task might be considered expired.
    *   `retries` (`int`, optional): Number of times to retry the task if it fails. Defaults to `0`.
    *   `max_retries` (`int`, optional): Maximum number of retries allowed.
    *   `depends_on` (`List[str]`, optional): A list of task IDs that this task depends on. This task will only execute after its dependencies are completed.
    *   `schedule` (`omniq.models.schedule.Schedule`, optional): A `Schedule` object for recurring or delayed execution.

### `omniq.models.schedule.Schedule`

Model for defining task scheduling.

*   **Attributes**:
    *   `run_at` (`datetime`, optional): Specific datetime for one-time execution.
    *   `cron` (`str`, optional): Cron string for recurring execution (e.g., "0 0 * * *").
    *   `interval` (`timedelta`, optional): Time interval for recurring execution.
    *   `paused` (`bool`, optional): If `True`, the schedule is paused.

## Task Queue Interfaces

### `omniq.queue.base.BaseTaskQueue`

The abstract base class for all task queue implementations.

*   **Methods**:
    *   `async enqueue(task: Task)`: Adds a task to the queue.
    *   `async dequeue(queue_name: str = "default") -> Optional[Task]`: Retrieves and removes a task from the queue.
    *   `async get_task(task_id: str) -> Optional[Task]`: Retrieves a task by its ID without removing it.
    *   `async delete_task(task_id: str)`: Deletes a task from the queue.

## Concrete Implementations

OmniQ provides several concrete implementations of `BaseTaskQueue`, leveraging different backends:

*   **`omniq.queue.memory.MemoryTaskQueue`**: In-memory task queue.
*   **`omniq.queue.file.FileTaskQueue`**: File-based task queue using `fsspec`.
    *   **Parameters**: `base_dir` (`str`)
*   **`omniq.queue.sqlite.SQLiteTaskQueue`**: SQLite-based task queue.
    *   **Parameters**: `database_path` (`str`)
*   **`omniq.queue.postgres.PostgreSQLTaskQueue`**: PostgreSQL-based task queue.
    *   **Parameters**: `dsn` (`str`)
*   **`omniq.queue.redis.RedisTaskQueue`**: Redis-based task queue.
    *   **Parameters**: `host` (`str`), `port` (`int`), `db` (`int`)
*   **`omniq.queue.nats.NATSTaskQueue`**: NATS-based task queue.
    *   **Parameters**: `servers` (`List[str]`)

## Usage Example

```python
import asyncio
from datetime import datetime, timedelta
from omniq.models.task import Task
from omniq.models.schedule import Schedule
from omniq.queue import MemoryTaskQueue # Can be replaced with other queue types

async def demonstrate_task_queue():
    task_queue = MemoryTaskQueue()

    # Create a simple task
    def my_simple_func(x, y):
        return x + y
    
    simple_task = Task(func=my_simple_func, args=(10, 20))
    await task_queue.enqueue(simple_task)
    print(f"Enqueued simple task: {simple_task.id}")

    # Create a scheduled task
    def my_scheduled_func():
        print("Scheduled task executed!")
    
    future_time = datetime.utcnow() + timedelta(seconds=5)
    scheduled_task = Task(
        func=my_scheduled_func,
        schedule=Schedule(run_at=future_time)
    )
    await task_queue.enqueue(scheduled_task)
    print(f"Enqueued scheduled task: {scheduled_task.id} to run at {future_time}")

    # Dequeue a task (as a worker would)
    dequeued_task = await task_queue.dequeue()
    if dequeued_task:
        print(f"Dequeued task: {dequeued_task.id}")
        # Execute the task
        result = dequeued_task.func(*dequeued_task.args, **dequeued_task.kwargs)
        print(f"Task result: {result}")
    else:
        print("No tasks in queue.")

    # Demonstrate named queues
    task_high_prio = Task(func=lambda: "High Prio", queue_name="high_priority", priority=10)
    task_low_prio = Task(func=lambda: "Low Prio", queue_name="low_priority", priority=1)

    await task_queue.enqueue(task_high_prio)
    await task_queue.enqueue(task_low_prio)
    print(f"Enqueued tasks to named queues.")

    # Dequeue from specific queue
    high_prio_task = await task_queue.dequeue(queue_name="high_priority")
    if high_prio_task:
        print(f"Dequeued from high_priority: {high_prio_task.func()}")

    # Clean up (delete) a task
    await task_queue.delete_task(simple_task.id)
    print(f"Deleted task {simple_task.id}")

if __name__ == "__main__":
    asyncio.run(demonstrate_task_queue())
```

This API provides the necessary building blocks for managing complex task workflows within OmniQ.