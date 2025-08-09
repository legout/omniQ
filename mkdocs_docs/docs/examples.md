# Examples

This section will provide a variety of examples to demonstrate OmniQ's features.

### Component-Based Usage

```python
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage
from omniq.workers import ThreadPoolWorker
import datetime as dt

# Create components individually
queue = FileTaskQueue(
    project_name="my_project",
    base_dir="some/path",
    queues=["low", "medium", "high"]
)

result_store = SQLiteResultStorage(
    project_name="my_project",
    base_dir="some/path"
)

# Create worker with reference to queue and result store
worker = ThreadPoolWorker(
    queue=queue,
    result_store=result_store,
    max_workers=20
)

# Define a task
def simple_task(name):
    print(f"Hello {name}")
    return name

# Start the worker
worker.start()

# Enqueue a task
task_id = queue.enqueue(
    func=simple_task,
    func_args=dict(name="Tom"),
    queue_name="low"
)

# Get the result
result = result_store.get(task_id)

# Stop the worker
worker.stop()

# Using context managers
with FileTaskQueue(...) as queue, SQLiteResultStorage(...) as result_store, ThreadPoolWorker(queue=queue, result_store=result_store) as worker:
    task_id = queue.enqueue(simple_task, func_args=dict(name="Tom"))
    result = result_store.get(task_id)
```

### Configuration-Based Usage

```python
from omniq import OmniQ
from omniq.models import FileTaskQueueConfig, SQLiteResultStorageConfig

# Create components using specific config classes
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage

queue = FileTaskQueue.from_config(
    FileTaskQueueConfig(
        project_name="my_project",
        base_dir="some/path",
        queues=["high", "medium", "low"]
    )
)

result_store = SQLiteResultStorage.from_config(
    SQLiteResultStorageConfig(
        project_name="my_project",
        base_dir="some/path"
    )
)

# Load from YAML file
oq = OmniQ.from_config_file("config.yaml")
```

### Working with Multiple Queues

```python
from omniq.queue import PostgresTaskQueue
from omniq.workers import ThreadPoolWorker

# Create PostgreSQL queue with multiple named queues
queue = PostgresTaskQueue(
    project_name="my_project",
    host="localhost",
    port=5432,
    username="postgres",
    password="secret",
    queues=["high", "medium", "low"]
)

# Create worker that processes queues in priority order
worker = ThreadPoolWorker(queue=queue, max_workers=10)
worker.start()

# Enqueue tasks to different queues
high_task_id = queue.enqueue(simple_task, func_args=dict(name="High Priority"), queue_name="high")
medium_task_id = queue.enqueue(simple_task, func_args=dict(name="Medium Priority"), queue_name="medium")
low_task_id = queue.enqueue(simple_task, func_args=dict(name="Low Priority"), queue_name="low")

# Worker will process "high" queue tasks first, then "medium", then "low"
```

### Handling Both Sync and Async Tasks

```python
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.workers import AsyncWorker
import asyncio

# Create components
queue = FileTaskQueue(project_name="my_project", base_dir="some/path")
worker = AsyncWorker(queue=queue, max_workers=10)

# Define sync and async tasks
def sync_task(x, y):
    return x * y

async def async_task(x, y):
    await asyncio.sleep(0.1)  # Simulate I/O
    return x + y

# Start worker
worker.start()

# Enqueue both types of tasks
sync_task_id = queue.enqueue(sync_task, func_args=dict(x=5, y=10))
async_task_id = queue.enqueue(async_task, func_args=dict(x=5, y=10))

# Get results
sync_result = worker.get_result(sync_task_id)  # 50
async_result = worker.get_result(async_task_id)  # 15
```

### Using fsspec for Cloud Storage

```python
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.storage import FileResultStorage

# Using local filesystem with DirFileSystem
local_queue = FileTaskQueue(
    project_name="my_project",
    base_dir="/path/to/local/storage",
    queues=["high", "medium", "low"]
)

# Using S3 (requires s3fs package)
s3_queue = FileTaskQueue(
    project_name="my_project",
    base_dir="s3://my-bucket/omniq",
    queues=["high", "medium", "low"],
    storage_options={"key": "access_key", "secret": "secret_key"}
)

# Create OmniQ with cloud storage
oq = OmniQ(
    project_name="my_project",
    task_queue=s3_queue,
    result_store=FileResultStorage(base_dir="s3://my-bucket/omniq/results")
)