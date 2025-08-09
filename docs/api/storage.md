# API - Storage

This section provides a detailed API reference for OmniQ's storage components, which manage the persistence of task results and lifecycle events.

## Result Storage

Result storage is responsible for saving and retrieving the outcomes of executed tasks.

### `omniq.results.base.BaseResultStorage`

The abstract base class for all result storage implementations.

*   **Methods**:
    *   `async store_result(task_id: str, result: Any, ttl: Optional[int] = None)`: Stores the result for a given task ID.
    *   `async get_result(task_id: str) -> Any`: Retrieves the result for a given task ID.
    *   `async delete_result(task_id: str)`: Deletes the result for a given task ID.

### Concrete Implementations

*   **`omniq.results.memory.MemoryResultStorage`**: In-memory result storage.
*   **`omniq.results.file.FileResultStorage`**: File-based result storage using `fsspec`.
    *   **Parameters**: `base_dir` (`str`)
*   **`omniq.results.sqlite.SQLiteResultStorage`**: SQLite-based result storage.
    *   **Parameters**: `database_path` (`str`)
*   **`omniq.results.postgres.PostgreSQLResultStorage`**: PostgreSQL-based result storage.
    *   **Parameters**: `dsn` (`str`)
*   **`omniq.results.redis.RedisResultStorage`**: Redis-based result storage.
    *   **Parameters**: `host` (`str`), `port` (`int`), `db` (`int`)
*   **`omniq.results.nats.NATSResultStorage`**: NATS-based result storage.
    *   **Parameters**: `servers` (`List[str]`)

## Event Storage

Event storage is responsible for persisting task lifecycle events.

### `omniq.events.base.BaseEventStorage`

The abstract base class for all event storage implementations.

*   **Methods**:
    *   `async log_event(event: TaskEvent)`: Logs a `TaskEvent`.
    *   `async get_events(task_id: str) -> List[TaskEvent]`: Retrieves all events for a given task ID.
    *   `async get_all_events() -> List[TaskEvent]`: Retrieves all logged events.

### Concrete Implementations

*   **`omniq.events.memory.MemoryEventStorage`**: In-memory event storage.
*   **`omniq.events.file.FileEventStorage`**: File-based event storage using `fsspec`.
    *   **Parameters**: `base_dir` (`str`)
*   **`omniq.events.sqlite.SQLiteEventStorage`**: SQLite-based event storage.
    *   **Parameters**: `database_path` (`str`)
*   **`omniq.events.postgres.PostgreSQLEventStorage`**: PostgreSQL-based event storage.
    *   **Parameters**: `dsn` (`str`)
*   **`omniq.events.redis.RedisEventStorage`**: Redis-based event storage.
    *   **Parameters**: `host` (`str`), `port` (`int`), `db` (`int`)
*   **`omniq.events.nats.NATSEventStorage`**: NATS-based event storage.
    *   **Parameters**: `servers` (`List[str]`)

## Usage Example

```python
import asyncio
from omniq.results import SQLiteResultStorage
from omniq.events import FileEventStorage
from omniq.models.event import TaskEvent
from datetime import datetime

async def demonstrate_storage():
    # Initialize result storage
    result_store = SQLiteResultStorage(database_path="my_results.db")
    await result_store.connect() # Connect if necessary

    # Store a result
    task_id = "task_123"
    result_data = {"status": "completed", "value": 42}
    await result_store.store_result(task_id, result_data)
    print(f"Stored result for {task_id}")

    # Retrieve a result
    retrieved_result = await result_store.get_result(task_id)
    print(f"Retrieved result for {task_id}: {retrieved_result}")

    # Initialize event storage
    event_store = FileEventStorage(base_dir="./my_events_log")
    await event_store.connect() # Connect if necessary

    # Log an event
    event = TaskEvent(task_id=task_id, event_type="STARTED", timestamp=datetime.utcnow(), details={"worker": "worker-A"})
    await event_store.log_event(event)
    print(f"Logged event for {task_id}")

    # Retrieve events for a task
    events_for_task = await event_store.get_events(task_id)
    for evt in events_for_task:
        print(f"  Event: {evt.event_type} at {evt.timestamp}")
    
    await result_store.disconnect() # Disconnect if necessary
    await event_store.disconnect() # Disconnect if necessary

if __name__ == "__main__":
    asyncio.run(demonstrate_storage())
```

For more details on how these storage components are integrated within the main OmniQ instance, refer to the [Configuration](configuration.md) documentation.