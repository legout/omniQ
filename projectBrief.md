# Brief Project Description

The goal of this project is to develop the python library `OmniQ`, a modular Python task queue library designed for both local and distributed task processing with scheduling, task dependencies, callbacks, event logging, and a dashboard.

---

## 1. Architecture Overview

### Core Design Principles
- **Dual Interface**: Provide both sync and async APIs throughout the library
- **Separation of Concerns**: Task storage, result storage, and event logging are decoupled and independent
- **Interface-Driven**: All components implement common interfaces
- **Storage Abstraction**: Use `obstore` for file and memory storage with extended capabilities
- **Worker Flexibility**: Support multiple worker types (async, thread, process, gevent)
- **Serialization Strategy**: Intelligent serialization with `msgspec` and `dill` for task enqueuing/dequeuing
- **Storage Independence**: Allow independent selection of storage backends for tasks, results, and events
- **SQL-Based Event Logging**: Use SQL or structured storage for efficient event querying and analysis
- **Task Lifecycle Management**: Support task TTL and automatic cleanup of expired tasks
- **Flexible Scheduling**: Enable pausing and resuming of scheduled tasks


### Data Flow
1.Tasks → Serialization → Task Storage Backend → TaskQueue → Worker Selection → Execution → Result Serialization → Result Storage Backend
2. Events → SQL-based Event Storage → Dashboard/Monitoring
3. Schedules → Scheduler → Task Creation → Queue


## 2. Module Architecture

### 2.1 Core Models (`omniq.models`)
**Purpose**: Define data structures and business logic

**Components**:
- `Task`: Serializable task with metadata, dependencies, callbacks, and TTL
- `Schedule`: Timing logic (cron, interval, timestamp) with pause/resume capability
- `TaskResult`: Execution outcome storage
- `TaskEvent`: Event logging data model

**Key Design Decisions**:
- Use `msgspec.Struct` for high-performance serialization
- Support both async and sync callable references
- Implement `__hash__` and `__eq__` for dependency tracking
- Store task metadata for tracking and monitoring
- Define clear result states (pending, running, success, error)
- Include TTL for automatic task expiration
- Support schedule state management (active, paused)

### 2.2 Storage Interfaces (`omniq.storage`)
**Purpose**: Abstract storage backends for pluggability

**Components**:
- `BaseTaskStorage`: Abstract interface for task storage with both sync and async methods
- `BaseResultStorage`: Abstract interface for result storage with both sync and async methods
- `BaseEventStorage`: Abstract interface for event logging (SQL-based only)
- Task and Result Storage implementations:
  - `FileStorage`: Using `obstore` for local and cloud storage (S3, Azure, GCP)
  - `MemoryStorage`: Using `obstore.MemoryStore` instead of custom RAM storage
  - `SQLiteStorage`: Local database storage
  - `PostgresStorage`: Distributed database storage (async)
  - `RedisStorage`: Distributed cache storage (async)
  - `NATSStorage`: Message queue storage (async)
- Event Storage implementations:
  - `SQLiteEventStorage`: Local database event storage
  - `PostgresEventStorage`: Distributed database event storage
  - `FileEventStorage`: JSON files with DuckDB querying

**Key Design Decisions**:
- Use `obstore` for file and memory storage backends
- Implement both sync and async interfaces for all storage backends
- Connection pooling for distributed backends
- Transaction support for consistency
- Bulk operations for performance
- Allow independent selection of storage backends for tasks, results, and events
- Default to using the same backend type for tasks and results if not explicitly specified
- Restrict event storage to SQL-based backends for efficient querying
- Support task TTL enforcement and cleanup in all storage backends
- Store schedule state (active/paused) in storage backends

### 2.3 Serialization Layer (`omniq.serialization`)
**Purpose**: Task and result serialization for storage and retrieval

**Components**:
- `SerializationDetector`: Type compatibility detection
- `MsgspecSerializer`: Primary serializer for compatible types
- `DillSerializer`: Fallback serializer for complex objects
- `SerializationManager`: Orchestrates serialization strategy

**Key Design Decisions**:
- Use the same serialization approach for tasks and results
- Use `msgspec` as primary serializer for performance
- Fall back to `dill` for complex Python objects
- Store serialization format with data for proper deserialization
- Implement security measures for `dill` deserialization

### 2.4 Task Queue Engine (`omniq.queue`)
**Purpose**: Core orchestration and execution logic

**Components**:
- `AsyncTaskQueue`: Async implementation of task queue
- `SyncTaskQueue`: Sync wrapper around async implementation
- `Scheduler`: Schedule processing and task queuing with pause/resume capability
- `DependencyResolver`: Graph-based dependency management
- `RetryManager`: Exponential backoff and failure handling
- `TTLManager`: Task expiration and cleanup

**Key Design Decisions**:
- Event-driven architecture using asyncio queues
- Provide synchronous wrappers for all operations
- Graceful shutdown with task completion
- Circuit breaker pattern for fault tolerance
- Support multiple storage backends
- Independent configuration of task and result storage backends
- Implement task TTL enforcement and cleanup
- Support schedule pausing and resuming

### 2.5 Worker Layer (`omniq.workers`)
**Purpose**: Task execution with multiple worker types

**Components**:
- `WorkerPool`: Worker management and task distribution
- Worker implementations:
  - `AsyncWorker`: Native async execution
  - `ThreadWorker`: Thread pool execution
  - `ProcessWorker`: Process pool execution
  - `GeventWorker`: Gevent pool execution

**Key Design Decisions**:
- Support multiple worker types for different workloads
- Handle both sync and async tasks appropriately
- Implement common interface for all worker types
- Provide proper resource management and cleanup
- Worker selection based on task requirements
- Result serialization and storage after task completion
- Respect task TTL during execution

### 2.6 Event System (`omniq.events`)
**Purpose**: Task lifecycle tracking and monitoring

**Components**:
- `EventLogger`: Central event collection with configurable levels
- `EventProcessor`: Async event handling
- Event types: ENQUEUED, EXECUTING, COMPLETE, ERROR, RETRY, CANCELLED, EXPIRED, SCHEDULE_PAUSED, SCHEDULE_RESUMED

**Key Design Decisions**:
- Non-blocking event logging with disable option
- Structured logging with metadata
- Configurable event retention policies
- Runtime logging level adjustment (DEBUG, INFO, WARNING, ERROR, DISABLED)
- Support both sync and async event handling
- SQL-based storage for efficient querying and analysis
- Track task TTL events and schedule state changes


### 2.7 Dashboard (`omniq.dashboard`)
**Purpose**: Web interface for monitoring and management

**Components**:
- `DashboardApp`: Litestar application
- `TaskViews`: Real-time task monitoring
- `ScheduleViews`: Schedule management
- `MetricsViews`: Performance statistics

**Key Design Decisions**:
- Server-sent events for real-time updates
- Reactive UI with datastar-py
- RESTful API for programmatic access
- Comprehensive task and worker monitoring
- Result inspection and visualization
- Schedule management with pause/resume controls
- Task TTL visualization and management

### 2.8 Configuration (`omniq.config`)
**Purpose**: Centralized configuration management

**Components**:
- `EnvConfig`: Environment variable configuration
- `ConfigProvider`: Configuration loading and validation
- `LoggingConfig`: Logging configuration

**Key Design Decisions**:
- Environment variables as primary configuration method
- Type conversion and validation for config values
- Component-specific configuration sections
- Runtime configuration changes
- Independent configuration of task, result, and event storage
- Configuration for default task TTL