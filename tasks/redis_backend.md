# OmniQ Redis Backend Implementation Prompt

## Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, and distributed processing in their applications with both synchronous and asynchronous interfaces.

---

## Core Design Principles

- **Async First, Sync Wrapped:** The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
- **Separation of Concerns:** Task queue, result storage, and event logging are decoupled and independent.
- **Interface-Driven:** All components implement common interfaces.
- **Storage Independence:** Allow independent selection of storage backends for tasks, results, and events.

---

## Module Architecture Focus

### `omniq.storage.redis`

- **AsyncRedisQueue**: Core async implementation using `redis.asyncio` for task queue operations (enqueue, dequeue, lock, etc.).
- **RedisQueue**: Synchronous wrapper around `AsyncRedisQueue` using the prescribed sync-wrapping pattern.
- **AsyncRedisResultStorage**: Async implementation for result storage using `redis.asyncio`.
- **RedisResultStorage**: Synchronous wrapper around `AsyncRedisResultStorage`.

**Key Design Decisions:**
- Use Redis key prefixes to support multiple queues and result sets.
- Ensure connection pooling and efficient resource management.
- Implement both async and sync context managers.
- Provide atomic task locking using Redis atomic operations (e.g., `SETNX`, Lua scripts).

### `omniq.backend.redis`

- Integrates the Redis queue and result storage implementations.
- Exposes backend interfaces for use by the OmniQ orchestrator.
- Does **not** provide event storage via Redis (per the implementation plan).

---

## Development Guidelines

### Async First, Sync Wrapped Implementation Guidelines

- All core functionality must be implemented using async/await.
- Synchronous wrappers should use `anyio.from_thread.run()` or equivalent.
- Use `Async` prefix for async classes; sync wrappers have no prefix.
- Implement both `__aenter__`/`__aexit__` and `__enter__`/`__exit__` context managers.
- Ensure proper exception propagation and resource cleanup in both sync and async contexts.

### Storage Implementation

- Use Redis key prefixes for queue and result storage separation.
- Support multiple queues within the same Redis instance.
- Ensure connection pooling for all Redis operations.
- Allow independent selection of storage backends for tasks and results.
- Implement both sync and async context managers for all storage classes.

### Task Queue and Worker Coordination

- Implement atomic task locking using Redis atomic operations (e.g., `SETNX`, Lua scripts) to prevent duplicate execution.
- Ensure all queue operations are safe for concurrent workers.

---

## Scope

- Fully implement the Redis backend, including task queue and result storage.
- Provide both asynchronous and synchronous interfaces for all operations (enqueue, dequeue, store, retrieve, etc.).
- Ensure robust connection management and resource cleanup.
- Utilize Redis atomic operations for task locking and coordination.
- Event storage is **not** implemented in Redis.

---

## Dependencies

- [`redis`](https://pypi.org/project/redis/) (including `redis.asyncio`)

---

## Completion

Upon completion, the Redis backend should provide robust, async-first, sync-wrapped implementations for both task queue and result storage, following all OmniQ design principles and development guidelines.