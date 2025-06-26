Of course. I have received the second project plan and will now perform the merge and apply the requested modifications.

Here is the consolidated project plan for **OmniQ**. It combines the details from both documents into a single, comprehensive plan, removes redundancy, and incorporates your specified technical changes regarding `fsspec` and sync/async compatibility.

-----

# **Project Plan: OmniQ - A Flexible Task Queue Library for Python**

## 1\. Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible and robust architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, dependencies, and distributed processing in their applications, with first-class support for both synchronous and asynchronous programming paradigms.

### **Key Features**

  * **Dual API:** First-class support for both synchronous (for frameworks like Flask, Django) and asynchronous (for frameworks like FastAPI, Litestar) operations, including context managers.
  * **Multiple Storage Backends:** Pluggable backends for tasks, results, and events, including File System (`fsspec`), In-Memory, SQLite, PostgreSQL, Redis, and NATS.
  * **Flexible Worker Types:** A variety of workers to suit different workloads: `Async`, `Thread Pool`, `Process Pool`, and `Gevent`.
  * **Unified File System Support via `fsspec`:** Supports numerous storage locations (local, in-memory, S3, Azure Blob, GCS) through a single interface.
  * **Advanced Task Management:**
      * Task scheduling with cron and interval patterns.
      * Support for pausing and resuming scheduled tasks.
      * Task dependencies and workflow management via dependency graphs.
      * Configurable Time-to-Live (TTL) for tasks and results for automatic cleanup.
  * **Decoupled Components:** Independent configuration for task queues, result storage, and event storage.
  * **Rich Event System:** Detailed lifecycle event logging for monitoring and auditing, with the ability to disable it or use SQL/File backends.
  * **Resilience and Fault Tolerance:** Built-in support for retries with exponential backoff, dead-letter queues, and circuit breakers.
  * **Flexible Configuration:** Configure the library via code, objects, dictionaries, YAML files, or environment variables.
  * **Web Dashboard:** A web interface built with Litestar for real-time monitoring, management, and visualization of tasks, schedules, and workers.

## 2\. Architecture Overview

### **Core Design Principles**

  * **Async First, Sync Wrapped:** The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
  * **Separation of Concerns**: Task queue, result storage, and event logging are decoupled, allowing them to be configured and scaled independently.
  * **Interface-Driven**: All components (storage, workers, serializers) adhere to a common interface, enabling easy extension and replacement.
  * **Intelligent Serialization**: A dual strategy using `msgspec` for performance and `dill` for compatibility ensures that any Python object can be serialized.

### **System Architecture Diagram**

```mermaid
flowchart TD
    subgraph "Application Layer"
        Client[Client Application]
    end

    subgraph "OmniQ Library"
        A[OmniQ Dual API<br>(Sync & Async Facades)] --> B(Task Queue)
        A --> C(Result Storage)
        A --> D(Event Storage)
        A --> E(Worker Pool)
        A --> S(Scheduler)

        subgraph "Storage Layer (fsspec, SQL, Cache, Messaging)"
            B --> B1[fsspec Queue<br>(File, S3, GCS, Azure)]
            B --> B2[Memory Queue]
            B --> B3[SQLite Queue]
            B --> B4[PostgreSQL Queue]
            B --> B5[Redis Queue]
            B --> B6[NATS Queue]

            C --> C1[fsspec Storage]
            C --> C2[Memory Storage]
            C --> C3[SQLite Storage]
            C --> C4[PostgreSQL Storage]
            C --> C5[Redis Storage]
            C --> C6[NATS Storage]

            D --> D1[SQLite Storage]
            D --> D2[PostgreSQL Storage]
            D --> D3[fsspec Storage<br>(JSON Files)]
        end

        subgraph "Execution Layer"
            E --> E1[Async Worker]
            E --> E2[Thread Pool Worker]
            E --> E3[Process Pool Worker]
            E --> E4[Gevent Pool Worker]
        end
    end

    Client --> A
```

### **Data Flow**

```mermaid
sequenceDiagram
    participant Client
    participant OmniQ
    participant Queue as Task Queue
    participant Worker
    participant ResultStore as Result Storage
    participant EventStore as Event Storage

    Client->>OmniQ: enqueue(task)
    OmniQ->>Queue: enqueue(serialized_task)
    Queue-->>OmniQ: task_id
    OmniQ-->>Client: task_id

    Worker->>Queue: dequeue(queues=["q1", "q2"])
    Queue-->>Worker: serialized_task
    Worker->>EventStore: log(EXECUTING)
    Worker->>Worker: execute(deserialized_task)
    Worker->>ResultStore: store(serialized_result)
    Worker->>EventStore: log(COMPLETED)

    Client->>OmniQ: get_result(task_id)
    OmniQ->>ResultStore: get(task_id)
    ResultStore-->>OmniQ: serialized_result
    OmniQ-->>Client: deserialized_result
```

## 3\. Project Structure

```
omniq/
├── pyproject.toml          # uv project configuration
├── uv.lock                 # uv lock file
├── README.md
├── src/
│   └── omniq/              # Source code directory
│       ├── __init__.py
│       ├── core.py         # Core OmniQ implementation & facades
│       ├── models/         # Data models (Task, Schedule, etc.) & configuration
│       ├── storage/        # Storage backend implementations
│       ├── serialization/  # Serialization utilities
│       ├── queue/          # Task queue engine and logic
│       ├── workers/        # Worker implementations
│       ├── events/         # Event system
│       ├── dashboard/      # Web dashboard
│       └── config/         # Configuration loading and management
├── tests/
│   ├── __init__.py
│   ├── test_models/
│   ├── test_storage/
│   ├── test_serialization/
│   ├── test_queue/
│   ├── test_workers/
│   └── test_events/
└── docs/
    ├── index.md
    └── ...                 # Other documentation files
```

## 4\. Key Technical Decisions

  * **Dual Interface Strategy:**

      * The core internal logic is implemented using `async`/`await` for high performance and concurrency.
      * A synchronous API is provided as a wrapper layer for use in traditional blocking applications.
      * All public-facing classes that manage resources (like storage connections) will implement both synchronous (`__enter__`/`__exit__`) and asynchronous (`__aenter__`/`__aexit__`) context managers.

  * **Storage Strategy with `fsspec`:**

      * The `obstore` dependency is replaced with `fsspec`. This provides a robust and widely-used abstraction for file-based storage. When initializing a filesystem for a local path, `fsspec.implementations.dir.DirFileSystem` should be used.
      * This change makes `s3fs`, `gcsfs`, and `adlfs` **optional dependencies**, which users can install to get S3, Google Cloud, and Azure support respectively.
      * Storage for tasks, results, and events can be configured independently (e.g., tasks in Redis, results in PostgreSQL, events in local JSON files).

  * **Serialization Strategy:**

      * A dual approach provides both performance and flexibility.
      * **`msgspec`** is the primary serializer for high-performance serialization of compatible data types.
      * **`dill`** is used as a fallback for serializing more complex Python objects like functions and classes.
      * The serialization format is stored alongside the data to ensure correct deserialization. Security measures (like signature verification) will be considered for `dill`.

  * **Worker Strategy:**

      * All worker types share a common interface.
      * `AsyncWorker` runs `async` tasks natively and `sync` tasks in a thread pool.
      * `ThreadPoolWorker`, `ProcessPoolWorker`, and `GeventPoolWorker` run `sync` tasks in their respective pools and `async` tasks within a managed event loop.

## 5\. Implementation Plan

### **Phase 1: Foundation (Weeks 1-2)**

1.  **Project Setup & Configuration:**
      * Initialize project structure with `uv init`. Configure `ruff`, `mypy`, and `pytest`.
      * Implement the configuration system (`omniq.config`), allowing overrides from environment variables (e.g., `OMNIQ_...`).
      * Establish a clear separation between library logging and the task event system.
2.  **Core Models (`omniq.models`):**
      * Implement `Task`, `Schedule`, `TaskResult`, `TaskEvent` using `msgspec.Struct`.
      * Include fields for TTL, dependencies, and both sync/async callable references.
3.  **Serialization Layer (`omniq.serialization`):**
      * Implement the dual serializer manager that detects types and chooses between `msgspec` and `dill`.
4.  **Storage Interfaces (`omniq.storage`):**
      * Define the base classes (`BaseTaskQueue`, `BaseResultStorage`, `BaseEventStorage`) with both `sync` and `async` abstract methods and context manager support.
5.  **File & Memory Storage (using `fsspec`):**
      * Implement `FileTaskQueue`, `FileResultStorage`, and `FileEventStorage` (using JSON) on top of the `fsspec` API.
      * Implement `MemoryTaskQueue` and `MemoryResultStorage`.
      * Ensure implementations correctly handle various `fsspec`-supported URLs (e.g., `file://`, `memory://`, `s3://`).
6.  **Core `OmniQ` Interface (`omniq.core`):**
      * Implement the main `OmniQ` class, providing the unified sync and async facades for all library functions.

### **Phase 2: Worker Implementation (Week 3)**

7.  **Worker Interface & Pool:**
      * Define a common `BaseWorker` interface.
      * Implement a `WorkerPool` for managing worker lifecycle, distribution, and health checks.
8.  **Worker Implementations (`omniq.workers`):**
      * Implement all four worker types: `AsyncWorker`, `ThreadPoolWorker`, `ProcessPoolWorker`, and `GeventPoolWorker`, ensuring each can handle both sync and async tasks correctly.

### **Phase 3: SQL Storage & Core Features (Week 4)**

9.  **SQLite Storage:**
      * Implement `SQLiteTaskQueue`, `SQLiteResultStorage`, and `SQLiteEventStorage`.
      * Include a task locking mechanism to prevent duplicate processing.
10. **Task Scheduling:**
      * Implement the scheduler to handle cron/interval tasks, including persistence and pause/resume functionality.
11. **Task Dependencies:**
      * Build the dependency graph resolver to manage task execution order and handle callbacks.

### **Phase 4: Distributed Storage (Week 5)**

12. **PostgreSQL Storage:**
      * Implement async-native `PostgresTaskQueue`, `PostgresResultStorage`, and `PostgresEventStorage` using a library like `asyncpg`.
      * Implement robust task locking using `FOR UPDATE SKIP LOCKED`.
13. **Redis Storage:**
      * Implement `RedisTaskQueue` and `RedisResultStorage` using an async Redis client.
      * Use Redis atomic operations for locking and pub/sub for potential real-time notifications.
14. **NATS Storage:**
      * Implement `NATSTaskQueue` and `NATSResultStorage` using NATS JetStream for persistence and KV/Object stores.
      * Use NATS queue groups to ensure tasks are consumed by only one worker.

### **Phase 5: Resilience & Features (Week 6)**

15. **Retry and Fault Tolerance:**
      * Implement retry logic with exponential backoff, a dead-letter queue for failed tasks, and a circuit breaker pattern for storage connections.
16. **Advanced Features:**
      * Finalize implementation for task TTL, result expiration, and the callback system.

### **Phase 6: Dashboard & Finalization (Week 7)**

17. **Web Dashboard (`omniq.dashboard`):**
      * Develop a `Litestar` application with real-time monitoring (SSE), schedule management, and metrics visualization using `htpy` and `datastar-py`.
18. **Testing and Documentation:**
      * Write a comprehensive test suite covering all backends, worker types, and both sync/async interfaces.
      * Create API documentation, usage examples, and deployment guides.

## 6\. Development Guidelines

  * **Dependency Management:** All project dependencies will be managed using `uv`.
  * **Sync/Async Implementation:**
      * Core logic will be `async`.
      * Sync wrappers will manage their own event loop or use a running one where appropriate.
      * Ensure resources are properly managed in both sync and async context managers (`__enter__`/`__exit__` and `__aenter__`/`__aexit__`).
  * **Configuration via Environment Variables:** The library will be configurable via environment variables prefixed with `OMNIQ_`, such as:
      * `OMNIQ_TASK_QUEUE_URL`: e.g., `redis://localhost:6379/0` or `fsspec+s3://my-bucket/tasks`
      * `OMNIQ_RESULT_STORAGE_URL`: e.g., `postgresql+asyncpg://user:pass@host/db`
      * `OMNIQ_EVENT_STORAGE_URL`: e.g., `sqlite:///path/to/events.db`
      * `OMNIQ_DEFAULT_WORKER`: `async`, `thread`, `process`, or `gevent`
      * `OMNIQ_MAX_WORKERS`: e.g., `10`
  * **Task Locking:** Every queue backend must implement a robust locking mechanism to prevent a single task from being executed by multiple workers simultaneously.
  * **External Library Usage:** When implementing features with unfamiliar libraries (`fsspec`, `msgspec`, `gevent`, `litestar`, etc.), developers should use `context7` and `deepwiki` MCPs to ask targeted questions and find best-practice implementation patterns.