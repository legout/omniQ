# OmniQ SQLite Backend: Think Mode Prompt

Analyze the following requirements and implementation notes to generate a detailed plan for implementing the SQLite backend for OmniQ:

## Relevant Architecture

- The storage layer supports pluggable backends for task queues, result storage, and event storage.
- All components implement both async (core) and sync (wrapper) interfaces.
- Multiple named queues are supported via a queue column approach with priority ordering.
- The backend must support both context managers (sync and async).
- Task events are stored without serialization in SQLite.

## Implementation Details

- Use `aiosqlite` for async operations.
- Implement both `AsyncSQLiteQueue` and `SQLiteQueue` (sync wrapper).
- Support multiple named queues using a queue column.
- Implement TTL enforcement and cleanup for tasks.
- Support bulk operations and transaction consistency.
- Store schedule state (active/paused) in the database.
- Implement task locking to prevent duplicate execution.
- Store events as structured rows (no serialization).
- Provide connection pooling for efficiency.

## Prompt

**Generate a detailed implementation plan for the SQLite backend, specifying:**
- The schema design for supporting multiple named queues and priority ordering.
- The required async and sync interfaces and their methods.
- How to handle task TTL, locking, and schedule state.
- Strategies for efficient bulk operations and transaction management.
- How to store and query events without serialization.
- Any edge cases or failure scenarios to consider.