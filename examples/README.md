# OmniQ Examples

This directory contains curated, runnable examples demonstrating key OmniQ features. Each example is a self-contained script that you can run directly.

## Running Examples

Each example can be run from the project root:

```bash
# Run an example
python examples/01_quickstart_async.py

# Run all examples
for script in examples/*.py; do python "$script"; done
```

## Examples

### 01_quickstart_async.py

**What it demonstrates:**
- AsyncOmniQ façade initialization
- File-based storage backend
- Enqueuing both sync and async tasks
- Worker pool configuration and execution
- Waiting for task results with `get_result(wait=True)`

**Key concepts:**
- `AsyncOmniQ` class
- `Settings` configuration
- `worker()` method to create worker pools
- Async/await patterns

**Run time:** ~1-2 seconds

---

### 02_scheduling_eta_and_interval.py

**What it demonstrates:**
- Task scheduling with `eta` (delayed execution)
- Repeating tasks with `interval`
- Worker polling behavior
- Interval task rescheduling (new task IDs each execution)

**Key concepts:**
- Delayed execution with `eta` parameter
- Repeating tasks with `interval` parameter (in milliseconds)
- Task lifecycle for scheduled and interval tasks

**Run time:** ~3 seconds

---

### 03_retries_and_task_errors.py

**What it demonstrates:**
- SQLite storage backend
- Deterministic retry behavior (fail N times then succeed)
- Task error and result metadata
- Retry budget and exponential backoff

**Key concepts:**
- `max_retries` parameter for retry configuration
- `TaskError` model with error details
- `attempts` tracking in task results
- Retry budget semantics (attempts < max_retries)

**Run time:** ~2-3 seconds

---

### 04_sync_api_logging_and_env.py

**What it demonstrates:**
- OmniQ sync façade for synchronous code
- `Settings.from_env()` for environment-based configuration
- Loguru logging configuration
- Task correlation with `bind_task()`
- `WorkerPool` for sync task execution

**Key concepts:**
- `OmniQ` sync API
- Environment variable configuration (`OMNIQ_BACKEND`, `OMNIQ_BASE_DIR`)
- Enhanced logging with `configure()` and `bind_task()`
- Sync worker pool execution

**Run time:** ~1-2 seconds

---

## Shared Task Functions

The `tasks.py` module contains shared task functions used across examples:

- `sync_add(a, b)` - Simple synchronous addition
- `async_multiply(a, b)` - Simple asynchronous multiplication
- `flaky_task(value, fail_before=2)` - Fails N times before succeeding (for retry demos)
- `echo_task(value)` - Echoes its input
- `process_item(item_id, data)` - Processes an item and returns a result dict

These functions are defined as top-level module functions to ensure stable `func_path` resolution.

## Example Conventions

All examples follow these conventions:

- **Fast**: Complete in under 10 seconds
- **Deterministic**: No randomness or external dependencies
- **Self-contained**: Use temporary directories for storage
- **Clear output**: Explicit prints explaining what's happening
- **Minimal overlap**: Each example demonstrates distinct feature clusters

## Storage Backends

The examples demonstrate both storage backends:
- File backend: `01_quickstart_async.py`, `02_scheduling_eta_and_interval.py`, `04_sync_api_logging_and_env.py`
- SQLite backend: `03_retries_and_task_errors.py`
