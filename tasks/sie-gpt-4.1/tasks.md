**Comprehensive Implementation Plan for OmniQ Library**

Below is a breakdown of the implementation strategy for the OmniQ library, from core extensible architecture to specific backend implementations. Each subtask below is followed by a **detailed prompt**, which should be saved as a markdown file under `@/tasks/<subtask-name>.md`.

---

## 1. Core Architecture Design and Implementation

### Subtask 1.1: Define Core Interfaces and Models

**Filename:** `@/tasks/01-core-interfaces-and-models.md`

**Prompt:**
> **Objective:**  
> Design and implement the core data models and interfaces for OmniQ, ensuring extensibility to support an arbitrary number of storage, result, and event backends.  
>
> **Requirements:**  
> - Define domain models: `Task`, `TaskResult`, `Schedule`, `TaskEvent`, and `Settings`, using `msgspec.Struct` for type-safety and serialization.  
> - Specify abstract base classes/interfaces (`ABC`s) for all critical components:  
>   - Task Queue (`BaseTaskQueue`)
>   - Result Storage (`BaseResultStorage`)
>   - Event Storage (`BaseEventStorage`)
>   - Worker (`BaseWorker`)
> - Each interface should offer both sync and async methods, using an "Async First, Sync Wrapped" pattern.  
> - Models must include unique identifiers, TTL support, status enums, dependency tracking, error/result states, run/schedule metadata, and serialization hints.
> - Include hashable/equatable support for tasks where needed (dependency graph support).
> - Settings must be overridable via environment variables with the `OMNIQ_` prefix.
>
> **Context from Project Plan:**  
> - Refer to the “Core Design Principles” and “Module Architecture” for guidance on how to keep separation of concerns and maintain interface-driven, extensible architecture.
> - Ensure “Component Separation,” “Backend Abstraction,” and “Async First, Sync Wrapped” patterns are central in all interface definitions.
>
> **Deliverables:**  
> - Full model definitions in `src/omniq/models/`  
> - Abstract base interface definitions in their respective modules (`src/omniq/queue/base.py`, `src/omniq/storage/base.py`, etc.).
> - Brief inline documentation for each model/interface.

---

### Subtask 1.2: Implement Serialization Layer

**Filename:** `@/tasks/02-serialization-layer.md`

**Prompt:**
> **Objective:**  
> Develop a modular serialization system within OmniQ that supports fast, secure, and reliable (de)serialization for core models and arbitrary task inputs/outputs.
>
> **Requirements:**  
> - Implement a `SerializationManager` that selects between `msgspec` (default) and `dill` (for complex objects).
> - Allow serialization selection logic based on instance/type inspection.
> - Record the serialization method used alongside stored values for accurate deserialization.
> - Incorporate security precautions when using `dill` (limit deserialization scope, warn users).
> - Ensure all core models use this serialization manager for storage.
>
> **Context from Project Plan:**  
> - Review the “Serialization Layer” and “Key Design Decisions: Serialization Strategy” sections.
>
> **Deliverables:**  
> - Pluggable serialization utilities in `src/omniq/serialization/`
> - Well-defined interface with usage in core models and planned future backends.

---

### Subtask 1.3: Core Scheduling and Dependency Engine

**Filename:** `@/tasks/03-scheduling-and-dependency-engine.md`

**Prompt:**
> **Objective:**  
> Implement the scheduling engine and dependency graph management for tasks.
>
> **Requirements:**  
> - Produce async (with sync wrappers) schedulers that handle immediate, interval, and cron-based schedules (using `croniter` and `python-dateutil`).
> - Support pausing and resuming of scheduled tasks.
> - Implement a task dependency graph to enforce dependency-based task execution.
> - Ensure all metadata/state changes generate appropriate events via the event system.
>
> **Context from Project Plan:**  
> - Refer to “Task Queue Engine” and “Task Models” for required features.
>
> **Deliverables:**  
> - Scheduler and dependency resolver modules under `src/omniq/queue/`.

---

### Subtask 1.4: Core Worker Pool and Execution Logic

**Filename:** `@/tasks/04-worker-pool-and-execution.md`

**Prompt:**
> **Objective:**  
> Develop a modular worker pool and unified task execution subsystem that works across backend storage types and both sync/async tasks.
>
> **Requirements:**  
> - Provide AsyncWorker, ThreadPoolWorker, ProcessPoolWorker, and GeventWorker (core async, with sync wrappers).
> - Support for max_workers and runtime configuration.
> - Implement logic to run async/sync Python callables, respecting task TTL and timeouts.
> - Handle callbacks, result storage, and event logging for task state transitions.
>
> **Context from Project Plan:**  
> - See “Worker Layer" and “Event System” for relevant requirements.
>
> **Deliverables:**  
> - Worker implementations and base interfaces under `src/omniq/workers/`.

---

### Subtask 1.5: Config and Settings Loader

**Filename:** `@/tasks/05-config-and-settings-loader.md`

**Prompt:**
> **Objective:**  
> Create a robust configuration loader supporting direct, dict, YAML, and environment variable-based configuration for all library components.
>
> **Requirements:**  
> - All settings constants are overridable with prefixed environment variables (`OMNIQ_`).
> - YAML loader, config validation, and type conversion using `msgspec`.
> - Support configuration for queues, storage, events, and workers.
>
> **Context from Project Plan:**  
> - Reference “Configuration” and “Settings and Environment Variables” sections.
>
> **Deliverables:**  
> - Comprehensive config loader and settings management under `src/omniq/config/`.

---

## 2. Backend Implementations

---

### Subtask 2.1: SQlite Backend

**Filename:** `@/tasks/06-sqlite-backend.md`

**Prompt:**
> **Objective:**  
> Implement complete support for SQlite as a backend for tasks, results, and events in the OmniQ system, following the core abstractions.
>
> **Requirements:**  
> - Use `aiosqlite` for async operations.
> - Design table schemas for tasks (with queue, priority, TTL), results, and events.
> - Implement task locking, transaction, and atomic deletion/cleanup of expired rows.
> - Support schedule state persistence, event metadata storage, and efficient querying.
> - Provide both async and sync wrapper classes.
> - Comprehensive test coverage using `pytest` and `pytest-asyncio`.
>
> **Context from Project Plan:**  
> - Review all storage, TTL, and event requirements.  
> - Use table-column approach for multiple named queues.
>
> **Dependencies:**  
> - Build on the previously defined core interfaces and serialization.
>
> **Deliverables:**  
> - Full SQlite backend implementation and tests under `src/omniq/storage/sqlite.py`, and corresponding test modules.

---

### Subtask 2.2: File Backend (Local, S3, ADL, GCS via fsspec)

**Filename:** `@/tasks/07-file-backend.md`

**Prompt:**
> **Objective:**  
> Develop an OmniQ backend using the `fsspec` interface for file/memory/remote object storage (local files, S3, ADLS, GCS).
>
> **Requirements:**  
> - Use `fsspec` to create a base file system abstraction, leveraging optional dependencies for S3 (`s3fs`), Azure (`adlfs`), and Google Cloud (`gcsfs`).
> - Implement directory structure for named queues, priority, and TTL.
> - Store results and events as files/JSON as specified.
> - Provide async implementation (leveraging `anyio` where necessary) with sync wrappers.
> - Support use of storage URI and `base_dir` parameter.
> - Support bulk operations and automatic cleanup.
> - Comprehensive test coverage against local memory and at least one cloud service.
>
> **Context from Project Plan:**  
> - Follow File Storage Implementation and Cloud Storage notes in the plan.
>
> **Dependencies:**  
> - Integrates with core interfaces, models, and serialization already defined.
>
> **Deliverables:**  
> - File backend implementation covering all core abstractions, live in `src/omniq/storage/file.py`, with tests.

---

### Subtask 2.3: PostgreSQL Backend

**Filename:** `@/tasks/08-postgres-backend.md`

**Prompt:**
> **Objective:**  
> Build a feature-rich PostgreSQL backend for OmniQ supporting full task, result, and event storage and querying.
>
> **Requirements:**  
> - Use `asyncpg` for all async operations.
> - Design efficient schemas for tasks (with named queues, priority, TTL), results, events (no serialization).
> - Implement robust task locking (e.g., row-level locking with `FOR UPDATE SKIP LOCKED`), transactions, and cleanup of expired tasks/results.
> - Support schedule state, querying, and indexed access.
> - Both async and sync interfaces.
> - Test thoroughly using `pytest-asyncio`.
>
> **Context from Project Plan:**  
> - Follow all “Storage Strategy", “Event Architecture” and “Fault Tolerance” details.
>
> **Dependencies:**  
> - Builds on core abstractions and serialization systems.
>
> **Deliverables:**  
> - PostgreSQL backend implementation and supporting tests in `src/omniq/storage/postgres.py`.

---

### Subtask 2.4: NATS.io Backend

**Filename:** `@/tasks/09-nats-backend.md`

**Prompt:**
> **Objective:**  
> Implement a high-performance NATS.io backend for streaming distributed task and result messaging in OmniQ.
>
> **Requirements:**  
> - Use `nats-py` for client connections (async-first).
> - Implement named queues via subject prefixes; support queue groups for exclusive task consumption.
> - Provide result and event streaming (reliable receive, replay).
> - Implement task locking as needed using NATS queue semantics.
> - Support TTL and expired task cleanup.
> - Both async and sync interfaces.
> - Test using local/dev NATS servers.
>
> **Context from Project Plan:**  
> - Review “Key Design Decisions: Task Locking” for NATS details.
>
> **Dependencies:**  
> - Must comply with declared task/result/event interfaces.
>
> **Deliverables:**  
> - NATS backend implementation in `src/omniq/storage/nats.py` with full tests.

---

### Subtask 2.5: Redis Backend

**Filename:** `@/tasks/10-redis-backend.md`

**Prompt:**
> **Objective:**  
> Develop a Redis-based backend for task, result, and event storage with OmniQ, supporting distributed concurrency.
>
> **Requirements:**  
> - Use `redis.asyncio` for async implementation.
> - Support queue prefixes for named queues, implement atomic operations for locking and TTL.
> - Store results and events in appropriate Redis structures.
> - Provide task expiration and dead-letter queue for errors/timeouts.
> - Support querying and efficient bulk cleanup.
> - Both async and sync interfaces.
> - Test with `pytest-asyncio` against local and remote Redis.
>
> **Context from Project Plan:**  
> - Pay special attention to “Redis Atomic Operations” notes and distributed task locking.
>
> **Dependencies:**  
> - Build with previous core architecture and serialization.
>
> **Deliverables:**  
> - Redis backend implementation in `src/omniq/storage/redis.py` and thorough tests.

---

### Subtask 2.6: Comprehensive Integration and Documentation

**Filename:** `@/tasks/11-integration-and-documentation.md`

**Prompt:**
> **Objective:**  
> Integrate all implemented backends, ensure unified API, and create comprehensive user and developer documentation.
>
> **Requirements:**  
> - Verify that all core abstractions and interfaces are honored by concrete backends.
> - Create unified entry points (`OmniQ`, `AsyncOmniQ`, backend factories).
> - Ensure YAML/dict/env configuration works for all backends.
> - Write clear usage docs and examples for:  
>   - Async/sync APIs  
>   - All supported backends  
>   - Custom configuration (YAML, object, env)  
>   - Advanced features (cloud, dependency, scheduling)
> - Prepare doctests and sample code.
>
> **Context from Project Plan:**  
> - Use guides and usage examples from the provided project plan as templates.
>
> **Dependencies:**  
> - Relies on all previous tasks.
>
> **Deliverables:**  
> - Integrated, fully documented package; docs and examples in `/docs/` and code in `/src/`.

---

This comprehensive set of prompts covers all aspects of the OmniQ system in a logical, sequential manner, designed to enable seamless extensibility and robust backend support as prescribed in the project plan.