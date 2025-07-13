# OmniQ SQLite Backend Implementation Task

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

### `omniq.storage.sqlite`

Implement the following classes:
- **AsyncSQLiteQueue**: Core async implementation using `aiosqlite` for task queue operations.
- **SQLiteQueue**: Synchronous wrapper around `AsyncSQLiteQueue`.
- **AsyncSQLiteResultStorage**: Async result storage implementation.
- **SQLiteResultStorage**: Sync wrapper for result storage.
- **AsyncSQLiteEventStorage**: Async event storage implementation.
- **SQLiteEventStorage**: Sync wrapper for event storage.

**Responsibilities and Design Decisions:**
- All core logic must be implemented asynchronously, with sync wrappers using `anyio.from_thread.run()` or equivalent.
- Each storage class must implement both async and sync context managers (`__aenter__`/`__aexit__`, `__enter__`/`__exit__`).
- Ensure proper resource management and exception propagation across sync/async boundaries.
- Use a queue column approach for SQL-based queues to support multiple queues.
- Implement transaction support for consistency, bulk operations for performance, and task locking to prevent duplicate execution.
- Database schemas must support task queue, result storage, and event logging as independent components.

### `omniq.backend.sqlite`

- Provide backend integration that wires up the SQLite-based queue, result storage, and event storage.
- Ensure the backend allows independent selection and configuration of each storage component.

---

## Development Guidelines

### Async First, Sync Wrapped Implementation Guidelines

- All core functionality must use async/await.
- Synchronous wrappers should use `anyio.from_thread.run()` or equivalent.
- Use `Async` prefix for async classes, no prefix for sync wrappers. Sync wrapper methods may use a `_sync` suffix.
- Implement both async and sync context managers.
- Ensure proper cleanup and error handling in both sync and async contexts.

### Storage Implementation

- Support multiple queues using a queue column in SQL tables.
- Implement connection pooling and efficient transaction management with `aiosqlite`.
- Support bulk operations for enqueue/dequeue and result/event storage.
- Implement robust task locking using database transactions and row locking to prevent duplicate execution.
- All storage backends (queue, result, event) must be independently selectable and configurable.

### Logging and Event Management

- Separate library logging from task event logging.
- Event storage is only enabled when explicitly configured.
- Task event logging should be implemented using SQL tables for efficient querying and analysis.

---

## Scope

Fully implement the SQLite backend for OmniQ, including:

- Task queue (enqueue, dequeue, task locking, bulk operations)
- Result storage (store, retrieve, bulk operations)
- Event storage (log events, query events)
- Database schema creation and migrations as needed
- Both asynchronous and synchronous interfaces for all operations
- Proper connection management and resource cleanup

---

## Dependencies

- **aiosqlite**: Async SQLite database interface (required for all async database operations)

---

## Completion

Signal completion of this task by using the `attempt_completion` tool with a summary of the created prompt.