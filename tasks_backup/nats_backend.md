# OmniQ NATS Backend: Think Mode Prompt

Analyze the following requirements and implementation notes to generate a detailed plan for implementing the NATS backend for OmniQ:

## Relevant Architecture

- The storage layer supports pluggable backends for task queues and result storage.
- All components implement both async (core) and sync (wrapper) interfaces.
- Multiple named queues are supported via subject prefixes.
- The backend must support both context managers (sync and async).

## Implementation Details

- Use `nats.aio` for async operations.
- Implement both `AsyncNATSQueue` and `NATSQueue` (sync wrapper).
- Support multiple named queues using subject prefixes.
- Implement TTL enforcement and cleanup for tasks.
- Support bulk operations and efficient message handling.
- Implement task locking to prevent duplicate execution.
- Store schedule state (active/paused) using NATS subjects or metadata.
- Use prefixes for queue and subject management.

## Prompt

**Generate a detailed implementation plan for the NATS backend, specifying:**
- The subject prefixing scheme for supporting multiple named queues.
- The required async and sync interfaces and their methods.
- How to handle task TTL, locking, and schedule state using NATS.
- Strategies for efficient bulk operations and message management.
- How to ensure reliable delivery and handle NATS-specific edge cases.
- Any failure scenarios or distributed system considerations.