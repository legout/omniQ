# Task 4: Worker Implementation

## Objective
To implement the task execution layer of the OmniQ library. This involves creating a flexible worker system that can process tasks from the queue. The initial focus will be on an asynchronous worker, which will serve as the core for other worker types.

## Requirements

### 1. Base Worker Interface (`src/omniq/workers/base.py`)
- Create a `base.py` file in the `src/omniq/workers/` directory.
- Define a `BaseWorker` abstract base class (ABC).
- This interface must declare the following methods:
    - `start()`: Starts the worker.
    - `stop()`: Stops the worker gracefully.
    - `run()`: The main loop for the worker to fetch and execute tasks.
- The interface should be designed to handle both `async` and `sync` operations, following the "Async First, Sync Wrapped" principle.

### 2. Async Worker Implementation (`src/omniq/workers/async.py`)
- Create an `async.py` file in the `src/omniq/workers/` directory.
- Implement `AsyncWorker` which inherits from `BaseWorker`.
- This worker will be the core async implementation.
- It should be able to:
    - Connect to a task queue.
    - Dequeue tasks one by one.
    - Execute the task's function. It must be capable of running both `async` and `sync` functions. Sync functions should be run in a separate thread pool (e.g., using `anyio.to_thread.run_sync`) to avoid blocking the async event loop.
    - After execution, store the result in the result storage.
    - Log lifecycle events (e.g., `STARTED`, `COMPLETED`, `FAILED`) to the event storage.
- The worker must respect task timeouts and TTLs.

### 3. Sync Worker Wrapper (`src/omniq/workers/thread.py`)
- While the primary focus is the async worker, a synchronous wrapper will be needed. For this task, we can outline the structure for the `ThreadWorker` in `thread.py`.
- Implement a `ThreadPoolWorker` that wraps the `AsyncWorker`.
- It will use a thread pool to run the async worker's `run` loop.
- It will expose a synchronous interface (`start`, `stop`).

## Completion Criteria
- `src/omniq/workers/base.py` is created with the `BaseWorker` abstract base class.
- `src/omniq/workers/async.py` is created with a fully functional `AsyncWorker`.
- The `AsyncWorker` can execute both `async` and `sync` tasks correctly.
- The worker interacts with the queue, result storage, and event storage as specified.
- The basic structure for a `ThreadPoolWorker` in `src/omniq/workers/thread.py` is defined, wrapping the async worker.