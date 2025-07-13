# OmniQ Core Architecture Implementation Prompt

## Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, and distributed processing in their applications with both synchronous and asynchronous interfaces.

---

## Core Design Principles

- **Async First, Sync Wrapped:** The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
- **Separation of Concerns:** Task queue, result storage, and event logging are decoupled and independent.
- **Interface-Driven:** All components implement common interfaces.
- **Serialization Strategy:** Intelligent serialization with `msgspec` and `dill` for task enqueuing/dequeuing.
- **Configuration System:** Centralized, environment-variable-driven configuration with runtime overrides.

---

## Module Architecture Focus

### `omniq.models`
- **Purpose:** Define data structures and business logic.
- **Components:**  
  - `Task`: Serializable task with metadata, dependencies, callbacks, and TTL.
  - `Schedule`: Timing logic (cron, interval, timestamp) with pause/resume capability.
  - `TaskResult`: Execution outcome storage.
  - `TaskEvent`: Event logging data model.
  - `Settings`: Library settings without "OMNIQ_" prefix, overridable by environment variables.
- **Design Decisions:**  
  - Use `msgspec.Struct` for serialization.
  - Support both async and sync callable references.
  - Implement `__hash__` and `__eq__` for dependency tracking.
  - Store task metadata for tracking and monitoring.
  - Define clear result states (pending, running, success, error).
  - Include TTL for automatic task expiration.
  - Support schedule state management (active, paused).
  - Implement settings constants without "OMNIQ_" prefix, overridable by "OMNIQ_" env vars.

### `omniq.serialization`
- **Purpose:** Task and result serialization for storage and retrieval.
- **Components:**  
  - `SerializationDetector`: Type compatibility detection.
  - `MsgspecSerializer`: Primary serializer for compatible types.
  - `DillSerializer`: Fallback serializer for complex objects.
  - `SerializationManager`: Orchestrates serialization strategy.
- **Design Decisions:**  
  - Use `msgspec` as primary serializer for performance.
  - Fall back to `dill` for complex Python objects.
  - Store serialization format with data for proper deserialization.
  - Implement security measures for `dill` deserialization.

### `omniq.queue`
- **Purpose:** Core orchestration and execution logic (not backend implementations).
- **Components:**  
  - `AsyncTaskQueue`: Async core implementation of task queue.
  - `TaskQueue`: Sync wrapper around async implementation.
  - `AsyncScheduler`: Async core implementation of scheduler.
  - `Scheduler`: Sync wrapper around async implementation.
  - `DependencyResolver`: Graph-based dependency management.
  - `RetryManager`: Exponential backoff and failure handling.
  - `TTLManager`: Task expiration and cleanup.
- **Design Decisions:**  
  - Event-driven architecture using asyncio queues.
  - Provide synchronous wrappers for all operations.
  - Graceful shutdown with task completion.
  - Circuit breaker pattern for fault tolerance.
  - Support multiple storage backends (abstract interface only).
  - Implement task TTL enforcement and cleanup.
  - Support schedule pausing and resuming.

### `omniq.workers`
- **Purpose:** Task execution with multiple worker types (base interfaces only).
- **Components:**  
  - `AsyncWorkerPool`: Async core implementation of worker pool.
  - `WorkerPool`: Sync wrapper around async implementation.
  - Worker implementations:  
    - `AsyncWorker` (core), `ThreadWorker`, `ProcessWorker`, `GeventWorker` (all as base implementations).
- **Design Decisions:**  
  - Implement async core functionality first.
  - Create sync wrappers around async implementations.
  - Support multiple worker types for different workloads.
  - Handle both sync and async tasks appropriately.
  - Implement common interface for all worker types.
  - Provide proper resource management and cleanup.
  - Worker selection based on task requirements.
  - Result serialization and storage after task completion.
  - Respect task TTL during execution.

### `omniq.events`
- **Purpose:** Task lifecycle tracking and monitoring (event system interfaces).
- **Components:**  
  - `AsyncEventLogger`: Async core implementation of event logger.
  - `EventLogger`: Sync wrapper around async implementation.
  - `AsyncEventProcessor`: Async core implementation of event processor.
  - `EventProcessor`: Sync wrapper around async implementation.
  - Event types: ENQUEUED, EXECUTING, COMPLETE, ERROR, RETRY, CANCELLED, EXPIRED, SCHEDULE_PAUSED, SCHEDULE_RESUMED.
- **Design Decisions:**  
  - Implement async core functionality first.
  - Create sync wrappers around async implementations.
  - Non-blocking event logging with disable option.
  - Structured logging with metadata.
  - Configurable event retention policies.
  - Event logging automatically disabled when no event storage is configured.
  - Store task events without serialization in SQLite, PostgreSQL, or as JSON files.
  - Track task TTL events and schedule state changes.
  - Clear separation between library logging and task event logging.

### `omniq.config`
- **Purpose:** Centralized configuration management.
- **Components:**  
  - `Settings`: Library settings constants without "OMNIQ_" prefix.
  - `EnvConfig`: Environment variable configuration with "OMNIQ_" prefix.
  - `ConfigProvider`: Configuration loading and validation.
  - `LoggingConfig`: Logging configuration.
- **Design Decisions:**  
  - Define settings constants without "OMNIQ_" prefix, overridable by "OMNIQ_" env vars.
  - Environment variables as primary configuration method.
  - Type conversion and validation for config values.
  - Component-specific configuration sections.
  - Runtime configuration changes.
  - Independent configuration of task queue, result storage, and event storage.
  - Configuration for default task TTL.
  - Separate configuration for library logging and task event logging.

### `omniq.core.py`
- **Purpose:** Main `OmniQ` class that orchestrates all components.
- **Responsibilities:**  
  - Compose and manage the lifecycle of the queue, workers, event system, and configuration.
  - Provide a unified interface for task submission, scheduling, and monitoring.
  - Expose both async and sync APIs for all core operations.

---

## Development Guidelines

### Async First, Sync Wrapped Implementation Guidelines

- Implement all core functionality using async/await.
- Create synchronous wrappers using `anyio.from_thread.run()` or event loops.
- Use `Async` prefix for core async classes, no prefix for sync wrappers. Sync wrapper methods should have a `_sync` suffix.
- Implement both `__aenter__`/`__aexit__` and `__enter__`/`__exit__` context managers.
- Preserve exception context across sync/async boundaries.
- Ensure proper cleanup in both sync and async contexts.

**Example Pattern:**
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
        return anyio.from_thread.run(self._async_queue.enqueue(task))

    def __enter__(self):
        anyio.from_thread.run(self._async_queue.__aenter__())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        anyio.from_thread.run(self._async_queue.__aexit__(exc_type, exc_val, exc_tb))
```

---

### Settings and Environment Variables

- Define settings constants without "OMNIQ_" prefix.
- Override settings with environment variables with "OMNIQ_" prefix.
- Example: `BASE_DIR` in settings, `OMNIQ_BASE_DIR` as environment variable.

**Supported Environment Variables:**
- `OMNIQ_LOG_LEVEL`: Set library logging level (DEBUG, INFO, WARNING, ERROR, DISABLED)
- `OMNIQ_DISABLE_LOGGING`: Disable all library logging when set to "1" or "true"
- `OMNIQ_TASK_QUEUE_TYPE`: Queue backend for tasks (file, memory, sqlite, postgres, redis, nats)
- `OMNIQ_TASK_QUEUE_URL`: Connection string for task queue backend
- `OMNIQ_RESULT_STORAGE_TYPE`: Storage backend for results (file, memory, sqlite, postgres, redis, nats)
- `OMNIQ_RESULT_STORAGE_URL`: Connection string for result storage backend
- `OMNIQ_EVENT_STORAGE_TYPE`: Storage backend for events (sqlite, postgres, file)
- `OMNIQ_EVENT_STORAGE_URL`: Connection string for event storage backend
- `OMNIQ_FSSPEC_URI`: URI for fsspec (e.g., "file:///path", "s3://bucket", "memory://")
- `OMNIQ_DEFAULT_WORKER`: Default worker type (async, thread, process, gevent)
- `OMNIQ_MAX_WORKERS`: Maximum number of workers
- `OMNIQ_THREAD_WORKERS`: Thread pool size
- `OMNIQ_PROCESS_WORKERS`: Process pool size
- `OMNIQ_GEVENT_WORKERS`: Gevent pool size
- `OMNIQ_TASK_TIMEOUT`: Default task execution timeout in seconds
- `OMNIQ_TASK_TTL`: Default time-to-live for tasks in seconds
- `OMNIQ_RETRY_ATTEMPTS`: Default number of retry attempts
- `OMNIQ_RETRY_DELAY`: Default delay between retries in seconds
- `OMNIQ_RESULT_TTL`: Default time-to-live for task results in seconds
- `OMNIQ_COMPONENT_LOG_LEVELS`: JSON string with per-component logging levels

---

## Scope

This task is to design and implement the core architecture of OmniQ, including:
- Base interfaces, abstract classes, and core models.
- Serialization logic and strategy.
- Central configuration system.
- The main `OmniQ` class orchestrating all components.

**Do NOT implement specific storage backends (SQLite, File, Postgres, Redis, NATS) or detailed worker pool implementations.** These will be addressed in separate subtasks.

---

## Completion

Signal completion by using the `attempt_completion` tool with a summary of the created prompt.