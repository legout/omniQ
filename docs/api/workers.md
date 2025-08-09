# API - Workers

This section provides a detailed API reference for OmniQ's worker components. Workers are the execution engines that pick up tasks from queues, process them, and manage their lifecycle.

## Worker Interfaces

### `omniq.workers.base.BaseWorker`

The abstract base class for all worker implementations.

*   **Methods**:
    *   `async start()`: Starts the worker, typically initiating a loop to fetch and process tasks.
    *   `async stop()`: Stops the worker gracefully.
    *   `async process_task(task: Task)`: Processes a single task. This method handles task execution, result storage, and event logging.

## Concrete Implementations

OmniQ provides several concrete worker implementations, each optimized for different concurrency models:

### `omniq.workers.async_.AsyncWorker`

An asynchronous worker that leverages Python's `asyncio` for concurrent task execution. Ideal for I/O-bound tasks.

*   **Parameters**:
    *   `task_queue` (`BaseTaskQueue`): The task queue from which to fetch tasks.
    *   `result_storage` (`BaseResultStorage`): The storage for task results.
    *   `event_logger` (`AsyncEventLogger`): The event logger for task lifecycle events.
    *   `concurrency` (`int`, optional): The maximum number of concurrent tasks. Defaults to `10`.
    *   `queue_names` (`List[str]`, optional): List of queue names to pull tasks from. Defaults to `["default"]`.

### `omniq.workers.thread.ThreadWorker`

A synchronous worker that uses a thread pool for executing tasks. Suitable for CPU-bound tasks where GIL is not a major concern, or for integrating with blocking libraries.

*   **Parameters**:
    *   `task_queue` (`BaseTaskQueue`): The task queue.
    *   `result_storage` (`BaseResultStorage`): The result storage.
    *   `event_logger` (`EventLogger`): The event logger.
    *   `max_workers` (`int`, optional): The maximum number of worker threads. Defaults to `cpu_count() * 5`.
    *   `queue_names` (`List[str]`, optional): List of queue names to pull tasks from. Defaults to `["default"]`.

### `omniq.workers.process.ProcessWorker`

A synchronous worker that uses a process pool for executing tasks. Best for CPU-bound tasks that benefit from true parallelism by bypassing the GIL.

*   **Parameters**:
    *   `task_queue` (`BaseTaskQueue`): The task queue.
    *   `result_storage` (`BaseResultStorage`): The result storage.
    *   `event_logger` (`EventLogger`): The event logger.
    *   `max_workers` (`int`, optional): The maximum number of worker processes. Defaults to `cpu_count()`.
    *   `queue_names` (`List[str]`, optional): List of queue names to pull tasks from. Defaults to `["default"]`.

### `omniq.workers.gevent.GeventWorker`

A worker that uses `gevent` for cooperative multitasking. Suitable for high-concurrency I/O-bound tasks in `gevent`-enabled environments.

*   **Parameters**:
    *   `task_queue` (`BaseTaskQueue`): The task queue.
    *   `result_storage` (`BaseResultStorage`): The result storage.
    *   `event_logger` (`EventLogger`): The event logger.
    *   `pool_size` (`int`, optional): The size of the gevent greenlet pool. Defaults to `100`.
    *   `queue_names` (`List[str]`, optional): List of queue names to pull tasks from. Defaults to `["default"]`.

## Worker Lifecycle and Integration

Workers are typically instantiated and managed by the main `OmniQ` or `AsyncOmniQ` instance. They continuously poll the configured task queues, execute tasks, update results, and log events.

```python
import asyncio
from omniq import AsyncOmniQ
from omniq.config import OmniQConfig

async def my_long_running_task(data):
    print(f"Worker processing: {data}")
    await asyncio.sleep(2)
    return f"Processed: {data}"

async def main_worker_example():
    # Configure OmniQ to use a specific worker type
    config = OmniQConfig(
        default_worker="async", # or "thread", "process", "gevent"
        task_queue_type="memory",
        result_storage_type="memory"
    )

    async with AsyncOmniQ(config=config) as omniq:
        print("OmniQ instance started with configured worker.")
        
        # Enqueue a task
        task_id = await omniq.enqueue(my_long_running_task, "some important data")
        print(f"Task '{task_id}' enqueued.")

        # In a real application, the worker would be running in the background
        # and would pick up this task. We can wait for the result.
        result = await omniq.get_result(task_id, timeout=5)
        print(f"Task '{task_id}' completed with result: {result}")

if __name__ == "__main__":
    asyncio.run(main_worker_example())
```

Understanding the different worker types and their configurations is crucial for optimizing OmniQ's performance and resource utilization in various application scenarios.