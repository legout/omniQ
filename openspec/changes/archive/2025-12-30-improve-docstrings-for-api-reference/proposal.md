# Change: Improve docstrings for mkdocstrings API reference

## Why
Current docstrings are usable for mkdocstrings but produce suboptimal API documentation. Critical gaps exist:
- Core data models (`Task`, `TaskResult`, `Schedule` TypedDicts) have no documentation
- `Settings.__init__` and `BackendType` enum lack parameter descriptions
- Public APIs have minimal or no usage examples
- Storage backends and logging utilities have sparse `Args:`/`Raises:` sections

This change improves docstrings in a focused, high-impact manner to ensure mkdocstrings generates high-quality API reference documentation.

## What Changes
### Priority 1: Critical Missing Docstrings (TypedDicts and Enums)
- Add comprehensive docstrings to `Schedule`, `Task`, `TaskResult` TypedDicts in `models.py` with full field documentation
- Add docstring to `BackendType` enum explaining backend options
- Add complete docstring to `Settings.__init__` with Args, Raises, and Example sections

### Priority 2: Add Examples to Public APIs (Façade and Power-User)
- Add usage examples to `AsyncOmniQ.enqueue()` method in `core.py`
- Add usage examples to `AsyncOmniQ.get_result()` method in `core.py`
- Add usage examples to `AsyncOmniQ.worker()` method in `core.py`
- Add usage example to `Settings.from_env()` classmethod in `config.py`
- Add usage examples to `AsyncTaskQueue.enqueue()` in `queue.py`
- Add usage examples to `AsyncTaskQueue.dequeue()` in `queue.py`
- Add usage examples to `AsyncTaskQueue.complete_task()` in `queue.py`
- Add usage examples to `AsyncTaskQueue.fail_task()` in `queue.py`
- Add usage examples to `AsyncWorkerPool` initialization and usage in `worker.py`

### Priority 3: Improve Storage Backend Docstrings
- Add Args/Raises/Returns sections to `FileStorage` methods in `storage/file.py`
- Add Args/Raises/Returns sections to `SQLiteStorage` methods in `storage/sqlite.py`
- Add brief class docstrings to `Serializer` Protocol and its implementations

### Priority 4: Improve Logging Module
- Add Args/Raises sections to `log_task_*` functions in `logging.py`
- Keep `log_task_*` docstrings concise but complete

## Impact
- Affected specs: `api-standards` (new; docstring standards)
- Affected code:
  - `src/omniq/models.py` (TypedDicts)
  - `src/omniq/config.py` (BackendType, Settings)
  - `src/omniq/core.py` (public façade methods)
  - `src/omniq/queue.py` (AsyncTaskQueue power-user API)
  - `src/omniq/worker.py` (AsyncWorkerPool power-user API)
  - `src/omniq/storage/file.py`, `storage/sqlite.py` (power-user APIs)
  - `src/omniq/logging.py` (utility functions)

## Non-Goals
- No runtime behavior changes or API modifications.
- No contributor documentation (users only).
- Not attempting to document every internal method (focus on public APIs and power-user modules).
- Examples focused on happy path (no error handling in examples).
