## 1. Async Worker Pool
- [ ] 1.1 Implement `AsyncWorkerPool` in `src/omniq/worker.py` with configurable `concurrency` and `poll_interval`.
- [ ] 1.2 Implement the background loop that polls storage for due tasks, spawns asyncio tasks, and waits for completion.
- [ ] 1.3 Ensure graceful shutdown semantics so in-flight tasks can complete or be cancelled cleanly.

## 2. Callable Execution and Retries
- [ ] 2.1 Implement helper logic to execute both async and sync callables (using a thread executor for sync functions).
- [ ] 2.2 Implement retry handling based on `max_retries`, attempts, and a simple exponential backoff with jitter.
- [ ] 2.3 Ensure interval tasks are rescheduled on success using their `interval` field.

## 3. Sync Worker Wrapper
- [ ] 3.1 Implement `WorkerPool` in `src/omniq/worker.py` that runs `AsyncWorkerPool` in a dedicated thread.
- [ ] 3.2 Provide blocking `start()` and `stop()` methods for sync callers.

