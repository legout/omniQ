# OmniQ v1 Product Requirements

## Overview

OmniQ is an async-first, lightweight Python task queue for local and simple distributed workloads. v1 focuses on a small, opinionated core with a clean API and minimal dependencies, while leaving clear extension points for advanced features later.

## Target Users & Use Cases

- Python developers who:
  - Want a simple job queue embedded in their app (background tasks, periodic jobs).
  - Prefer modern async APIs but still need a sync-friendly wrapper.
  - Don’t want to adopt a heavyweight system (Celery, distributed brokers) for small/medium workloads.
- Typical use cases:
  - Offloading slow I/O (HTTP calls, DB queries) to background workers.
  - Lightweight scheduled jobs (run once later, or at a fixed interval).
  - Batch processing tasks driven by application code.

## v1 Goals

- Async-first core with a simple sync wrapper.
- Minimal but solid feature set:
  - Enqueue tasks (sync or async callables) with arguments.
  - Dequeue and execute tasks via a worker pool.
  - Result storage and retrieval.
  - Basic retry and timeout semantics.
  - Simple scheduling (`eta`/delay, optional fixed interval).
- Only 1–2 storage backends:
  - File-based queue/result storage (local filesystem, optionally in-memory via fsspec).
  - SQLite-based queue/result storage.
- Simple configuration:
  - Code-first configuration (Python API) with a small set of env var overrides.
- Clear seams for future expansion (backends, workers, event system) without breaking v1 users.

## Non-Goals / Deferred Features

The following are explicitly out of scope for v1 and reserved for later versions:

- Additional backends: PostgreSQL, Redis, NATS and cloud storage variants (S3, Azure, GCP) as first-class backends.
- Multiple worker implementations: dedicated gevent worker, process-pool worker, etc.
- Advanced event system: persistent event stores, event processors, event queries.
- Complex scheduling:
  - Cron expressions, advanced calendar rules.
  - Workflow/DAG task dependencies.
- Full-blown configuration framework:
  - Multiple config formats, deep config hierarchies, runtime reconfiguration.
- Multi-tenant/security-hardened serialization for untrusted or multi-tenant workloads. v1 includes an explicit unsafe mode using `cloudpickle` but does not attempt to make it safe for untrusted inputs.

## User Stories (v1)

As a developer, I can:

- Enqueue a Python function with arguments and get a task ID.
- Start a worker pool that processes queued tasks using async concurrency.
- Retrieve the result of a completed task by task ID.
- Configure OmniQ via straightforward Python constructors and a few env vars.
- Schedule a task to run later or repeatedly at a fixed interval.
- Run the same codebase in dev (file-based storage) and staging (SQLite) with minimal changes.

## Success Criteria

- API can be explained in a single page of docs with a few examples.
- Core implementation is small enough that a new contributor can understand it in less than a day.
- v1 passes a test suite covering:
  - Task lifecycle, retries, failures.
  - File and SQLite backends.
  - Basic scheduling.
- Adding a new backend or worker type later does not require major refactors to v1 code.

---

# OmniQ v1 Technical Spec

## 1. Architecture Overview

- **Async-first core**: core types and operations are async.
- **Sync wrapper**: thin sync interface around the async core for users not running an event loop.
- **Storage abstraction**: a small, focused interface for queue/result storage with two v1 implementations (file, SQLite).
- **Worker model**: one worker-pool type based on asyncio tasks, plus a sync wrapper.
- **Config & serialization**: small config layer with env overrides; msgspec-based serialization by default, with an opt-in unsafe mode using `cloudpickle`.

High-level objects:

- `AsyncOmniQ` / `OmniQ` (interface).
- `AsyncTaskQueue` (queue engine using storage).
- `AsyncWorkerPool` (worker loop).
- `Task`, `TaskResult`, `TaskStatus`, `Schedule` (models).
- `BaseStorage`, `FileStorage`, `SQLiteStorage` (queue+result storage).
- `Settings` / `load_settings()` for configuration.
- `Serializer` abstraction with a msgspec implementation (default) and a cloudpickle-based unsafe implementation.

## 2. Modules & Structure

Minimal structure (v1):

- `omniq/__init__.py`
  - Public re-exports: `AsyncOmniQ`, `OmniQ`, key models.
- `omniq/core.py`
  - `AsyncOmniQ`, `OmniQ` sync wrapper, high-level API.
- `omniq/models.py`
  - `Task`, `TaskResult`, `TaskStatus`, `TaskError`, `Schedule`.
- `omniq/storage/base.py`
  - `BaseStorage` (queue+result interface).
- `omniq/storage/file.py`
  - `FileStorage` using local filesystem (optionally `fsspec.LocalFileSystem` / `MemoryFileSystem`).
- `omniq/storage/sqlite.py`
  - `SQLiteStorage` using `aiosqlite`.
- `omniq/queue.py`
  - `AsyncTaskQueue` (enqueue/dequeue logic, scheduling, retries).
- `omniq/worker.py`
  - `AsyncWorkerPool`, `WorkerPool` (sync wrapper).
- `omniq/config.py`
  - `Settings` dataclass, env overrides.
- `omniq/serialization.py`
  - `MsgspecSerializer`, `Serializer` protocol.

This is intentionally smaller than the original multi-package architecture; an extended layout can be introduced once advanced features land.

## 3. Core Models

### Task

Fields:

- `id: str`
- `func_path: str` (module:callable dotted path).
- `args: list[Any]`, `kwargs: dict[str, Any]` (serialized via the configured serializer; msgspec by default, cloudpickle in unsafe mode).
- `eta: datetime | None` (earliest execution time).
- `interval: timedelta | None` (for fixed-interval repetition; optional).
- `max_retries: int` (default from settings).
- `timeout: float | None` (seconds; default from settings).
- `created_at`, `updated_at`.

No DAG/dependency fields in v1.

### TaskStatus

Enum values:

- `PENDING`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `RETRYING`
- `CANCELLED`

### TaskResult

Fields:

- `task_id`
- `status`
- `result` (serialized)
- `error` (string/struct)
- `finished_at`
- Optional `attempts`, `last_attempt_at`

### Schedule

For v1: simple `eta` plus optional `interval`. No cron expressions yet.

## 4. Storage Abstraction

`BaseStorage` responsibilities (async-only API):

- Queue-related:
  - `async enqueue(task: Task) -> str`
  - `async dequeue(now: datetime) -> Task | None`  
    Returns the next due task (`eta <= now`), with simple FIFO or priority by `eta`.
  - `async mark_running(task_id: str) -> None`
  - `async mark_done(task_id: str, result: TaskResult) -> None`
  - `async mark_failed(task_id: str, error: TaskError, will_retry: bool) -> None`
- Result-related:
  - `async get_result(task_id: str) -> TaskResult | None`
  - `async purge_results(older_than: datetime) -> int` (for TTL cleanup).
- Optional:
  - `async reschedule(task_id: str, new_eta: datetime) -> None` for retries or interval tasks.

### v1 Backends

#### FileStorage

- Directory-based layout:
  - `queue/` (pending tasks, possibly sharded by state).
  - `results/`.
- Uses msgspec to serialize `Task` and `TaskResult` to files.
- Simple file-based locking or atomic operations (e.g., `os.rename`) for `dequeue`.

#### SQLiteStorage

- Single DB (file path or `:memory:`) with tables:
  - `tasks` (id, func_path, args, kwargs, eta, status, attempts, max_retries, timeout, created_at, updated_at, interval, etc.).
  - `results` (task_id, status, result, error, finished_at, attempts).
- Use indexes on `eta` and `status` for efficient `dequeue`.

No separate event storage in v1, beyond what’s needed for `TaskResult`.

## 5. Worker Model

### AsyncWorkerPool

Config:

- `concurrency: int` (number of concurrent tasks).
- `poll_interval: float` (seconds between queue polls when idle).

Behavior:

- Background loop:
  - Poll storage for due tasks (`dequeue(now)`).
  - Spawn `asyncio` tasks to execute them, up to `concurrency`.
  - On completion, store result, handle retries based on `max_retries` and error.
- Handles both sync and async callables:
  - If callable is async: `await func(*args, **kwargs)`.
  - If callable is sync: run in thread executor.
- Retry strategy:
  - Simple exponential backoff with jitter (configurable base delay).

### WorkerPool (sync wrapper)

- Starts/stops an `AsyncWorkerPool` in a dedicated thread, exposes `start()` and `stop()` as blocking calls.

## 6. Public API (v1)

High-level:

- `AsyncOmniQ`
  - `__init__(storage: BaseStorage, *, settings: Settings | None = None)`
  - `async enqueue(func: Callable | str, *args, eta=None, interval=None, **kwargs) -> str`
  - `async get_result(task_id: str, *, wait: bool = False, timeout: float | None = None) -> TaskResult | None`
  - `async worker(concurrency: int = 1, poll_interval: float = 1.0) -> AsyncWorkerPool`
- `OmniQ` (sync wrapper)
  - Mirrors methods with blocking semantics, running async via anyio or a similar helper.

Minimal example (conceptual):

```python
oq = OmniQ.from_env()  # or explicit config

task_id = oq.enqueue(send_email, to="user@example.com")
result = oq.get_result(task_id, wait=True, timeout=30)
```

## 7. Configuration

### Settings

`Settings` (dataclass or msgspec.Struct):

- `backend: Literal["file", "sqlite"]`
- `database_url: str | None` (for SQLite).
- `base_dir: str | None` (for file storage).
- `default_timeout: float`
- `default_max_retries: int`
- `result_ttl_seconds: int`
 - `serializer: Literal["msgspec", "cloudpickle"]` (defaults to `"msgspec"`).

### Environment Variables

`from_env()` reads a small set of env vars:

- `OMNIQ_BACKEND` (`file` / `sqlite`).
- `OMNIQ_DB_URL` (e.g., `sqlite:///omniq.db` or path).
- `OMNIQ_BASE_DIR`.
- `OMNIQ_DEFAULT_TIMEOUT`.
- `OMNIQ_DEFAULT_MAX_RETRIES`.
- `OMNIQ_RESULT_TTL`.
 - `OMNIQ_SERIALIZER` (`"msgspec"` or `"cloudpickle"`, defaults to `"msgspec"`).

No YAML/dict/object config machinery in v1; those can be added later via a `ConfigProvider`.

## 8. Serialization

- v1 exposes two serialization modes via a `Serializer` abstraction:
  - **Safe mode (default)** using msgspec:
    - Tasks store `func_path` (string) and `args` / `kwargs` encoded via msgspec.
    - Enqueue will fail with a clear `SerializationError` if arguments cannot be encoded.
    - Suitable for most users and for long-term persistence; recommended unless you fully control the environment.
  - **Unsafe mode** using `cloudpickle`:
    - Tasks store `func_path` plus `args` / `kwargs` serialized with `cloudpickle` (and results likewise).
    - Allows arbitrary Python objects in arguments and results (including custom classes, closures, instances, etc.).
    - Only appropriate for fully trusted, non-multi-tenant deployments; not safe for untrusted input or strict cross-version compatibility.
- `MsgspecSerializer` and `CloudpickleSerializer` implement the `Serializer` protocol.
- The active serializer is selected via settings / environment (e.g., `serializer="msgspec"` or `serializer="cloudpickle"`).

## 9. Scheduling & Retries

### Scheduling

- Immediate tasks: no `eta`.
- Delayed tasks: `eta > now`.
- Optional fixed-interval tasks:
  - On success, if `interval` is set, the worker reschedules the task by creating a new `eta`.
- No cron expressions in v1; cron-based schedules are a future feature.

### Retries

- `max_retries` per task; default from settings.
- Backoff: `delay = base * (2 ** attempts)` plus small jitter.
- After exceeding retries, task is marked `FAILED`.

## 10. Logging & Events (v1)

### Logging

- Standard Python logging for library internals (queue operations, worker lifecycle, errors).
- Log level controlled via `OMNIQ_LOG_LEVEL` env var (INFO/DEBUG/WARNING/ERROR).

### Event System

- No dedicated event storage or event query API in v1.
- Future-compatible: task state changes are localized in storage and logging, so later an event pipeline can hook in without breaking APIs.

## 11. Extensibility Hooks (for Future Features)

- `BaseStorage` interface:
  - Designed so adding `RedisStorage`, `PostgresStorage`, `NATSStorage` later is straightforward.
- `Serializer` protocol:
  - Allows plugging in additional serializers later (e.g., dill-based or other custom implementations) beyond the built-in msgspec and cloudpickle serializers.
- Worker strategy:
  - `AsyncWorkerPool` can later be complemented by specialized workers (process pool, gevent) that re-use the same queue/storage APIs.
- Events:
  - Future `EventLogger` or `EventStore` can subscribe to task lifecycle changes at a limited set of well-defined points (enqueue, start, finish, retry, fail).
