# Task 2: Storage Interfaces and SQLite Backend Implementation

## Objective
To define the abstract base classes for all storage components (task queue, result storage, event storage) and to implement the concrete SQLite-based backend for each of these components. This task focuses on creating a fully functional SQLite storage layer, which is a primary requirement.

## Requirements

### 1. Base Storage Interfaces (`src/omniq/storage/base.py`)
- Create a `base.py` file within the `src/omniq/storage/` directory.
- Define abstract base classes (ABCs) for the storage components:
    - `BaseQueue`: An interface for task queue operations. It must define both `async` and `sync` methods for enqueuing and dequeuing tasks. It should also include a method for task locking to prevent duplicate processing.
    - `BaseResultStorage`: An interface for storing and retrieving task results. It must define `async` and `sync` methods.
    - `BaseEventStorage`: An interface for logging task lifecycle events. It must define `async` and `sync` methods.
- These interfaces should be designed with the "Async First, Sync Wrapped" principle in mind. The primary methods should be `async`, and sync wrappers will be provided in the concrete implementations.

### 2. SQLite Backend Implementation (`src/omniq/storage/sqlite.py`)
- Create a `sqlite.py` file within the `src/omniq/storage/` directory.
- Implement the concrete storage classes using `aiosqlite` for the async core and `anyio` for the sync wrappers.

#### `AsyncSQLiteQueue` and `SQLiteQueue`
- Implements `BaseQueue`.
- Manages task persistence in an SQLite database.
- Must support multiple named queues (e.g., using a `queue_name` column in the tasks table).
- Implements a task locking mechanism (e.g., updating a task's status to `processing` within a transaction) to ensure tasks are not processed by more than one worker.
- The `SQLiteQueue` class will be a synchronous wrapper around the `AsyncSQLiteQueue`.

#### `AsyncSQLiteResultStorage` and `SQLiteResultStorage`
- Implements `BaseResultStorage`.
- Stores and retrieves `TaskResult` objects from an SQLite database.
- Supports TTL for results, including a mechanism for cleaning up expired entries.
- The `SQLiteResultStorage` class will be a synchronous wrapper around the `AsyncSQLiteResultStorage`.

#### `AsyncSQLiteEventStorage` and `SQLiteEventStorage`
- Implements `BaseEventStorage`.
- Stores `TaskEvent` objects in an SQLite database. Events should be stored in a structured way that allows for efficient querying.
- The `SQLiteEventStorage` class will be a synchronous wrapper around the `AsyncSQLiteEventStorage`.

### 3. Backend Integration (`src/omniq/backend/`)
- Create `base.py` and `sqlite.py` in the `src/omniq/backend/` directory.
- In `base.py`, define a `BaseBackend` interface with methods to create instances of the task queue, result storage, and event storage.
- In `sqlite.py`, implement `SQLiteBackend` which inherits from `BaseBackend`. This class will be responsible for creating and managing instances of `SQLiteQueue`, `SQLiteResultStorage`, and `SQLiteEventStorage` from a single configuration.

## Completion Criteria
- `src/omniq/storage/base.py` is created with the `BaseQueue`, `BaseResultStorage`, and `BaseEventStorage` abstract base classes.
- `src/omniq/storage/sqlite.py` is created and contains the full implementation for the SQLite-based queue, result storage, and event storage, including both async classes and their sync wrappers.
- `src/omniq/backend/base.py` and `src/omniq/backend/sqlite.py` are created with the `BaseBackend` and `SQLiteBackend` implementations.
- The SQLite implementation correctly handles multiple queues and includes a task locking mechanism.
- All implementations follow the "Async First, Sync Wrapped" design principle.