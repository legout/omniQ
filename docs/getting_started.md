# Getting Started with OmniQ

This section guides you through the initial setup and basic usage of OmniQ.

## Installation

OmniQ can be installed using `pip`. It's recommended to use a virtual environment.

```bash
pip install omniq
```

## Project Setup

OmniQ uses `uv` for dependency management. If you don't have `uv` installed, you can install it via `pip`:

```bash
pip install uv
```

Once `uv` is installed, you can set up your project:

```bash
uv init
uv add omniq
```

## Basic Usage

OmniQ is designed for both synchronous and asynchronous task processing.

### Synchronous Example

```python
from omniq import OmniQ

def my_sync_task(x, y):
    return x + y

with OmniQ() as omniq:
    task_id = omniq.enqueue(my_sync_task, 1, 2)
    result = omniq.get_result(task_id)
    print(f"Synchronous task result: {result}")
```

### Asynchronous Example

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
```

For more detailed examples, refer to the [Examples](examples.md) section.