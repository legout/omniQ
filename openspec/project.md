# Project Context

## Purpose
OmniQ is an async-first, lightweight Python task queue library.  
Its primary goal is to provide a simple, embeddable job queue and worker system for Python applications without the complexity of heavyweight distributed frameworks.  
v1 focuses on a minimal but solid core: enqueueing tasks, executing them via an async worker pool, storing results, and supporting basic scheduling and retries, with clear extension points for more advanced backends and features later.

## Tech Stack
- Python (>= 3.13)
- Asyncio (async-first core APIs)
- msgspec (serialization)
- cloudpickle (unsafe serialization mode)
- aiosqlite (for SQLite storage backend)
- Local filesystem / fsspec (for file-based storage, optional)
- Hatchling / pyproject.toml for packaging
- Pytest (planned, for testing)

## Project Conventions

### Code Style
- Prefer clear, typed, modern Python (3.13+), with type hints on public APIs.
- Async-first: core classes and methods are `async`, with explicit sync wrappers where needed.
- Class naming:
  - Async core types use the `Async` prefix (e.g., `AsyncOmniQ`, `AsyncWorkerPool`).
  - Sync wrappers drop the prefix (e.g., `OmniQ`, `WorkerPool`).
- Methods on sync wrappers call into async implementations using a small, centralized helper (e.g., anyio or a dedicated runner).
- Use descriptive, non-abbreviated names for public APIs; avoid one-letter variables except for trivial loops.
- Formatting and linting will follow standard tools (e.g., black/ruff) once configured; until then, keep style consistent and simple.

### Architecture Patterns
- Async-first core with thin sync interfaces.
- Clear separation between:
- Public interface (`AsyncOmniQ` / `OmniQ`)
  - Queue/worker engine (`AsyncTaskQueue`, `AsyncWorkerPool`)
  - Storage backends (`BaseStorage` with file/SQLite implementations)
  - Serialization and configuration helpers
- Storage is abstracted behind a small `BaseStorage` interface so new backends (Redis, Postgres, NATS, cloud storage) can be added later without changing the core API.
- v1 intentionally keeps a small module layout (single `omniq` package with a few focused modules) and avoids unnecessary layering until real complexity justifies it.

### Testing Strategy
- Use pytest for unit and integration tests.
- Focus initial tests on:
  - Task lifecycle (enqueue → run → result).
  - Retry and timeout behavior.
  - File and SQLite storage behavior (including edge cases, like empty queues and failures).
  - Worker pool concurrency behavior (basic happy-path and failure scenarios).
- Prefer small, deterministic tests; avoid networked or long-running integration tests in v1.
- Aim for good coverage around public APIs and core storage/worker logic before adding advanced features.

### Git Workflow
- Default branch: `main`.
- Use feature branches for non-trivial work; keep changes scoped and focused.
- Commit messages should be clear and action-oriented (e.g., `add file storage backend`, `implement async worker pool`).
- For larger or behavior-changing work, use OpenSpec changes (`openspec/changes/<change-id>/`) with a proposal and tasks before implementing.

## Domain Context
- OmniQ is a task queue library, not a full workflow orchestrator in v1.
- The primary domain concepts are:
  - Tasks: Python callables plus arguments, scheduled for later execution.
  - Task results: persisted outcomes of task execution (success or failure).
  - Storage backends: mechanisms to persist tasks and results (file/SQLite in v1).
  - Worker pools: async workers that pull tasks from storage and execute them.
- Advanced features like DAG-style dependencies, cron scheduling, multiple distributed backends, and detailed event logging are intentionally deferred to later versions.

## Important Constraints
- Must remain lightweight and easy to embed in a single Python process or small-scale deployment.
- v1 must not depend on heavy external infrastructure (no mandatory Redis, NATS, or external databases beyond SQLite).
- Public APIs should be stable enough to extend later without breaking early adopters wherever possible.
- Unsafe serialization (cloudpickle) is available as an explicit opt-in mode and must never be used with untrusted or multi-tenant inputs; the default remains msgspec-based safe serialization.

## External Dependencies
- No required external network services in v1.
- Optional use of SQLite (via `aiosqlite`) for persistent storage.
- Optional use of fsspec-compatible filesystems in the future (e.g., S3, Azure, GCS) via additional dependencies, but these are not required for v1.
