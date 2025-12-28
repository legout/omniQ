# Change: Refactor SQLite storage backend for correctness and reliability

## Why
The SQLite backend contains duplicated `dequeue()` logic and debug prints, and its async I/O strategy is fragile. In this environment, `aiosqlite.connect()` hangs, and the current sqlite3 fallback wrapper is incomplete for cursor operations (e.g., `fetchone()`).

## What Changes
- Remove duplicated/dead code and debug output from `SQLiteStorage`.
- Simplify SQLite URL/path handling (avoid over-engineered parsing; keep behavior correct for absolute vs relative paths).
- Define and implement a reliable async strategy for sqlite:
  - robust `aiosqlite` usage with timeouts and clear failure modes, and/or
  - a correct sqlite3+executor wrapper that supports cursor fetch operations if `aiosqlite` cannot be used.
- Ensure attempt counting and RUNNING claim semantics are consistent with the core lifecycle.

## Impact
- Affected specs: `task-storage-sqlite`, `task-storage-core`
- Affected code (expected): `src/omniq/storage/sqlite.py`, `src/omniq/storage/_async_sqlite.py`
- Risk: Medium (core backend); mitigated by focused storage tests and basic stress tests for dequeue ordering and atomicity.
- Non-goals: introducing new third-party I/O dependencies (keep v1 lightweight unless explicitly approved).
