# Task Queues

In OmniQ, task queues are responsible for storing and managing tasks before they are processed by workers. OmniQ supports multiple named queues and various backends for task storage.

## Key Concepts

*   **Named Queues**: Tasks can be enqueued into specific named queues, allowing for logical separation and priority management.
*   **Priority Ordering**: Tasks within a queue can be prioritized, influencing the order in which workers pick them up.
*   **Backend Independence**: You can configure different backends for your task queues independently of other components like result storage or event logging.

## Supported Backends

OmniQ offers several built-in backends for task queues:

*   **Memory Backend**: Ideal for in-memory processing, suitable for scenarios where persistence is not required or for testing.
    ```python
    from omniq.queue import MemoryTaskQueue
    queue = MemoryTaskQueue()
    ```
*   **File Backend**: Stores tasks in files, leveraging `fsspec` for flexible storage locations, including local disk and cloud storage (S3, Azure, GCP).
    ```python
    from omniq.queue import FileTaskQueue
    queue = FileTaskQueue(base_dir="./omniq_tasks")
    ```
*   **SQLite Backend**: Utilizes SQLite for persistent task storage.
    ```python
    from omniq.queue import SQLiteTaskQueue
    queue = SQLiteTaskQueue(database_path="tasks.db")
    ```
*   **PostgreSQL Backend**: Connects to a PostgreSQL database for robust and scalable task persistence.
    ```python
    from omniq.queue import PostgreSQLTaskQueue
    queue = PostgreSQLTaskQueue(dsn="postgresql://user:password@host:port/database")
    ```
*   **Redis Backend**: Leverages Redis for high-performance, in-memory task queuing with optional persistence.
    ```python
    from omniq.queue import RedisTaskQueue
    queue = RedisTaskQueue(host="localhost", port=6379)
    ```
*   **NATS Backend**: Integrates with NATS for distributed messaging and task queuing.
    ```python
    from omniq.queue import NATSTaskQueue
    queue = NATSTaskQueue(servers=["nats://localhost:4222"])
    ```

## Enqueuing Tasks

Tasks are enqueued using the `enqueue` method of your OmniQ instance. You can specify the queue name.

```python
from omniq import OmniQ

def my_task(data):
    print(f"Processing: {data}")

with OmniQ() as omniq:
    # Enqueue to default queue
    task_id_default = omniq.enqueue(my_task, "Hello from default queue!")

    # Enqueue to a named queue
    task_id_priority = omniq.enqueue(my_task, "High priority task", queue_name="priority_queue")

    print(f"Task ID (default): {task_id_default}")
    print(f"Task ID (priority): {task_id_priority}")
```

## Retrieving Tasks (for Workers)

Workers interact with task queues to retrieve tasks for processing. This is typically handled internally by OmniQ's worker implementations.

```python
# Example of how a worker might retrieve tasks (simplified)
# This is usually abstracted by OmniQ's worker classes
async def get_next_task(queue):
    task = await queue.dequeue()
    return task
```

For more details on how workers process tasks from queues, refer to the [Workers](workers.md) documentation.