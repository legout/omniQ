## 1. Specify timeout semantics
- [x] 1.1 Add timeout behavior requirements to `worker-pool-core` via an OpenSpec delta.
- [x] 1.2 Clarify how `timeout` on the task (or default from settings) is interpreted for async vs sync callables.
- [x] 1.3 Define the error shape / messaging for timeout failures at the `TaskResult` level.

## 2. Implement timeout enforcement
- [x] 2.1 Update `AsyncWorkerPool._execute_task` in `src/omniq/worker.py` to enforce per-task timeouts using `asyncio.wait_for` (or equivalent).
- [x] 2.2 Ensure timeout behavior applies consistently to both async and sync callables.
- [x] 2.3 Integrate timeout failures with the existing retry logic (treat timeout as a failure that may be retried up to `max_retries`).

## 3. Tests and validation
- [x] 3.1 Add tests that verify tasks exceeding their timeout are cancelled and recorded as failures.
- [x] 3.2 Add tests that verify tasks with `timeout=None` or unset are not subject to per-task timeouts.
- [x] 3.3 Add tests that verify timed-out tasks participate in retry/backoff behavior as specified.