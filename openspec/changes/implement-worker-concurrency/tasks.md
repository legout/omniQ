## 1. Spec
- [ ] Update `worker-pool-core` concurrency requirement to explicitly require parallel task execution up to the configured limit
- [ ] Update/clarify sync wrapper requirements for `start()` / `stop()`

## 2. Implementation
- [ ] Implement bounded concurrency in `AsyncWorkerPool` (no more sequential `_execute_task` loop)
- [ ] Ensure polling continues while capacity is available
- [ ] Ensure stop signals exit promptly (bounded by `poll_interval` and configurable timeouts)
- [ ] Update `WorkerPool` to match spec semantics and document any deprecations

## 3. Tests
- [ ] Add a concurrency test proving `N` tasks run concurrently (uses coordination primitives, not sleeps)
- [ ] Add shutdown tests: stop while idle; stop while tasks in-flight; stop timeout behavior

