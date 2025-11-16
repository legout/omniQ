## Why
OmniQ v1 needs a small, focused storage abstraction with concrete file-based persistence so tasks and results can survive process restarts and be shared across worker processes. The PRD calls for a `BaseStorage` interface plus a file-based backend with simple but reliable dequeue semantics.

## What Changes
- Define a `BaseStorage` async interface for queue and result operations used by the queue engine and worker pool.
- Specify dequeue ordering by `eta` and simple FIFO semantics for due tasks.
- Introduce a file-based storage backend that uses the local filesystem for tasks and results, with safe dequeue and write patterns.
- Clarify how serialization is applied at the storage boundary without committing to a specific serializer here.

## Impact
- Establishes a stable contract for multiple backends while keeping v1 limited to file and SQLite.
- Enables developers to run OmniQ in a single process or across multiple local worker processes using the filesystem.
- Keeps the storage interface small so future backends (Redis, Postgres, cloud storage) can be added without breaking the core API.

