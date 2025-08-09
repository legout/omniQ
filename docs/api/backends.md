# API - Backends

This section provides a detailed API reference for OmniQ's backend interfaces and implementations. Backends define how OmniQ components (Task Queues, Result Storage, Event Storage) interact with underlying persistence and messaging systems.

## Abstract Base Classes

OmniQ defines abstract base classes for each backend type, ensuring a consistent interface across different implementations.

*   `omniq.backend.base.BaseBackend`: The foundational abstract class for all OmniQ backends.
*   `omniq.backend.base.BaseTaskQueueBackend`: Defines the interface for task queue operations (enqueue, dequeue, etc.).
*   `omniq.backend.base.BaseResultStorageBackend`: Defines the interface for result storage operations (store, retrieve, etc.).
*   `omniq.backend.base.BaseEventStorageBackend`: Defines the interface for event storage operations (log_event, get_events, etc.).

## Concrete Implementations

### File Backend

*   `omniq.backend.file.FileBackend`: Implements backend operations using the local filesystem, with `fsspec` support for cloud storage.
    *   **Parameters**:
        *   `base_dir` (`str`): The base directory for storing data.
    *   **Usage**:
        ```python
        from omniq.backend import FileBackend
        file_backend = FileBackend(base_dir="./omniq_data")
        ```

### Memory Backend

*   `omniq.backend.memory.MemoryBackend`: An in-memory backend for non-persistent storage.
    *   **Parameters**: None
    *   **Usage**:
        ```python
        from omniq.backend import MemoryBackend
        memory_backend = MemoryBackend()
        ```

### SQLite Backend

*   `omniq.backend.sqlite.SQLiteBackend`: Implements backend operations using SQLite.
    *   **Parameters**:
        *   `database_path` (`str`): Path to the SQLite database file.
    *   **Usage**:
        ```python
        from omniq.backend import SQLiteBackend
        sqlite_backend = SQLiteBackend(database_path="omniq.db")
        ```

### PostgreSQL Backend

*   `omniq.backend.postgres.PostgreSQLBackend`: Implements backend operations using PostgreSQL.
    *   **Parameters**:
        *   `dsn` (`str`): PostgreSQL connection string (DSN).
    *   **Usage**:
        ```python
        from omniq.backend import PostgreSQLBackend
        pg_backend = PostgreSQLBackend(dsn="postgresql://user:pass@host:port/dbname")
        ```

### Redis Backend

*   `omniq.backend.redis.RedisBackend`: Implements backend operations using Redis.
    *   **Parameters**:
        *   `host` (`str`): Redis host.
        *   `port` (`int`): Redis port.
        *   `db` (`int`): Redis database number.
    *   **Usage**:
        ```python
        from omniq.backend import RedisBackend
        redis_backend = RedisBackend(host="localhost", port=6379, db=0)
        ```

### NATS Backend

*   `omniq.backend.nats.NATSBackend`: Implements backend operations using NATS.
    *   **Parameters**:
        *   `servers` (`List[str]`): List of NATS server URLs.
    *   **Usage**:
        ```python
        from omniq.backend import NATSBackend
        nats_backend = NATSBackend(servers=["nats://localhost:4222"])
        ```

## Backend Selection and Configuration

OmniQ automatically selects and initializes the appropriate backend based on your configuration settings (`OMNIQ_TASK_QUEUE_TYPE`, `OMNIQ_RESULT_STORAGE_TYPE`, `OMNIQ_EVENT_STORAGE_TYPE`). You can specify backend-specific parameters in your configuration as well.

For more information on configuring backends, refer to the [Configuration](configuration.md) documentation.