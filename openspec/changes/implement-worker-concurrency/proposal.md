# Change: Implement true worker concurrency and clarify sync wrapper semantics

## Why
`AsyncWorkerPool` currently processes tasks sequentially even when configured with `concurrency > 1`, and the sync `WorkerPool.start()` blocks indefinitely (joins immediately). This contradicts the worker-pool specification and makes the worker API misleading.

## What Changes
- Implement real concurrency in `AsyncWorkerPool` with a bounded concurrency mechanism.
- Define shutdown semantics: how in-flight tasks are handled on stop, and how the polling loop exits.
- Clarify and align the synchronous wrapper behavior:
  - either make `start()` non-blocking (returns once running), or
  - introduce explicit `run_forever()` while keeping `start()` non-blocking.

## Impact
- Affected specs: `worker-pool-core`
- Affected code (expected): `src/omniq/worker.py`, `src/omniq/core.py`
- Potentially user-visible behavior change: `WorkerPool.start()` no longer blocks forever (or is renamed with a migration path).
- Risk: Medium (concurrency + shutdown edge cases); mitigated via deterministic tests and timeouts.

