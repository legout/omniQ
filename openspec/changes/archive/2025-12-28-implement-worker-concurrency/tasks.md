## 1. Spec
- [x] Update `worker-pool-core` concurrency requirement to explicitly require parallel task execution up to the configured limit
- [x] Update/clarify sync wrapper requirements for `start()` / `stop()`
- [x] Update spec to define in-flight task tracking (asyncio.Task objects vs IDs)
- [x] Update spec to define shutdown semantics (cancel vs drain, timeout behavior)
- [x] Update spec to delegate retry/interval scheduling to queue (no duplicate logic in worker)

## 2. Implementation
- [x] Implement bounded concurrency in `AsyncWorkerPool` (no more sequential `_execute_task` loop)
  - Use asyncio.Semaphore(self.concurrency) to limit concurrent tasks
  - Track asyncio.Task objects for proper shutdown handling
- [x] Ensure polling continues while capacity is available
  - Current implementation already does this
- [x] Ensure stop signals exit promptly (bounded by `poll_interval` and configurable timeouts)
  - Current implementation has shutdown_event mechanism
- [x] Update `WorkerPool` to match spec semantics and document any deprecations
  - start() is blocking by design for sync wrapper pattern
- [x] Update `worker-pool-core` spec to remove duplicate retry/interval scheduling requirements
  - Queue owns retry policy, worker delegates

## 3. Tests
- [x] Add a concurrency test proving `N` tasks run concurrently (uses coordination primitives, not sleeps)
  - test_worker_concurrency.py exists and verifies semaphore limits concurrency properly
- [x] Add shutdown tests: stop while idle; stop while tasks in-flight; stop timeout behavior
  - Verify graceful shutdown with proper task cleanup
