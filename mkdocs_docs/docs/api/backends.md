# Backends

This section will describe the different backends and their usage.

The Backend classes provide a unified interface for storage systems. They allow you to create a task queue, result storage, and event storage from a single backend configuration.

### Backend-Based Usage

```python
from omniq import OmniQ
from omniq.backend import SQLiteBackend, FileBackend, PostgresBackend

# Create backends
sqlite_backend = SQLiteBackend(project_name="my_project", base_dir="some/path")
file_backend = FileBackend(project_name="my_project", base_dir="some/path")
pg_backend = PostgresBackend(
    project_name="my_project",
    host="localhost",
    port=5432,
    username="postgres",
    password="secret"
)

# Create OmniQ with a single backend
oq = OmniQ.from_backend(sqlite_backend, worker_type="thread_pool", worker_config={"max_workers": 10})

# Or mix backends for different components
oq = OmniQ.from_backend(
    backend=file_backend,  # For task queue
    result_store_backend=sqlite_backend,  # For result storage
    event_store_backend=pg_backend,  # For event storage
    worker_type="async",
    worker_config={"max_workers": 20}
)

# Create individual components from backends
from omniq import TaskQueue, ResultStore, EventStore
task_queue = TaskQueue.from_backend(file_backend, queues=["high", "medium", "low"])
result_store = ResultStore.from_backend(sqlite_backend)
event_store = EventStore.from_backend(pg_backend)