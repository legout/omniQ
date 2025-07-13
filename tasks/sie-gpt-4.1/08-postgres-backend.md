<!-- @/tasks/08-postgres-backend.md -->
# Subtask 2.3: PostgreSQL Backend

**Objective:**  
Build a feature-rich PostgreSQL backend for OmniQ supporting full task, result, and event storage and querying.

**Requirements:**  
- Use `asyncpg` for all async operations.
- Design efficient schemas for tasks (with named queues, priority, TTL), results, events (no serialization).
- Implement robust task locking (e.g., row-level locking with `FOR UPDATE SKIP LOCKED`), transactions, and cleanup of expired tasks/results.
- Support schedule state, querying, and indexed access.
- Both async and sync interfaces.
- Test thoroughly using `pytest-asyncio`.

**Context from Project Plan:**  
- Follow all “Storage Strategy", “Event Architecture” and “Fault Tolerance” details.

**Dependencies:**  
- Builds on core abstractions and serialization systems.

**Deliverables:**  
- PostgreSQL backend implementation and supporting tests in `src/omniq/storage/postgres.py`.