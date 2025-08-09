# Storage

OmniQ provides flexible storage solutions for task results and events, allowing you to choose the backend that best suits your application's needs for persistence, scalability, and performance.

## Key Concepts

*   **Result Storage**: Stores the outcomes (return values or exceptions) of executed tasks.
*   **Event Storage**: Logs task lifecycle events (e.g., enqueued, started, completed, failed) for monitoring and auditing.
*   **Backend Independence**: Result storage and event storage can be configured with different backends, independently of each other and of the task queue backend.

## Supported Storage Backends

OmniQ offers several built-in backends for both result and event storage:

*   **Memory Backend**:
    *   **Use Case**: Non-persistent storage, suitable for testing, short-lived tasks, or when results/events do not need to survive application restarts.
    ```python
    from omniq.results import MemoryResultStorage
    from omniq.events import MemoryEventStorage
    result_storage = MemoryResultStorage()
    event_storage = MemoryEventStorage()
    ```
*   **File Backend**:
    *   **Use Case**: Persistent storage using the local filesystem or cloud storage via `fsspec` (e.g., S3, Azure Blob Storage, Google Cloud Storage).
    ```python
    from omniq.results import FileResultStorage
    from omniq.events import FileEventStorage
    result_storage = FileResultStorage(base_dir="./omniq_results")
    event_storage = FileEventStorage(base_dir="./omniq_events")
    ```
*   **SQLite Backend**:
    *   **Use Case**: Lightweight, file-based relational database for persistent storage. Good for single-node deployments or when a full database server is not desired.
    ```python
    from omniq.results import SQLiteResultStorage
    from omniq.events import SQLiteEventStorage
    result_storage = SQLiteResultStorage(database_path="results.db")
    event_storage = SQLiteEventStorage(database_path="events.db")
    ```
*   **PostgreSQL Backend**:
    *   **Use Case**: Robust and scalable relational database for persistent storage in production environments.
    ```python
    from omniq.results import PostgreSQLResultStorage
    from omniq.events import PostgreSQLEventStorage
    result_storage = PostgreSQLResultStorage(dsn="postgresql://user:password@host:port/database")
    event_storage = PostgreSQLEventStorage(dsn="postgresql://user:password@host:port/database")
    ```
*   **Redis Backend**:
    *   **Use Case**: High-performance, in-memory data store with optional persistence, suitable for caching results or high-throughput event logging.
    ```python
    from omniq.results import RedisResultStorage
    from omniq.events import RedisEventStorage
    result_storage = RedisResultStorage(host="localhost", port=6379)
    event_storage = RedisEventStorage(host="localhost", port=6379)
    ```
*   **NATS Backend**:
    *   **Use Case**: Messaging system for distributed event logging and real-time result propagation.
    ```python
    from omniq.results import NATSResultStorage
    from omniq.events import NATSEventStorage
    result_storage = NATSResultStorage(servers=["nats://localhost:4222"])
    event_storage = NATSEventStorage(servers=["nats://localhost:4222"])
    ```

## Configuring Storage

You can configure the storage backends for results and events via the OmniQ configuration, either through environment variables, YAML files, or directly in code.

```python
from omniq import OmniQ
from omniq.config import OmniQConfig

# Using configuration
config = OmniQConfig(
    result_storage_type="sqlite",
    event_storage_type="file",
    result_storage_path="my_app_results.db", # Path for SQLite
    event_storage_base_dir="./app_events" # Base directory for File storage
)

omniq = OmniQ(config=config)

# Get a task result
task_id = omniq.enqueue(lambda: "hello")
result = omniq.get_result(task_id)
print(f"Task result: {result}")
```

## Retrieving Results

After a task is executed, its result can be retrieved using the `get_result` method of the OmniQ instance.

```python
from omniq import OmniQ

def calculate_sum(a, b):
    return a + b

with OmniQ() as omniq:
    task_id = omniq.enqueue(calculate_sum, 10, 20)
    result = omniq.get_result(task_id, timeout=10) # Wait up to 10 seconds for result
    print(f"Calculation result: {result}")
```

## Event Logging

OmniQ automatically logs various events throughout a task's lifecycle. These events can be retrieved and processed for monitoring, debugging, or building audit trails.

```python
from omniq import OmniQ
from omniq.events import TaskEvent

# Assuming an OmniQ instance with event storage configured
with OmniQ() as omniq:
    task_id = omniq.enqueue(lambda: "eventful task")

    # In a real scenario, you would typically have an event processor
    # listening for events. For demonstration, we might retrieve them directly
    # (Note: direct retrieval of all events might not be efficient for large systems)
    events = omniq.get_events(task_id)
    for event in events:
        print(f"Event: {event.event_type} for task {event.task_id} at {event.timestamp}")
```

For more details on event types and processing, refer to the [Events](events.md) documentation.