<!-- @/tasks/06-sqlite-backend.md -->
# Subtask 2.1: SQlite Backend

**Objective:**  
Implement complete support for SQlite as a backend for tasks, results, and events in the OmniQ system, following the core abstractions.

**Requirements:**  
- Use `aiosqlite` for async operations.
- Design table schemas for tasks (with queue, priority, TTL), results, and events.
- Implement task locking, transaction, and atomic deletion/cleanup of expired rows.
- Support schedule state persistence, event metadata storage, and efficient querying.
- Provide both async and sync wrapper classes.
- Comprehensive test coverage using `pytest` and `pytest-asyncio`.

**Context from Project Plan:**  
- Review all storage, TTL, and event requirements.  
- Use table-column approach for multiple named queues.

**Dependencies:**  
- Build on the previously defined core interfaces and serialization.

**Deliverables:**  
- Full SQlite backend implementation and tests under `src/omniq/storage/sqlite.py`, and corresponding test modules.