# OmniQ

OmniQ is a modular Python task queue library designed for flexible and efficient task processing, supporting both local and distributed environments. It adopts an "Async First, Sync Wrapped" architecture, providing high performance with easy-to-use synchronous interfaces.

## Key Features

*   **Flexible Backends**: Supports various backends for task queues, result storage, and event logging including Memory, File (with `fsspec` for cloud storage), SQLite, PostgreSQL, Redis, and NATS.
*   **Multiple Worker Types**: Offers different concurrency models with Async, Thread, Process, and Gevent workers.
*   **Comprehensive Configuration**: Easily configurable via environment variables, YAML files, or direct code.
*   **Task Management**: Features like task dependencies, scheduling, and Time-To-Live (TTL) for fine-grained control.
*   **Event-Driven Architecture**: Robust event logging for monitoring and auditing task lifecycles.
*   **Intelligent Serialization**: Efficient handling of Python objects using `msgspec` and `dill`.
*   **Named Queues**: Organize and prioritize tasks across multiple queues.

## Documentation

For comprehensive information on installation, usage, configuration, and API details, please refer to the [full documentation](docs/index.md).

## Quick Start

Install OmniQ using `pip`:

```bash
pip install omniq
```

A simple asynchronous example:

```python
import asyncio
from omniq import AsyncOmniQ

async def my_async_task(x, y):
    await asyncio.sleep(0.1) # Simulate async operation
    return x * y

async def main():
    async with AsyncOmniQ() as omniq:
        task_id = await omniq.enqueue(my_async_task, 3, 4)
        result = await omniq.get_result(task_id)
        print(f"Asynchronous task result: {result}")

if __name__ == "__main__":
    asyncio.run(main())