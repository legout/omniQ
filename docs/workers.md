# Workers

OmniQ workers are responsible for executing tasks retrieved from task queues. OmniQ supports various worker types, allowing you to choose the best execution model for your application.

## Key Concepts

*   **Task Execution**: Workers fetch tasks from configured queues, execute the associated functions, and record results.
*   **Concurrency Models**: Different worker types offer different concurrency models (e.g., asynchronous, threading, multiprocessing).
*   **Lifecycle Management**: Workers handle the lifecycle of tasks, including error handling, retries, and result storage.

## Supported Worker Types

OmniQ provides several built-in worker implementations:

*   **AsyncWorker**:
    *   Designed for native asynchronous task execution.
    *   Ideal for I/O-bound tasks where `asyncio` can be fully leveraged.
    ```python
    from omniq.workers import AsyncWorker
    # Example usage (typically integrated within OmniQ instance)
    worker = AsyncWorker(...)
    await worker.start()
    ```
*   **ThreadWorker**:
    *   Executes tasks in a thread pool.
    *   Suitable for CPU-bound tasks that can benefit from parallelism within a single process.
    ```python
    from omniq.workers import ThreadWorker
    # Example usage
    worker = ThreadWorker(...)
    worker.start()
    ```
*   **ProcessWorker**:
    *   Executes tasks in separate processes.
    *   Best for heavily CPU-bound tasks to bypass Python's Global Interpreter Lock (GIL).
    ```python
    from omniq.workers import ProcessWorker
    # Example usage
    worker = ProcessWorker(...)
    worker.start()
    ```
*   **GeventWorker**:
    *   Utilizes `gevent` for cooperative multitasking (green threads).
    *   Useful for high-concurrency I/O-bound tasks in applications that use `gevent`.
    ```python
    from omniq.workers import GeventWorker
    # Example usage
    worker = GeventWorker(...)
    worker.start()
    ```

## Worker Configuration

Workers are typically configured as part of your main OmniQ instance. You can specify the default worker type in your configuration.

```python
from omniq import OmniQ
from omniq.config import OmniQConfig

# Configure OmniQ to use a ThreadWorker by default
config = OmniQConfig(default_worker="thread")
omniq = OmniQ(config=config)

# When you enqueue a task, it will be processed by the default worker
# Or you can specify a worker type for a specific task
def my_task():
    print("Task executed by a worker")

omniq.enqueue(my_task)
```

## Running Workers

Workers can be started explicitly or managed by the OmniQ instance.

```python
import time
from omniq import OmniQ

def long_running_task(x, y):
    time.sleep(2) # Simulate work
    return x * y

with OmniQ() as omniq:
    task_id = omniq.enqueue(long_running_task, 5, 6)
    print(f"Task enqueued with ID: {task_id}")
    # In a real application, workers would be running in the background
    # and pick up tasks from the queue.
    # For demonstration, you might explicitly start a worker or wait for results.
    result = omniq.get_result(task_id, timeout=5)
    print(f"Task result: {result}")
```

For more details on task management and results, refer to the [Task Queues](task_queues.md) and [Storage](storage.md) documentation.