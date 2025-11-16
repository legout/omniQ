## Why
OmniQ's v1 worker model is an async worker pool with a simple sync wrapper. The PRD defines an asyncio-based worker that polls storage, executes tasks concurrently, handles retries with backoff, and supports both async and sync callables. A clear spec is needed so implementations stay small and predictable.

## What Changes
- Define the behavior of `AsyncWorkerPool`, including concurrency, polling, and shutdown.
- Specify how workers execute async vs sync callables, including thread executor usage for sync functions.
- Describe the retry and backoff strategy, including how `max_retries`, attempts, and jitter interact with scheduling.
- Introduce a sync `WorkerPool` wrapper that runs the async pool in a dedicated thread with blocking `start()` and `stop()`.

## Impact
- Provides a single, well-understood worker implementation for v1 that matches the PRD.
- Keeps worker behavior predictable and easy to test, with clear retry and scheduling rules.
- Leaves room to add alternative worker strategies (e.g., process pool, gevent) later without changing the queue or storage APIs.

