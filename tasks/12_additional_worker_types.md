# Task 12: Additional Worker Types

## Objective
To implement the remaining worker types as outlined in the project plan: Process Pool Worker and Gevent Pool Worker.

## Requirements

### 1. Process Pool Worker (`src/omniq/workers/process.py`)
- Create `src/omniq/workers/process.py`.
- Implement `AsyncProcessWorker` and `ProcessPoolWorker` (sync wrapper) using `multiprocessing.Pool` or similar for process-based concurrency.
- This worker should be capable of running both sync and async tasks, handling task execution in separate processes to bypass GIL limitations for CPU-bound tasks.
- Ensure proper process management and cleanup.

### 2. Gevent Pool Worker (`src/omniq/workers/gevent.py`)
- Create `src/omniq/workers/gevent.py`.
- Implement `AsyncGeventWorker` and `GeventPoolWorker` (sync wrapper) using `gevent` for coroutine-based concurrency.
- This worker should be capable of running both sync and async tasks within gevent greenlets.
- Ensure proper gevent patching and context management.

## Completion Criteria
- `src/omniq/workers/process.py` is created with `AsyncProcessWorker` and `ProcessPoolWorker`.
- `src/omniq/workers/gevent.py` is created with `AsyncGeventWorker` and `GeventPoolWorker`.
- Both new worker types correctly implement the `BaseWorker` interface and handle sync/async tasks as specified.