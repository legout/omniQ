# OmniQ NATS.io Backend Implementation Prompt

## Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, and distributed processing in their applications with both synchronous and asynchronous interfaces.

## Core Design Principles

- **Async First, Sync Wrapped:** The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
- **Separation of Concerns:** Task queue, result storage, and event logging are decoupled and independent.
- **Interface-Driven:** All components implement common interfaces.
- **Storage Independence:** Allow independent selection of storage backends for tasks, results, and events.

## Module Architecture Focus

### `omniq.storage.nats`
- **AsyncNATSQueue:** Core async implementation using `nats.aio` for task queue operations.
- **NATSQueue:** Synchronous wrapper around `AsyncNATSQueue`.
- **AsyncNATSResultStorage:** Core async implementation for result storage using NATS.
- **NATSResultStorage:** Synchronous wrapper around `AsyncNATSResultStorage`.

Responsibilities:
- Implement enqueue, dequeue, store, retrieve, and related operations for tasks and results.
- Use NATS subject prefixes to support multiple queues.
- Ensure connection pooling for efficient distributed operation.
- Provide both async and sync context managers (`__aenter__`/`__aexit__`, `__enter__`/`__exit__`).

### `omniq.backend.nats`
- Integrates the NATS-based queue and result storage into the OmniQ backend interface.
- Coordinates task queueing and result storage using the NATS implementations.
- Ensures backend can independently select storage for tasks and results.

**Note:** NATS is not used as an event storage backend in OmniQ. Only task queue and result storage are implemented for NATS.

## Development Guidelines

- **Async First, Sync Wrapped Implementation Guidelines:**
  - Implement all core functionality using async/await.
  - Create synchronous wrappers using `anyio.from_thread.run()` or event loops.
  - Use `Async` prefix for async classes, no prefix for sync wrappers. Sync wrapper methods should have a `_sync` suffix.
  - Implement both async and sync context managers.
  - Preserve exception context and ensure proper resource cleanup in both sync and async contexts.

- **Storage Implementation (NATS-specific):**
  - Use subject prefixes for queue separation.
  - Implement connection pooling for distributed backends.
  - Support independent selection of storage backends for tasks and results.

- **Task Queue and Worker Coordination:**
  - Use NATS queue groups to ensure exclusive consumption of tasks by workers (task locking).
  - Implement multiple queues using subject prefixes.

## Scope

- Fully implement the NATS.io backend for OmniQ, including both task queue and result storage.
- Provide asynchronous and synchronous interfaces for all operations (enqueue, dequeue, store, retrieve, etc.).
- Ensure robust connection management to NATS.
- Utilize NATS queue groups for exclusive task consumption and worker coordination.

## Dependencies

- [`nats-py`](https://github.com/nats-io/nats.py): NATS messaging system client for Python.

## Completion

Upon completion, the NATS backend should provide a robust, async-first, interface-driven implementation for both task queue and result storage, fully integrated into the OmniQ architecture, and adhering to all design and development guidelines above.