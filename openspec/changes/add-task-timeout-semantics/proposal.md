## Why
The v1 PRD calls out "basic retry and timeout semantics", but current OpenSpec capabilities and the implemented `AsyncWorkerPool` only define retry behavior. There is no specification or implementation of per-task execution timeouts based on the `timeout` field in the task model and settings.

Without explicit timeout semantics, long-running or stuck callables can block workers indefinitely, violate user expectations from the PRD, and make retries ineffective for certain classes of failures.

## What Changes
- Specify how per-task `timeout` values are interpreted by the worker pool for both async and sync callables.
- Define behavior when a task exceeds its timeout (cancellation, error signaling, and interaction with retries).
- Document the "no timeout" behavior when `timeout` is `None` or unset.
- Update the worker implementation to enforce timeouts using asyncio primitives in a way that keeps the worker small and predictable.

## Impact
- Aligns the implementation and specs with the v1 PRD requirement for timeout semantics.
- Provides a clear failure mode for hung or excessively long-running tasks.
- Keeps the worker model simple by treating timeouts as another failure mode that plugs into the existing retry logic.

