# Getting Started

This page will guide you through the process of setting up and using OmniQ.

## Basic Usage with AsyncOmniQ

```python
from omniq import AsyncOmniQ
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage, PostgresEventStorage
import datetime as dt

# Create AsyncOmniQ instance with default components
oq = AsyncOmniQ(
    project_name="my_project",
    task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
    result_store=SQLiteResultStorage(base_dir="some/path"),
    event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
)

# Define an async task
async def async_task(name):
    print(f"Hello {name}")
    return name

# Start the worker
await oq.start_worker()

# Enqueue a task
task_id = await oq.enqueue(
    func=async_task,
    func_args=dict(name="Tom"),
    queue_name="low",
    run_in=dt.timedelta(seconds=100),
    ttl=dt.timedelta(hours=1),
    result_ttl=dt.timedelta(minutes=5)
)

# Get the result
result = await oq.get_result(task_id)

# Schedule a recurring task
schedule_id = await oq.schedule(
    func=async_task,
    func_args=dict(name="Tom"),
    interval=dt.timedelta(seconds=10),
    queue_name="low"
)

# Get latest result from scheduled task
latest_result = await oq.get_result(schedule_id=schedule_id, kind="latest")

# Stop the worker
await oq.stop_worker()

# Using async context manager
async with AsyncOmniQ(...) as oq:
    task_id = await oq.enqueue(async_task, func_args=dict(name="Tom"))
    result = await oq.get_result(task_id)
```

## Basic Usage with OmniQ (Sync)

```python
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage, PostgresEventStorage
import datetime as dt

# Create OmniQ instance with default components
oq = OmniQ(
    project_name="my_project",
    task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
    result_store=SQLiteResultStorage(base_dir="some/path"),
    event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
)

# Define a task
def simple_task(name):
    print(f"Hello {name}")
    return name

# Start the worker
oq.start_worker()

# Enqueue a task
task_id = oq.enqueue(
    func=simple_task,
    func_args=dict(name="Tom"),
    queue_name="low",
    run_in=dt.timedelta(seconds=100),
    ttl=dt.timedelta(hours=1),
    result_ttl=dt.timedelta(minutes=5)
)

# Get the result
result = oq.get_result(task_id)

# Schedule a recurring task
schedule_id = oq.schedule(
    func=simple_task,
    func_args=dict(name="Tom"),
    interval=dt.timedelta(seconds=10),
    queue_name="low"
)

# Get latest result from scheduled task
latest_result = oq.get_result(schedule_id=schedule_id, kind="latest")

# Stop the worker
oq.stop_worker()

# Using sync context manager
with OmniQ(...) as oq:
    task_id = oq.enqueue(simple_task, func_args=dict(name="Tom"))
    result = oq.get_result(task_id)
```