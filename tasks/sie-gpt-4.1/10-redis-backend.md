<!-- @/tasks/10-redis-backend.md -->
# Subtask 2.5: Redis Backend

**Objective:**  
Develop a Redis-based backend for task, result, and event storage with OmniQ, supporting distributed concurrency.

**Requirements:**  
- Use `redis.asyncio` for async implementation.
- Support queue prefixes for named queues, implement atomic operations for locking and TTL.
- Store results and events in appropriate Redis structures.
- Provide task expiration and dead-letter queue for errors/timeouts.
- Support querying and efficient bulk cleanup.
- Both async and sync interfaces.
- Test with `pytest-asyncio` against local and remote Redis.

**Context from Project Plan:**  
- Pay special attention to “Redis Atomic Operations” notes and distributed task locking.

**Dependencies:**  
- Build with previous core architecture and serialization.

**Deliverables:**  
- Redis backend implementation in `src/omniq/storage/redis.py` and thorough tests.