## Overview
This change implements the async worker pool that drives task execution. The worker pool coordinates polling storage, resolving callables, executing tasks with concurrency limits, and handling retries and interval rescheduling.

Key goals:
- Keep the worker loop small and understandable.
- Make concurrency and shutdown behavior predictable.
- Centralize retry and backoff logic so storage remains simple.

## Core Structures
- Location: `src/omniq/worker.py`
- Main types:
  - `AsyncWorkerPool`
  - `WorkerPool` (sync wrapper)
- Dependencies:
  - `BaseStorage` for queue operations.
  - `Serializer` (indirectly, via task models).
  - `AsyncTaskQueue` or equivalent queue helper, if introduced later.

## AsyncWorkerPool Design

### Configuration
- Constructor parameters:
  - `storage: BaseStorage`
  - `concurrency: int` (default 1)
  - `poll_interval: float` seconds (default 1.0)
  - Optional: `base_retry_delay: float` (default small value, e.g., 1.0)
- Internal state:
  - `running: bool` flag.
  - Set of in-flight asyncio tasks.

### Main Loop
- `start()`:
  - Marks `running = True`.
  - Spawns a background coroutine (`_run_loop`) that:
    - While `running`:
      - Fill available worker slots up to `concurrency`:
        - `while len(in_flight) < concurrency:`
          - `task = await storage.dequeue(now=now())`
          - If no task: break; otherwise schedule `_execute_task(task)` as an asyncio Task and add to `in_flight`.
      - If `in_flight` is empty:
        - `await asyncio.sleep(poll_interval)`
      - Otherwise:
        - Wait for any in-flight task to complete using `asyncio.wait(..., return_when=FIRST_COMPLETED)`.
    - When stopping, optionally wait for in-flight tasks to finish or cancel them based on shutdown policy.

### Shutdown Semantics
- `stop()`:
  - Sets `running = False`.
  - Signals the loop to exit on the next iteration.
  - Policy (v1):
    - Default: allow in-flight tasks to finish (best-effort graceful shutdown).
    - If needed, expose a flag or method (e.g., `stop(cancel_in_flight=True)`) later to cancel tasks.

## Task Execution Pipeline

### Resolving Callables
- `func_path` resolution:
  - Use `importlib` to import the module and fetch the attribute referenced by the dotted path.
  - Cache resolved callables in a simple dict to avoid repeated imports where possible.

### Async vs Sync Callables
- If `callable` is `async def` or returns a coroutine:
  - Execute with `await func(*args, **kwargs)`.
- Otherwise (sync callable):
  - Use `loop.run_in_executor(None, functools.partial(func, *args, **kwargs))`.
  - Executor: default thread pool via `None` executor; v1 avoids custom executors to keep things simple.

### Status Updates
- Before execution:
  - Call `storage.mark_running(task.id)`.
- On success:
  - Build `TaskResult` with `status=SUCCESS` and serialized return value.
  - Call `storage.mark_done(task.id, result)`.
- On failure:
  - Build error metadata (stringified exception plus basic traceback info).
  - Decide whether to retry or fail permanently and call `storage.mark_failed(task.id, error, will_retry=...)`.

## Retries and Backoff

### Attempts Tracking
- Attempts are tracked on the task or result model (e.g., `attempts` field).
- Worker behavior:
  - Read current attempt count when executing.
  - Increment and persist attempt count via `mark_failed` / rescheduling operations.

### Backoff Formula
- Base formula from PRD:
  - `delay = base_retry_delay * (2 ** attempts)`
  - Add jitter: `delay += random.uniform(0, jitter_max)` where `jitter_max` is a small constant (e.g., `0.1 * delay`).
- Rescheduling:
  - When `attempts < max_retries`:
    - Compute `new_eta = now() + delay`.
    - Call `storage.mark_failed(task.id, error, will_retry=True)`.
    - Call `storage.reschedule(task.id, new_eta)` if supported; otherwise re-enqueue as a new task instance as a fallback.
  - When `attempts >= max_retries`:
    - Call `storage.mark_failed(task.id, error, will_retry=False)` and do not reschedule.

## Interval Scheduling

### Fixed-Interval Tasks
- For tasks with `interval` set:
  - On successful completion:
    - Compute `new_eta = now() + task.interval`.
    - Reschedule the same task (or a logical continuation) for the next run:
      - Prefer `storage.reschedule(task.id, new_eta)` if supported.
      - If unsupported, enqueue a new task with the same callable and arguments as a fallback.
- Workers do not attempt to "catch up" missed intervals; they schedule from completion time to keep semantics simple.

## Sync WorkerPool Wrapper

### Design
- Location: `src/omniq/worker.py` (same module).
- Responsibilities:
  - Create and own an event loop running in a dedicated thread.
  - Start `AsyncWorkerPool` on that loop.
  - Provide blocking `start()` / `stop()` methods for synchronous callers.

### Lifecycle
- `start()`:
  - Spawn a thread that:
    - Creates an event loop.
    - Runs `async_worker_pool.start()` and then the main loop.
  - Block until the worker loop signals that it is running (e.g., using an `Event`).
- `stop()`:
  - Signal the async side to stop (`running = False`).
  - Use thread-safe `call_soon_threadsafe` to wake the loop.
  - Join the thread before returning.

## Logging and Observability
- Worker-level logging:
  - Log at `INFO` level for:
    - Worker start/stop events.
    - Task start, success, and final failure.
  - Log at `DEBUG` level for:
    - Poll cycles with no work.
    - Per-attempt retry details (attempt count, next `eta`).
  - Avoid logging full argument payloads; log only task IDs and high-level context.

