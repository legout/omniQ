# Async Quickstart

This tutorial will walk you through the basics of using OmniQ with async Python. You'll learn how to:

- Initialize OmniQ with file storage
- Enqueue both sync and async tasks
- Run workers to process tasks
- Retrieve task results

## Prerequisites

You'll need Python 3.13 or later. Install OmniQ:

```bash
pip install omniq
```

## Step 1: Initialize OmniQ

First, create an `AsyncOmniQ` instance with settings. We'll use file storage for this example:

```python
import asyncio
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

async def main():
    # Configure with file storage
    settings = Settings(
        backend="file",
        base_dir=Path("./omniq_data")
    )
    omniq = AsyncOmniQ(settings)
```

The `Settings` class configures your task queue. Key options include:

- `backend`: Storage backend ("file" or "sqlite")
- `base_dir`: Directory for storing task data
- `serializer`: Serialization format ("json" or "pickle")

## Step 2: Define Task Functions

Task functions should be regular Python functions (sync or async):

```python
# Sync task
def add_numbers(a: int, b: int) -> int:
    return a + b

# Async task
async def multiply_numbers(a: int, b: int) -> int:
    await asyncio.sleep(0.1)  # Simulate async work
    return a * b
```

**Important**: Task functions must be importable (top-level functions in a module), not nested functions or lambdas.

## Step 3: Enqueue Tasks

Use `omniq.enqueue()` to add tasks to the queue:

```python
async def main():
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Enqueue tasks
    sync_task_id = await omniq.enqueue(add_numbers, 5, 3)
    async_task_id = await omniq.enqueue(multiply_numbers, 4, 7)

    print(f"Enqueued sync task: {sync_task_id}")
    print(f"Enqueued async task: {async_task_id}")
```

`enqueue()` returns a unique task ID that you can use to track the task later.

## Step 4: Process Tasks with Workers

Create a worker pool to process tasks:

```python
async def main():
    # ... (previous setup)

    # Create worker pool with 2 workers
    workers = omniq.worker(concurrency=2)

    # Start workers in the background
    worker_task = asyncio.create_task(workers.start())

    # Let workers process tasks
    await asyncio.sleep(2.0)

    # Stop workers gracefully
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)
```

The worker pool:
- Claims tasks from the queue
- Executes your task functions
- Handles errors and retries
- Stores results back to the queue

## Step 5: Retrieve Results

Get task results using the task ID:

```python
async def main():
    # ... (enqueue and process tasks)

    # Wait for results
    sync_result = await omniq.get_result(sync_task_id, wait=True, timeout=5.0)
    async_result = await omniq.get_result(async_task_id, wait=True, timeout=5.0)

    print(f"Sync result: {sync_result}")
    print(f"Async result: {async_result}")
```

`get_result()` options:
- `wait=True`: Block until task completes
- `timeout=5.0`: Maximum time to wait
- Returns the task result or `None` if not found

## Complete Example

Here's the complete working example:

```python
import asyncio
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

def add_numbers(a: int, b: int) -> int:
    """Simple sync task."""
    return a + b

async def multiply_numbers(a: int, b: int) -> int:
    """Simple async task."""
    await asyncio.sleep(0.1)
    return a * b

async def main():
    # Initialize OmniQ
    settings = Settings(backend="file", base_dir=Path("./omniq_data"))
    omniq = AsyncOmniQ(settings)

    # Enqueue tasks
    sync_task_id = await omniq.enqueue(add_numbers, 5, 3)
    async_task_id = await omniq.enqueue(multiply_numbers, 4, 7)
    print(f"Enqueued tasks: {sync_task_id}, {async_task_id}")

    # Start workers
    workers = omniq.worker(concurrency=2)
    worker_task = asyncio.create_task(workers.start())

    # Wait for results
    sync_result = await omniq.get_result(sync_task_id, wait=True, timeout=5.0)
    async_result = await omniq.get_result(async_task_id, wait=True, timeout=5.0)

    # Stop workers
    await workers.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)

    print(f"Results: sync={sync_result}, async={async_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- Learn about [scheduling tasks](scheduling.md) with delays and intervals
- Understand [retry behavior](retries.md) and error handling
- See how to [choose a storage backend](../how-to/choose-backend.md)

## Run the Example

A complete runnable example is available in the repository:

```bash
cd examples
python 01_quickstart_async.py
```

This example demonstrates all the concepts covered in this tutorial.
