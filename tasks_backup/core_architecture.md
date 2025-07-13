# OmniQ Core Architecture: Think Mode Prompt

Analyze the following to define the core interfaces and design principles for the OmniQ library:

## Core Design Principles

- Async-first, sync-wrapped: Core library is asynchronous for performance, with sync wrappers for convenience.
- Separation of concerns: Task queue, result storage, and event logging are decoupled and independent.
- Interface-driven: All components implement common interfaces.
- Storage abstraction: Use `fsspec` for file and memory storage.
- Worker flexibility: Support async, thread, process, and gevent workers.
- Serialization: Use `msgspec` and `dill` for intelligent serialization.
- Storage independence: Allow independent selection of storage backends for tasks, results, and events.
- SQL-based event logging: Use SQL or structured storage for event querying.
- Task lifecycle management: Support TTL and automatic cleanup.
- Flexible scheduling: Enable pausing and resuming of scheduled tasks.

## Architecture Overview

- OmniQ coordinates Task Queue, Result Storage, Event Storage, and Worker components.
- Task Queue supports File, Memory, SQLite, PostgreSQL, Redis, and NATS backends.
- Result Storage and Event Storage support the same backend types.
- Workers include async, thread pool, process pool, and gevent pool types.
- Backend layer provides unified interfaces for each backend type.

## Enhanced System & Component Architecture

- Interface Layer: Async API (core), Sync API (wrappers).
- Task Management: Task model (with TTL), scheduling, dependency graph.
- Storage Layer: Task Queue, Result Storage, Event Storage (all pluggable).
- Execution Layer: Multiple worker types.
- Configuration Layer: YAML, env, dict, object config.
- Backend Layer: Unified backend interface for all storage types.

## Component Separation & Backend Abstraction

- Components are independent and replaceable.
- Backend classes provide unified interface for storage systems.
- Multiple named queues supported in all backends.

## Storage Interfaces

- `BaseTaskQueue`, `BaseResultStorage`, `BaseEventStorage` define sync/async interfaces.
- Implement async core functionality first, then sync wrappers.
- Use `fsspec` for file/memory storage with `base_dir` as prefix.
- Support memory, local, S3, Azure, GCP via fsspec.
- Connection pooling, transactions, bulk ops, TTL enforcement, task locking.

## Prompt

**Define the core interfaces and design principles for the OmniQ library based on the above. Specify:**
- The required interfaces for task queues, result storage, event storage, and workers.
- The principles that should guide implementation and extension.
- How to ensure pluggability, separation of concerns, and backend independence.
- Any patterns or abstractions needed for robust, scalable, and testable design.