## Why
The PRD requires a SQLite-based backend so OmniQ can be used in environments where filesystem-based storage is insufficient or where SQL tooling is preferred. SQLite provides a lightweight, local, transactional store that fits OmniQ's v1 constraints without introducing external infrastructure.

## What Changes
- Introduce a `SQLiteStorage` implementation of the `BaseStorage` interface using `aiosqlite`.
- Define a minimal schema for `tasks` and `results` tables, including indexes for efficient dequeue by `eta` and status.
- Specify how dequeue, mark_*, result retrieval, and TTL cleanup behave in the SQLite backend.

## Impact
- Enables deployments that prefer SQLite files over directory-based queues while keeping the same core API.
- Provides a more queryable and transactional store for tasks and results without changing worker or public API behavior.
- Keeps v1 lightweight by depending only on SQLite, not on external databases or brokers.

