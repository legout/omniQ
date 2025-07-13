# OmniQ Redis Backend: Think Mode Prompt

Analyze the following requirements and implementation notes to generate a detailed plan for implementing the Redis backend for OmniQ:

## Relevant Architecture

- The storage layer supports pluggable backends for task queues and result storage.
- All components implement both async (core) and sync (wrapper) interfaces.
- Multiple named queues are supported via queue prefixes.
- The backend must support both context managers (sync and async).

## Implementation Details

- Use `redis.asyncio` for async operations.
- Implement both `AsyncRedisQueue` and `RedisQueue` (sync wrapper).
- Support multiple named queues using queue prefixes.
- Implement TTL enforcement and cleanup for tasks.
- Support bulk operations and efficient key management.
- Implement task locking to prevent duplicate execution.
- Store schedule state (active/paused) using Redis keys or metadata.
- Use prefixes for queue and key management.

## Prompt

**Generate a detailed implementation plan for the Redis backend, specifying:**
- The prefixing scheme for supporting multiple named queues.
- The required async and sync interfaces and their methods.
- How to handle task TTL, locking, and schedule state using Redis.
- Strategies for efficient bulk operations and key management.
- How to ensure reliable delivery and handle Redis-specific edge cases.
- Any failure scenarios or distributed system considerations.