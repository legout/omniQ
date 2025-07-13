# OmniQ PostgreSQL Backend Implementation Task

## Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, and distributed processing in their applications with both synchronous and asynchronous interfaces.

---

## Core Design Principles

- **Async First, Sync Wrapped:** The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
- **Separation of Concerns:** Task queue, result storage, and event logging are decoupled and independent.
- **Interface-Driven:** All components implement common interfaces.
- **Storage Independence:** Allow independent selection of storage backends for tasks, results, and events.

---

## Module Architecture Focus

### `omniq.storage.postgres`

Implement the following classes:
- **AsyncPostgresQueue**: Core async implementation using `asyncpg`.
- **PostgresQueue**: Sync wrapper around `AsyncPostgresQueue`.
- **AsyncPostgresResultStorage**: Async result storage for PostgreSQL.
- **PostgresResultStorage**: Sync wrapper for result storage.
- **AsyncPostgresEventStorage**: Async event storage for PostgreSQL.
- **PostgresEventStorage**: Sync wrapper for event storage.

**Key Design Decisions:**
- Implement async core functionality first.
- Provide sync wrappers using `anyio.from_thread.run()` or event loops.
- Ensure transaction support for consistency.
- Support bulk operations for performance.
- Implement both sync and async context managers.
- Use queue column approach for SQL-based queues.
- Implement task locking using database transactions and row locking.

### `omniq.backend.postgres`

- Integrate the storage classes above into a cohesive backend.
- Expose configuration and initialization for PostgreSQL-backed task queues, result storage, and event storage.
- Ensure backend can be selected independently for tasks, results, and events.

---

## Development Guidelines

### Async First, Sync Wrapped Implementation Guidelines

- Implement all core functionality using async/await.
- Create synchronous wrappers using `anyio.from_thread.run()` or event loops.
- Use `Async` prefix for core async classes, no prefix for sync wrappers. Sync wrapper methods should have a `_sync` suffix.
- Implement both `__aenter__`/`__aexit__` and `__enter__`/`__exit__` context managers.
- Preserve exception context across sync/async boundaries.
- Ensure proper cleanup in both sync and async contexts.

#### Example Pattern

```python
# Async core implementation
class AsyncTaskQueue:
    async def enqueue(self, task):
        # Async implementation
        ...

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Sync wrapper
class TaskQueue:
    def __init__(self, *args, **kwargs):
        self._async_queue = AsyncTaskQueue(*args, **kwargs)

    def enqueue(self, task):
        return anyio.from_thread.run(self._async_queue.enqueue, task)

    def __enter__(self):
        anyio.from_thread.run(self._async_queue.__aenter__)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        anyio.from_thread.run(self._async_queue.__aexit__, exc_type, exc_val, exc_tb)
```

### Storage Implementation

- Implement multiple queues in all task queue backends.
- Use a queue column approach for SQL-based queues.
- Support connection pooling for efficient resource usage.
- Ensure transaction support for consistency.
- Implement bulk operations for performance.
- Implement task locking using database transactions and row locking.
- Support both sync and async context managers.

### Logging and Event Management

- Separate library logging from task events.
- Library logging is for debugging and monitoring the library itself, configured via function, constant, or environment variable.
- Task event logging is for tracking task lifecycle and is only enabled when event storage is explicitly configured.
- Event storage should be SQL-based for efficient querying and analysis.

---

## Scope

Fully implement the PostgreSQL backend for OmniQ, including:

- Task queue (enqueue, dequeue, locking, bulk operations, etc.)
- Result storage (store, retrieve, bulk operations)
- Event storage (log events, query events)
- Database schema creation and migrations as needed
- Asynchronous and synchronous interfaces for all operations
- Proper connection pooling and resource management
- Task locking using database transactions and row locking

---

## Dependencies

- **asyncpg**: Async PostgreSQL database interface

---

## Completion

Upon completion, signal by using the `attempt_completion` tool with a summary of the created prompt.