# Change: Add curated, feature-covering examples

## Why
OmniQ currently has a minimal example set and at least one example/doc path is out of sync with the implemented API surface, making first-time adoption harder than necessary.

This change adds a small, high-signal set of runnable examples that cover the main OmniQ features with minimal overlap and updates documentation to point to them.

## What Changes
- Add a curated examples suite (4 scripts) that is fast, deterministic, and clearly differentiated.
- Add shared example helpers (`examples/tasks.py`) to keep scripts small and to ensure `func_path` resolution works reliably.
- Add `examples/README.md` that indexes examples by “what it demonstrates”.
- Update/replace the existing retry example to be correct and runnable.
- Update `README.md` snippets that reference non-existent worker APIs to match the current implementation (documentation-only).

## Impact
- Affected specs: none (documentation/examples only; no runtime behavior changes intended).
- Affected code:
  - `examples/` (new and updated scripts)
  - `README.md` (snippets + pointers to examples)
  - `docs/` (optional cross-links, if needed)

## Non-Goals
- No new public APIs, storage backends, or behavioral changes to queue/worker semantics.
- No long-running examples, external services, or network calls.

## Example Set (Proposed)
- `examples/01_quickstart_async.py`
  - Enqueue 2 tasks (1 sync + 1 async), run workers, await results.
  - Covers: `AsyncOmniQ`, `Settings`, file backend, args/kwargs, concurrency/polling, `get_result(wait=True)`.
- `examples/02_scheduling_eta_and_interval.py`
  - One delayed task + one interval task, observe scheduling and rescheduling.
  - Covers: `eta`, `interval`, worker polling, interval rescheduling semantics (new task IDs).
- `examples/03_retries_and_task_errors.py`
  - Deterministic “fail N times then succeed” with retries and recorded error/result metadata.
  - Covers: SQLite backend, retry budget/backoff, task error/result metadata.
- `examples/04_sync_api_logging_and_env.py`
  - Configure via env, enqueue from sync code, run sync worker wrapper, show correlation logging.
  - Covers: `Settings.from_env()`, `OmniQ`, `WorkerPool`, `omniq.logging.configure()`, `task_context()` / `bind_task()`.

