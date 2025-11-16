## Overview
This change introduces the `BaseStorage` abstraction and a file-backed implementation. Both are central cross-cutting components used by the queue engine and worker pool, and they involve concurrency and durability tradeoffs that benefit from an explicit design.

The goals are:
- Keep the storage interface small and stable for v1.
- Support safe enqueue/dequeue semantics with minimal locking.
- Make it easy to add future backends (SQLite, Redis, Postgres, cloud) without changing the interface.

## BaseStorage Interface
- Location: `src/omniq/storage/base.py`
- Core types: `Task`, `TaskResult`, `TaskStatus` from `src/omniq/models.py`.

### Interface Design
- Async-only: all methods are `async` to align with the async-first core.
- Methods:
  - `enqueue(task: Task) -> str`
  - `dequeue(now: datetime) -> Task | None`
  - `mark_running(task_id: str) -> None`
  - `mark_done(task_id: str, result: TaskResult) -> None`
  - `mark_failed(task_id: str, error: TaskError, will_retry: bool) -> None`
  - `get_result(task_id: str) -> TaskResult | None`
  - `purge_results(older_than: datetime) -> int`
  - `reschedule(task_id: str, new_eta: datetime) -> None` (optional, backend may raise `NotImplementedError` if unsupported).

### Ordering and Visibility
- `dequeue(now)` returns at most one task with `eta <= now`.
- Backends SHOULD:
  - Prefer the earliest `eta`.
  - Use FIFO ordering for tasks with the same `eta`, when practical.
- Once a task is returned from `dequeue`, it MUST NOT be returned again unless explicitly rescheduled.

### Error Semantics
- `mark_failed(..., will_retry=True)` is used when the worker intends to retry:
  - Storage marks status as `RETRYING` but does not reschedule; the queue/worker is responsible for computing and setting a new `eta` (via `reschedule` or a subsequent `enqueue`-style operation).
- `mark_failed(..., will_retry=False)` sets status to `FAILED` and records final error details.

## FileStorage Layout and Naming
- Location: `src/omniq/storage/file.py`
- Configuration:
  - Base directory from settings (e.g., `Settings.base_dir`).
  - Two subdirectories:
    - `<base>/queue/` for task files.
    - `<base>/results/` for result files.

### File Naming
- Task files:
  - Name: `<task-id>.task` under `queue/`.
  - Contents: serialized `Task` using the active `Serializer`.
- Result files:
  - Name: `<task-id>.result` under `results/`.
  - Contents: serialized `TaskResult`.

### Task Lifecycle in Files
- Enqueue:
  - Write a temporary file (e.g., `<task-id>.task.tmp`) then atomically rename to `<task-id>.task` to avoid partial writes.
- Dequeue:
  - Scan `queue/` for due tasks:
    - Deserialize candidates and filter by `eta <= now`.
    - Claim a task by renaming:
      - `<base>/queue/<task-id>.task` → `<base>/queue/<task-id>.running`
    - The `.running` extension indicates that the task is claimed by some worker.
- mark_running:
  - Optional for `FileStorage` if rename on dequeue already implies "running".
  - Implementation MAY update metadata or be a no-op.
- mark_done / mark_failed:
  - Persist a `TaskResult` file under `results/`.
  - Remove or rename the `queue/` file:
    - `<task-id>.running` → `<task-id>.done` (or delete), depending on how much history we want kept in the queue directory.

## Concurrency and Atomicity

### Atomic Dequeue Strategy
- Use `os.rename` as the primary atomic operation:
  - Only one process should succeed in renaming `<task-id>.task` to `<task-id>.running`.
  - If a worker loses the race, `os.rename` fails and the worker picks another task or returns `None`.
- Avoid per-task locks or external lock files in v1 to keep implementation small.

### Multi-Process Access
- Assumptions:
  - All workers share a local filesystem with POSIX-like atomic rename semantics.
  - We do not attempt to support network filesystems with weaker guarantees in v1.
- Failure Modes:
  - If a worker crashes after renaming to `.running` but before recording a result:
    - A future enhancement could include a "stale running task" recovery mechanism.
    - v1 may leave this case as undefined behavior or require manual cleanup.

## Serializer Integration
- Storage is serializer-agnostic:
  - It receives concrete `Task` / `TaskResult` instances and a `Serializer` instance (injected via configuration).
  - Responsibilities:
    - Call `serializer.encode_task(task)` / `serializer.decode_task(bytes)` (names to be finalized in `serialization.py`).
    - Store raw bytes in files; storage does not inspect the structured payload beyond metadata already in the models.
- This keeps `BaseStorage` reusable for both msgspec and cloudpickle modes.

## Extensibility Considerations
- The same `BaseStorage` interface is intended for:
  - SQLite (`SQLiteStorage`).
  - Future distributed backends (Redis, Postgres, NATS, S3, etc.).
- File-specific choices (directory names, extensions) are implementation details and not part of the interface contract.
- Backends may add internal metadata (e.g., attempt counters, last heartbeat) but MUST respect the core models defined in the task queue change.

