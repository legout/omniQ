<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It uses an "Async First, Sync Wrapped" architecture where core functionality is implemented asynchronously with synchronous wrappers for convenience.

## Development Commands

This project uses `uv` for dependency management and Python environment handling:

- **Project setup**: `uv init` (already done)
- **Install dependencies**: `uv add <package>` 
- **Remove dependencies**: `uv remove <package>`
- **Run tests**: `uv run pytest` (when implemented)
- **Code formatting**: `uv run black src/` (when black is added)
- **Linting**: `uv run ruff check src/` (when ruff is added)
- **Type checking**: `uv run mypy src/` (when mypy is added)
- **Run async tests**: `uv run pytest -m asyncio` (when pytest-asyncio is added)
- **Coverage**: `uv run pytest --cov=omniq` (when pytest-cov is added)
- **Import sorting**: `uv run isort src/` (when isort is added)

### Core Dependencies to Add

- **msgspec**: `uv add msgspec` - High-performance serialization and validation
- **dill**: `uv add dill` - Advanced object serialization beyond pickle
- **fsspec**: `uv add fsspec` - Filesystem abstraction for local and cloud storage
- **pyyaml**: `uv add pyyaml` - YAML file parsing for configuration
- **python-dateutil**: `uv add python-dateutil` - Date and time utilities for scheduling
- **anyio**: `uv add anyio` - Synchronous wrappers library
- **croniter**: `uv add croniter` - Cron-style scheduling implementation

### Optional Storage Backend Dependencies

- **aiosqlite**: `uv add aiosqlite` - Async SQLite database interface
- **asyncpg**: `uv add asyncpg` - Async PostgreSQL database interface
- **redis**: `uv add redis` - Redis client (includes redis.asyncio)
- **nats-py**: `uv add nats-py` - NATS messaging system client

### Optional Cloud Storage Dependencies

- **s3fs**: `uv add s3fs` - S3 filesystem implementation for fsspec
- **adlfs**: `uv add adlfs` - Azure Data Lake filesystem implementation for fsspec
- **gcsfs**: `uv add gcsfs` - Google Cloud Storage filesystem implementation for fsspec

### Development Dependencies

- **pytest**: `uv add --dev pytest` - Testing framework
- **pytest-asyncio**: `uv add --dev pytest-asyncio` - Async testing support
- **pytest-cov**: `uv add --dev pytest-cov` - Test coverage reporting
- **black**: `uv add --dev black` - Code formatting
- **isort**: `uv add --dev isort` - Import sorting
- **mypy**: `uv add --dev mypy` - Static type checking
- **ruff**: `uv add --dev ruff` - Fast Python linter

## Core Architecture

### "Async First, Sync Wrapped" Pattern

All core implementations use async/await with synchronous wrappers using `anyio.from_thread.run()`:

```python
# Async core implementation
class AsyncTaskQueue:
    async def enqueue(self, task): ...
    async def __aenter__(self): 
        await self.connect()
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Sync wrapper  
class TaskQueue:
    def __init__(self, *args, **kwargs):
        self._async_queue = AsyncTaskQueue(*args, **kwargs)
    
    def enqueue(self, task):
        return anyio.from_thread.run(self._async_queue.enqueue(task))
    
    def __enter__(self):
        anyio.from_thread.run(self._async_queue.__aenter__())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        anyio.from_thread.run(self._async_queue.__aexit__(exc_type, exc_val, exc_tb))
```

### Component Separation

OmniQ separates concerns into independent components:
- **Task Queue**: Storage and retrieval of tasks
- **Result Storage**: Storage and retrieval of task results  
- **Event Storage**: Task lifecycle event logging
- **Workers**: Task execution engines
- **Backend**: Unified interface for storage systems

### Module Structure

```
src/omniq/
├── __init__.py
├── models/         # Data models and configuration
│   ├── __init__.py
│   ├── task.py     # Task model with metadata, dependencies, TTL
│   ├── schedule.py # Schedule model with pause/resume capability
│   ├── result.py   # TaskResult model for execution outcomes
│   ├── event.py    # TaskEvent model for lifecycle logging
│   └── config.py   # Configuration models using msgspec.Struct
├── storage/        # Storage interface definitions
│   ├── __init__.py
│   ├── base.py     # Abstract base interfaces
│   ├── file.py     # File storage implementations (fsspec)
│   ├── memory.py   # Memory storage implementations (fsspec)
│   ├── sqlite.py   # SQLite storage implementations (aiosqlite)
│   ├── postgres.py # PostgreSQL storage implementations (asyncpg)
│   ├── redis.py    # Redis storage implementations (redis.asyncio)
│   └── nats.py     # NATS storage implementations (nats.aio)
├── serialization/  # Serialization layer
│   ├── __init__.py
│   ├── base.py     # SerializationDetector and Manager
│   ├── msgspec.py  # MsgspecSerializer for compatible types
│   └── dill.py     # DillSerializer for complex objects
├── queue/          # Task queue implementations
│   ├── __init__.py
│   ├── base.py     # Base queue interfaces
│   ├── file.py     # File-based task queues
│   ├── memory.py   # Memory-based task queues
│   ├── sqlite.py   # SQLite-based task queues
│   ├── postgres.py # PostgreSQL-based task queues
│   ├── redis.py    # Redis-based task queues
│   └── nats.py     # NATS-based task queues
├── workers/        # Worker implementations
│   ├── __init__.py
│   ├── base.py     # Base worker interfaces
│   ├── async.py    # AsyncWorker (native async execution)
│   ├── thread.py   # ThreadWorker (thread pool execution)
│   ├── process.py  # ProcessWorker (process pool execution)
│   └── gevent.py   # GeventWorker (gevent pool execution)
├── events/         # Event system
│   ├── __init__.py
│   ├── logger.py   # AsyncEventLogger and EventLogger
│   └── processor.py # AsyncEventProcessor and EventProcessor
├── config/         # Configuration system
│   ├── __init__.py
│   ├── settings.py # Library settings constants (no OMNIQ_ prefix)
│   ├── env.py      # Environment variable handling (OMNIQ_ prefix)
│   └── loader.py   # ConfigProvider and LoggingConfig
├── backend/        # Backend abstractions
│   ├── __init__.py
│   ├── base.py     # Backend interface
│   ├── file.py     # FileBackend
│   ├── sqlite.py   # SQLiteBackend
│   ├── postgres.py # PostgresBackend
│   ├── redis.py    # RedisBackend
│   └── nats.py     # NATSBackend
└── core.py         # Core OmniQ and AsyncOmniQ implementations
```

## Key Design Principles

1. **Async First, Sync Wrapped**: Core library implemented asynchronously with synchronous wrappers
2. **Separation of Concerns**: Task queue, result storage, and event logging are decoupled and independent
3. **Interface-Driven**: All components implement common interfaces
4. **Storage Independence**: Tasks, results, and events can use different backends independently
5. **Multiple Storage Backends**: File (fsspec), Memory, SQLite, PostgreSQL, Redis, NATS
6. **Multiple Worker Types**: Async, Thread Pool, Process Pool, Gevent
7. **Flexible Configuration**: Code, objects, dictionaries, YAML files, environment variables
8. **Cloud Storage Support**: S3, Azure, GCP through fsspec with optional dependencies
9. **Task Lifecycle Management**: TTL, dependencies, scheduling with pause/resume
10. **Intelligent Serialization**: msgspec + dill dual serialization strategy
11. **Multiple Named Queues**: Priority ordering support across all backends
12. **Event-Driven Architecture**: Non-blocking event logging for task lifecycle tracking

## Storage Backends

- **File**: Uses `fsspec` with support for local, memory, S3, Azure, GCP
- **SQLite**: Using `aiosqlite` for async operations
- **PostgreSQL**: Using `asyncpg` for async operations  
- **Redis**: Using `redis.asyncio` for async operations
- **NATS**: Using `nats.aio` for async operations

## Configuration System

Environment variables use `OMNIQ_` prefix to override settings constants:
- Settings: `BASE_DIR = "default/path"`
- Environment: `OMNIQ_BASE_DIR=/custom/path`

**Key Configuration Variables:**
- `OMNIQ_LOG_LEVEL`: Library logging level (DEBUG, INFO, WARNING, ERROR, DISABLED)
- `OMNIQ_TASK_QUEUE_TYPE`: Queue backend (file, memory, sqlite, postgres, redis, nats)
- `OMNIQ_RESULT_STORAGE_TYPE`: Result storage backend 
- `OMNIQ_EVENT_STORAGE_TYPE`: Event storage backend (sqlite, postgres, file)
- `OMNIQ_DEFAULT_WORKER`: Default worker type (async, thread, process, gevent)
- `OMNIQ_TASK_TTL`: Default time-to-live for tasks in seconds
- `OMNIQ_RESULT_TTL`: Default time-to-live for task results in seconds

## Current State

The project is in early development with:
- Project structure defined in implementation plan
- Basic pyproject.toml configuration
- Empty src/omniq/ directory with py.typed marker
- Comprehensive architecture documentation

## Implementation Priority

Based on the implementation plan, focus on these modules in order:

1. **Core Foundation** (`omniq.models`)
   - Task model with metadata, dependencies, callbacks, and TTL
   - Schedule model with timing logic and pause/resume capability
   - TaskResult model for execution outcomes
   - TaskEvent model for lifecycle logging
   - Configuration models using msgspec.Struct

2. **Serialization Layer** (`omniq.serialization`)
   - SerializationDetector for type compatibility
   - MsgspecSerializer for high-performance serialization
   - DillSerializer for complex Python objects
   - SerializationManager for orchestration

3. **Storage Interfaces** (`omniq.storage.base`)
   - BaseTaskQueue abstract interface
   - BaseResultStorage abstract interface 
   - BaseEventStorage abstract interface
   - Both sync and async method definitions

4. **Configuration System** (`omniq.config`)
   - Settings constants without "OMNIQ_" prefix
   - Environment variable handling with "OMNIQ_" prefix
   - ConfigProvider for loading and validation
   - LoggingConfig for logging setup

5. **Event System** (`omniq.events`)
   - AsyncEventLogger core implementation
   - EventLogger sync wrapper
   - AsyncEventProcessor core implementation
   - EventProcessor sync wrapper
   - Event types: ENQUEUED, EXECUTING, COMPLETE, ERROR, etc.

6. **Worker Layer** (`omniq.workers`)
   - AsyncWorker core implementation
   - Worker sync wrappers (Thread, Process, Gevent)
   - Support for both sync and async tasks
   - Multiple queue processing with priority ordering

7. **Core Orchestrator** (`omniq.core`)
   - AsyncOmniQ main async implementation
   - OmniQ sync wrapper
   - Component coordination and lifecycle management
   - Scheduler integration

8. **Storage Backends Implementation** (after core is complete)
   - File and memory backends (`omniq.queue`, `omniq.storage`)
   - SQLite, PostgreSQL, Redis, NATS backends
   - Backend abstractions (`omniq.backend`)

**Key Implementation Guidelines:**
- Implement async core first, then sync wrappers
- Use `anyio.from_thread.run()` for sync wrappers
- All components should support both sync and async context managers
- Maintain separation between task queue, result storage, and event storage
- Support independent backend configuration for each component type