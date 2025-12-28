# Change: Fix retry/state-machine consistency across queue and storages

## Why
Retry handling is currently inconsistent across `AsyncTaskQueue` and storage backends, causing incorrect state transitions and a hard failure for FileStorage retries. This also leads to inconsistent attempt counting and duplicated “mark running” behavior.

## What Changes
- Make retry flow consistent with the simplified status machine (`PENDING/RUNNING/SUCCESS/FAILED/CANCELLED`).
- Define a single, consistent contract between queue and storage for:
  - when a task becomes `RUNNING`
  - how attempts are counted
  - how a retryable failure is recorded vs rescheduled
- Fix FileStorage retry behavior so retryable failures do not raise `NotFoundError`.
- Remove debug `print()` usage in core retry paths (**non-functional** logging should go through the logging system).

## Impact
- Affected specs: `task-queue-core`, `task-storage-core`, `task-storage-file`
- Affected code (expected): `src/omniq/queue.py`, `src/omniq/models.py`, `src/omniq/storage/base.py`, `src/omniq/storage/file.py`, `src/omniq/storage/sqlite.py`
- Behavior: retry and attempt semantics become predictable and consistent across backends.
- Risk: Medium (touches core lifecycle behavior); mitigated by adding deterministic tests for retry across file + sqlite backends.

