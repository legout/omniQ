# OmniQ Architecture

Learn about OmniQ's architecture, component boundaries, and how they work together.

## Overview

OmniQ has a clean, modular architecture with clear separation of concerns across four main components:

1. **Façade Layer**: User-facing API (`AsyncOmniQ` / `OmniQ`)
2. **Queue Layer**: Core task queue engine (`AsyncTaskQueue`)
3. **Worker Layer**: Task execution pool (`AsyncWorkerPool`)
4. **Storage Layer**: Persistence abstraction (`BaseStorage`)

This separation enables:
- Independent testing of components
- Easy swapping of storage backends
- Clear ownership boundaries
- Flexible deployment patterns

## Component Diagram

```mermaid
graph TD
    UserApp[User Application<br/>(Your Code)]
    Facade[Façade Layer<br/>AsyncOmniQ / OmniQ<br/><br/>Task Lifecycle Management<br/>- enqueue<br/>- get_result<br/>- worker]
    Queue[Queue Layer<br/>AsyncTaskQueue<br/><br/>Core Queue Logic<br/>- dequeue FIFO<br/>- retry scheduling<br/>- interval task rescheduling<br/>- task state management]
    Worker[Worker Layer<br/>AsyncWorkerPool<br/><br/>Task Execution<br/>- claim tasks from queue<br/>- deserialize arguments<br/>- execute task functions<br/>- serialize results<br/>- handle errors]
    Storage[Storage Layer<br/>BaseStorage Implementations<br/><br/>FileStorage<br/>SQLiteStorage]

    UserApp -->|uses| Facade
    Facade -->|delegates| Queue
    Queue -->|uses| Worker
    Worker -->|uses| Storage
## Component Responsibilities

### Façade Layer

The façade (`AsyncOmniQ` / `OmniQ`) provides a simplified, user-facing API.

**Responsibilities**:
- Initialize settings and storage backend
- Provide high-level task operations
- Create worker pools
- Delegating to queue and storage

**Key Methods**:
```python
class AsyncOmniQ:
    async def enqueue(self, func_path, args, kwargs, ...): ...
    async def get_result(self, task_id, wait, timeout): ...
    def worker(self, concurrency, poll_interval): ...
```

**Benefits**:
- Simple API for common use cases
- Encapsulates complexity
- Single import point (`from omniq import AsyncOmniQ`)

### Queue Layer

The queue (`AsyncTaskQueue`) handles all task queue logic and state management.

**Responsibilities**:
- FIFO task dequeue (with ETA scheduling)
- Retry policy implementation
- Interval task rescheduling
- Task state transitions (PENDING → RUNNING → COMPLETED/FAILED)
- Atomic task claims for workers

**Key Methods**:
```python
class AsyncTaskQueue:
    async def enqueue(self, func_path, args, kwargs, ...): ...
    async def dequeue(self): ...
    async def complete_task(self, task_id, result, task): ...
    async def fail_task(self, task_id, error, task): ...
```

**Owned Concepts**:
- Retry budget (attempts vs max_retries)
- Exponential backoff with jitter
- Scheduling semantics (eta, interval)
- Task lifecycle management

**Benefits**:
- Testable without workers
- Swappable storage backends
- Clear retry and scheduling semantics

### Worker Layer

The worker pool (`AsyncWorkerPool`) manages concurrent task execution.

**Responsibilities**:
- Claim tasks from queue atomically
- Execute task functions
- Serialize/deserialize task data
- Handle task errors and timeouts
- Report completion/failure to queue

**Key Methods**:
```python
class AsyncWorkerPool:
    def __init__(self, queue, concurrency, poll_interval): ...
    async def start(self): ...
    async def stop(self): ...
    async def process_tasks(self, limit): ...
```

**Owned Concepts**:
- Concurrency management
- Polling interval
- Task function import and execution
- Error propagation

**Benefits**:
- Isolated from queue logic
- Flexible concurrency configuration
- Graceful shutdown handling

### Storage Layer

Storage (`BaseStorage` and implementations) provides persistence abstraction.

**Responsibilities**:
- Persist task metadata and results
- Provide atomic task claims
- Support task status lookups
- Handle serialization/deserialization

**Key Methods**:
```python
class BaseStorage(ABC):
    @abstractmethod
    async def enqueue(self, task): ...

    @abstractmethod
    async def dequeue(self): ...

    @abstractmethod
    async def claim_task(self, task_id, worker_id): ...

    @abstractmethod
    async def complete_task(self, task_id, result): ...

    @abstractmethod
    async def fail_task(self, task_id, error): ...
```

**Implementations**:
- `FileStorage`: JSON files in directory
- `SQLiteStorage`: SQLite database with ACID transactions

**Benefits**:
- Backend-agnostic queue logic
- Easy to add new storage backends
- Testable with in-memory implementations

## Communication Patterns

### Enqueue Flow

```mermaid
graph TB
    UserCode[User Code]
    AsyncOmniQ_Facade[AsyncOmniQ<br/>(Façade)]
    AsyncTaskQueue_Queue[AsyncTaskQueue<br/>(Queue)]
    Storage_FileSQLite[Storage<br/>(File/SQLite)]

    UserCode -->|AsyncOmniQ.enqueue| AsyncOmniQ_Facade
    AsyncOmniQ_Facade -->|AsyncTaskQueue.enqueue| AsyncTaskQueue_Queue
    AsyncTaskQueue_Queue -->|Storage.enqueue| Storage_FileSQLite
    Storage_FileSQLite -->|Persist task| Done
```

### Worker Execution Flow

```mermaid
graph TB
    Worker[AsyncWorkerPool<br/>(Worker)]
    Queue1[AsyncTaskQueue<br/>(Queue)]
    Storage1[Storage<br/>(File/SQLite)]
    Queue2[AsyncTaskQueue<br/>(Queue)]
    Worker2[AsyncWorkerPool]
    TaskFunction[Task Function<br/>(User Code)]
    Worker3[AsyncWorkerPool]
    Queue3[AsyncTaskQueue<br/>(Queue)]

    Worker -->|poll_queue| Queue1
    Queue1 -->|Storage.claim_task<br/>[atomic]| Storage1
    Storage1 -->|Return claimed task| Queue2
    Queue2 -->|deserialize task| Worker2
    Worker2 -->|import and execute function| TaskFunction
    TaskFunction -->|return result or raise error| Worker3
    Worker3 -->|serialize result/error<br/>complete_task / fail_task| Queue3
    Queue3 -->|Storage.complete_task / fail_task| Done
```

## Design Principles

### 1. Separation of Concerns

Each component has single responsibility:

- **Façade**: User experience and API design
- **Queue**: Task queue semantics and retry logic
- **Worker**: Task execution and concurrency
- **Storage**: Persistence and data modeling

### 2. Dependency Direction

Dependencies flow downward:

```
Façade → Queue → Storage
Façade → Worker (Worker → Queue → Storage)
```

No upward dependencies (e.g., Storage doesn't depend on Queue).

### 3. Abstract Interfaces

Storage uses abstract base class:

```python
# Queue only knows about BaseStorage
async def __init__(self, storage: BaseStorage): ...

# User chooses implementation
storage = SQLiteStorage("path/to/db")
storage = FileStorage("/path/to/dir")
```

### 4. Clear Ownership

Each concept is owned by one layer:

| Concept | Owned By | Not Owned By |
|----------|-----------|---------------|
| Retry budget | Queue | Worker |
| Concurrency | Worker | Queue |
| Persistence | Storage | Queue, Worker |
| Task lifecycle | Queue | Worker (only transitions) |

## Extensibility

### Adding New Storage Backend

Implement `BaseStorage` interface:

```python
from omniq.storage.base import BaseStorage

class RedisStorage(BaseStorage):
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url)

    async def enqueue(self, task):
        # Implement enqueue logic
        pass

    # Implement other abstract methods...
```

### Custom Retry Policies

Subclass `AsyncTaskQueue`:

```python
from omniq.queue import AsyncTaskQueue

class CustomRetryQueue(AsyncTaskQueue):
    def _should_retry(self, task, attempts):
        # Custom retry logic
        pass

    def _calculate_retry_delay(self, retry_count):
        # Custom delay calculation
        pass
```

## Benefits of This Architecture

### 1. Testability

Each component can be tested independently:

```python
# Test queue without storage
mock_storage = MockStorage()
queue = AsyncTaskQueue(mock_storage)

# Test worker without queue
mock_queue = MockAsyncTaskQueue()
workers = AsyncWorkerPool(mock_queue)
```

### 2. Flexibility

Swap storage backends without changing queue/worker code:

```python
# Development
storage = FileStorage("./dev_data")

# Production
storage = SQLiteStorage("/var/lib/omniq/tasks.db")

# Same queue and worker code works with both
queue = AsyncTaskQueue(storage)
workers = AsyncWorkerPool(queue)
```

### 3. Clear Boundaries

Ownership is explicit and unambiguous:

```python
# Queue owns retry logic
queue._should_retry(task, attempts)  # ✓ Queue's job

# Worker owns execution
workers._execute_task(task)  # ✓ Worker's job

# Storage owns persistence
storage.claim_task(task_id)  # ✓ Storage's job
```

### 4. Maintainability

Changes to one component don't affect others:

```python
# Change retry policy (Queue only)
# No impact on Worker or Storage

# Add new storage backend
# No impact on Queue or Worker
```

## Next Steps

- Read [scheduling model explanation](scheduling.md) for ETA/interval semantics
- Understand [retry model explanation](retry_mechanism.md) for retry budget
- See [storage tradeoffs explanation](storage-tradeoffs.md) for backend comparison

## Summary

- **Façade**: Simplified user API (`AsyncOmniQ` / `OmniQ`)
- **Queue**: Core task queue logic (`AsyncTaskQueue`)
- **Worker**: Task execution pool (`AsyncWorkerPool`)
- **Storage**: Persistence abstraction (`BaseStorage` implementations)
- **Principles**: Separation of concerns, abstract interfaces, clear ownership
- **Benefits**: Testability, flexibility, maintainability

OmniQ's modular architecture provides clean boundaries, independent testing, and easy extensibility while keeping the public API simple for users.
