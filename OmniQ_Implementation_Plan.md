# Enhanced Implementation Plan for the `OmniQ` Python Library

This plan outlines the development of `OmniQ`, a modular Python task queue library designed for both local and distributed task processing with scheduling, task dependencies, callbacks, event logging, and a dashboard.

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

### Enhanced System Architecture
```
TaskQueue (Orchestrator)
├── Interface Layer
│   ├── Async API
│   └── Sync API (wrappers around async)
├── Task Management Layer
│   ├── Task (data model with TTL)
│   ├── Schedule (timing logic with pause/resume)
│   └── TaskDependencyGraph (dependency resolution)
├── Storage Layer
│   ├── Task Storage Interface
│   │   ├── File Storage (using obstore for local/cloud files)
│   │   ├── Memory Storage (using obstore MemoryStore)
│   │   ├── SQLite Storage
│   │   ├── PostgreSQL Storage
│   │   ├── Redis Storage
│   │   └── NATS Storage
│   ├── Result Storage Interface (independent from task storage)
│   │   ├── File Storage (using obstore for local/cloud files)
│   │   ├── Memory Storage (using obstore MemoryStore)
│   │   ├── SQLite Storage
│   │   ├── PostgreSQL Storage
│   │   ├── Redis Storage
│   │   └── NATS Storage
│   └── Event Storage Interface (SQL-based only)
│       ├── SQLite Storage
│       ├── PostgreSQL Storage
│       └── File Storage (JSON + DuckDB)
├── Execution Layer
│   ├── Worker Types
│   │   ├── Async Workers
│   │   ├── Thread Pool Workers
│   │   ├── Process Pool Workers
│   │   └── Gevent Pool Workers
│   ├── Task Execution
│   └── CallbackManager (lifecycle hooks)
└── Dashboard Layer
    └── WebInterface (Litestar + htpy + datastar-py)
```

### Data Flow
1.Tasks → Serialization → Task Storage Backend → TaskQueue → Worker Selection → Execution → Result Serialization → Result Storage Backend
2. Events → SQL-based Event Storage → Dashboard/Monitoring
3. Schedules → Scheduler → Task Creation → Queue

---

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

---

## 3. Implementation Tasks with Architecture Context

### Phase 1: Foundation (Weeks 1-2)

**Task 1: Project Setup and Configuration**
- Initialize project structure and dependencies
- Implement environment variable configuration in `omniq.config`
- Set up logging configuration with levels and component-specific settings
- Configure development tools (pytest, ruff, mypy)
- *Architecture*: Configuration foundation for all components

**Task 2: Core Models**
- Implement `Task`, `Schedule`, `TaskResult`, `TaskEvent` using `msgspec.Struct`
- Add support for both sync and async callable references
- Design dependency tracking mechanisms
- Define result states and transitions
- *Architecture*: Foundation for all other components

**Task 3: Serialization Layer**
- Implement type detection for serializer selection
- Build `msgspec` primary serializer
- Create `dill` fallback serializer
- Add serialization format metadata
- Implement security measures for `dill`
- *Architecture*: Task and result serialization

**Task 4: Storage Interfaces**
- Define `BaseStorage` and `BaseEventStorage` with sync and async methods
- Add result storage methods to `BaseStorage`
- Implement connection management patterns
- Add context manager support for both sync and async
- Create storage factory for backend selection
- *Architecture*: Enables pluggable backends

**Task 5: ObStore Integration**
- Implement file storage using `obstore` for local and cloud storage
- Create memory storage using `obstore.MemoryStore`
- Add support for different storage locations (S3, Azure, GCP)
- Implement both sync and async interfaces
- Add result storage support in obstore backends
- *Architecture*: Enhanced storage capabilities

**Task 6: Worker Interface**
- Define worker protocol with both sync and async methods
- Design worker lifecycle management
- Implement worker factory for type selection
- *Architecture*: Worker abstraction layer

**Task 7: TaskQueue Core**
- Build async task queue implementation
- Create sync wrapper around async implementation
- Implement task enqueueing and dequeueing with serialization
- Add result storage and retrieval
- Add graceful shutdown mechanisms
- *Architecture*: Central coordination point

### Phase 2: Worker Implementation (Week 3)

**Task 8: Async Worker**
- Implement async worker for native async execution
- Add concurrency control and resource management
- Implement result serialization and storage
- Implement graceful shutdown
- *Architecture*: Async task execution

**Task 9: Thread Pool Worker**
- Implement thread pool worker for I/O-bound sync tasks
- Add thread management and lifecycle control
- Handle sync task execution in threads
- Implement result serialization and storage
- *Architecture*: Thread-based execution

**Task 10: Process Pool Worker**
- Implement process pool worker for CPU-bound tasks
- Add process management and communication
- Handle serialization for cross-process tasks
- Implement result serialization and storage
- *Architecture*: Process-based execution

**Task 11: Gevent Pool Worker**
- Implement gevent pool worker for high-concurrency workloads
- Add greenlet management
- Handle cooperative multitasking
- Implement result serialization and storage
- *Architecture*: Gevent-based execution

**Task 12: Worker Pool Management**
- Implement worker pool for task distribution
- Add worker selection based on task requirements
- Create monitoring and health checks
- *Architecture*: Worker orchestration

### Phase 3: Local Persistence (Week 4)

**Task 13: SQLite Storage**
- Design schema for tasks, schedules, events, and results
- Implement migrations and indexing
- Add connection pooling
- Provide both sync and async interfaces
- Implement result table structure and queries
- *Architecture*: Production-ready local storage

**Task 14: Event Storage**
- Build SQL-based event storage
- Implement JSON+DuckDB storage
- Add query optimization
- Support configurable retention policies
- *Architecture*: Monitoring foundation

**Task 15: Result Management**
- Build result storage with expiration
- Implement result aggregation
- Add result streaming for large datasets
- Provide both sync and async result interfaces
- Use the same serialization approach as for tasks
- *Architecture*: Task output handling

### Phase 4: Scheduling & Dependencies (Week 5)

**Task 16: Scheduler Integration**
- Implement schedule processing loop
- Add timezone support and DST handling
- Build schedule persistence layer
- Create both sync and async scheduler interfaces
- *Architecture*: Temporal task management

**Task 17: Dependency System**
- Build task dependency graph
- Implement cycle detection
- Add parallel execution optimization
- Support both sync and async resolution
- *Architecture*: Complex workflow support

**Task 18: Retry & Fault Tolerance**
- Implement exponential backoff
- Add circuit breaker for storage failures
- Build dead letter queue
- Create retry policies and limits
- *Architecture*: Production resilience

**Task 19: Callback System**
- Implement lifecycle hooks
- Add callback chaining
- Support both sync and async callbacks
- Create callback error handling
- *Architecture*: Extensible task behavior

### Phase 5: Distributed Storage (Week 6)

**Task 20: PostgreSQL Backend**
- Build robust async SQL storage
- Implement connection pooling
- Add transaction support
- Create sync wrapper around async implementation
- Implement result tables and queries
- *Architecture*: Enterprise-grade persistence

**Task 21: Redis Backend**
- Implement async Redis-based storage
- Add pub/sub for real-time updates
- Support Redis Cluster
- Create sync wrapper around async implementation
- Implement result storage using hash structures with TTL
- *Architecture*: Distributed cache storage

**Task 22: NATS Backend**
- Implement async NATS storage with JetStream
- Add subject-based routing
- Support NATS clustering
- Create sync wrapper around async implementation
- Implement result storage using KV store or object store
- *Architecture*: Cloud-native messaging

### Phase 6: Dashboard & Monitoring (Week 7)

**Task 23: Web Dashboard**
- Build Litestar application
- Implement real-time task monitoring
- Add schedule management UI
- Create metrics visualization
- Add result inspection and visualization
- *Architecture*: User interface layer

**Task 24: Testing & Integration**
- Write comprehensive test suite for both sync and async interfaces
- Add performance benchmarks
- Build integration scenarios
- Test worker types and storage backends
- Test result storage and retrieval
- *Architecture*: Quality assurance

**Task 25: Documentation & Examples**
- Create comprehensive API documentation
- Write usage examples for both sync and async APIs
- Document worker types and use cases
- Add deployment guides
- *Architecture*: Knowledge sharing

---

## 4. Technical Decisions & Rationale

### Dual Interface Strategy
- **Async Foundation**: Core implementation uses async for performance
- **Sync Wrappers**: Synchronous interfaces wrap async implementations
- **Consistent API**: Similar method signatures between sync and async interfaces
- **Context Management**: Proper resource handling in both interfaces
- **Error Propagation**: Consistent error handling across interfaces

### Storage Strategy
- **ObStore Integration**: Use `obstore` for file and memory storage with extended capabilities
- **Multiple Backends**: Support various storage options for different needs
- **Unified Interface**: Common protocol for all storage backends
- **Dual Interface**: Both sync and async methods for all storage operations
- **Cloud Support**: Seamless support for S3, Azure Blob, and Google Cloud Storage
- **Unified Result Storage**: Store results in the same backend as tasks
- **Backend-Specific Optimizations**: Use specialized features of each backend for result storage

### Serialization Strategy
- **Unified Approach**: Use the same serialization strategy for tasks and results
- **Dual Approach**: Use `msgspec` for performance, `dill` for compatibility
- **Type Detection**: Automatically select appropriate serializer
- **Format Tagging**: Store serialization format with data
- **Security**: Implement signature verification for `dill` deserialization

### Worker Strategy
- **Multiple Worker Types**: Support different execution models
- **Async Workers**: Native async execution for I/O-bound tasks
- **Thread Pool**: Thread-based execution for I/O-bound sync tasks
- **Process Pool**: Process-based execution for CPU-bound tasks
- **Gevent Pool**: Cooperative multitasking for high-concurrency workloads
- **Worker Selection**: Runtime selection based on task requirements
- **Result Handling**: Consistent result serialization and storage across worker types

### Event Architecture
- **Non-blocking Logging**: Events don't slow down task execution
- **Structured Events**: Rich metadata for monitoring and debugging
- **Configurable Levels**: Runtime adjustment of logging levels
- **Dual Interface**: Both sync and async event handling

### Fault Tolerance
- **Circuit Breaker**: Prevents cascade failures in distributed storage
- **Retry Logic**: Exponential backoff with jitter
- **Graceful Degradation**: System continues with reduced functionality
- **Dead Letter Queue**: Store failed tasks for inspection

---

## 5. Development Approach

### Build Order Rationale
1. **Configuration & Models**: Establish foundation with environment variables and data structures
2. **Storage & Serialization**: Build data management layer with `obstore` integration and result storage
3. **Workers & Queue**: Implement task distribution and execution with multiple worker types
4. **Features & Extensions**: Add scheduling, dependencies, callbacks, and retry logic
5. **Distributed Storage**: Implement PostgreSQL, Redis, and NATS backends with result storage
6. **Dashboard & Documentation**: Create monitoring interface and comprehensive documentation

### Testing Strategy
- Unit tests developed concurrently with code (test-driven development)
- Integration tests for storage backends
- Worker-specific tests for different execution models
- Performance benchmarks for critical paths
- Sync and async interface tests
- Result storage and retrieval tests
- Schedule pause/resume functionality tests
- Task TTL enforcement tests

### Dependency Management
- Core library: `obstore`, `msgspec`, `dill`, `asyncio` (stdlib)
- Worker dependencies: `gevent`, `concurrent.futures` (stdlib)
- Storage backends: `asyncpg`, `aioredis`, `nats-py`
- Dashboard: `litestar`, `htpy`, `datastar-py`
- Development: `pytest`, `pytest-asyncio`, `ruff`, `mypy` (managed via uv)

---

## 6. Development Guidelines

### Environment Variable Configuration
- Use environment variables for deployment-specific settings
- Support the following variables:
  - `OMNIQ_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, DISABLED)
  - `OMNIQ_DISABLE_LOGGING`: Disable all logging when set to "1" or "true"
  - `OMNIQ_TASK_STORAGE_TYPE`: Storage backend for tasks (file, memory, sqlite, postgres, redis, nats)
  - `OMNIQ_TASK_STORAGE_URL`: Connection string for task storage backend
  - `OMNIQ_RESULT_STORAGE_TYPE`: Storage backend for results (file, memory, sqlite, postgres, redis, nats)
  - `OMNIQ_RESULT_STORAGE_URL`: Connection string for result storage backend
  - `OMNIQ_EVENT_STORAGE_TYPE`: Storage backend for events (sqlite, postgres, file)
  - `OMNIQ_EVENT_STORAGE_URL`: Connection string for event storage backend
  - `OMNIQ_OBSTORE_URI`: URI for obstore (e.g., "file:///path", "s3://bucket", "memory://")
  - `OMNIQ_DEFAULT_WORKER`: Default worker type (async, thread, process, gevent)
  - `OMNIQ_MAX_WORKERS`: Maximum number of workers
  - `OMNIQ_THREAD_WORKERS`: Thread pool size
  - `OMNIQ_PROCESS_WORKERS`: Process pool size
  - `OMNIQ_GEVENT_WORKERS`: Gevent pool size
  - `OMNIQ_TASK_TIMEOUT`: Default task execution timeout in seconds
  - `OMNIQ_TASK_TTL`: Default time-to-live for tasks in seconds
  - `OMNIQ_RETRY_ATTEMPTS`: Default number of retry attempts
  - `OMNIQ_RETRY_DELAY`: Default delay between retries in seconds
  - `OMNIQ_RESULT_TTL`: Default time-to-live for task results in seconds
  - `OMNIQ_DASHBOARD_PORT`: Web dashboard port number
  - `OMNIQ_DASHBOARD_ENABLED`: Enable/disable dashboard
  - `OMNIQ_COMPONENT_LOG_LEVELS`: JSON string with per-component logging levels

### Context7 MCP and Deepwiki MCP Usage
When implementing tasks involving unfamiliar libraries, use the context7 MCP and deepwiki MCP to:
- **msgspec**: Get advanced serialization patterns and validation examples
- **obstore**: Learn storage abstraction patterns and cloud storage integration
- **gevent/greenlet**: Understand cooperative multitasking patterns
- **nats/nats.py**: Learn advanced messaging patterns
- **litestar**: Understand API routing, dependency injection, and middleware patterns
- **htpy**: Learn component-based UI development and templating
- **datastar/datastar-py**: Understand reactive data binding and state management


### Sync/Async Implementation Guidelines
- **Async First**: Implement core functionality using async
- **Sync Wrappers**: Create synchronous wrappers using `asyncio.run()` or event loops
- **Context Managers**: Implement both `__enter__`/`__exit__` and `__aenter__`/`__aexit__`
- **Error Handling**: Preserve exception context across sync/async boundaries
- **Resource Management**: Ensure proper cleanup in both sync and async contexts

### Worker Implementation Guidelines
- **Common Interface**: All workers implement the same interface
- **Resource Limits**: Configurable concurrency limits for all worker types
- **Graceful Shutdown**: Proper shutdown sequence with task completion
- **Monitoring**: Expose metrics for worker performance and health
- **Task Routing**: Intelligent routing of tasks to appropriate workers
- **Result Handling**: Consistent result serialization and storage across worker types

### Storage Implementation Guidelines
- **Independent Configuration**: Allow separate configuration of task, result, and event storage
- **Default Behavior**: Use the same backend type for tasks and results if not explicitly specified
- **SQL-Based Event Storage**: Restrict event storage to SQL or structured storage options
- **Serialization Consistency**: Use the same serialization approach for tasks and results
- **TTL Support**: Implement expiration for both tasks and results across all backends
- **Backend-Specific Optimizations**: Use specialized features of each backend where appropriate
- **Schedule State Management**: Store schedule state (active/paused) in all backends

### Testing Guidelines
- **Test-Driven Development**: Write unit tests concurrently with code development
- **Test Coverage**: Aim for high test coverage across all components
- **Test Categories**: 
  - Unit tests for individual components
  - Integration tests for backend interactions
  - Functional tests for end-to-end workflows
  - Performance tests for critical paths
- **Test Fixtures**: Create reusable fixtures for common test scenarios
- **Async Testing**: Use pytest-asyncio for testing async code
- **Mock Dependencies**: Use mocks for external dependencies
- **Continuous Testing**: Run tests automatically on code changes

### Example Usage (Async)
```python
from omniq import AsyncTaskQueue, Task

# Create a task queue with async interface
queue = AsyncTaskQueue(
    storage_type="memory",
    worker_type="async",
    max_workers=10
)

# Define an async task
async def my_task(x, y):
    return x + y

# Enqueue task
task_id = await queue.enqueue(my_task, args=(5, 10))

# Get result
result = await queue.get_result(task_id)
print(f"Result: {result}")  # Result: 15
```

### Example Usage (Sync)
```python
from omniq import TaskQueue, Task

# Create a task queue with sync interface
queue = TaskQueue(
    storage_type="sqlite",
    worker_type="thread",
    max_workers=5
)

# Define a sync task
def my_task(x, y):
    return x + y

# Enqueue task
task_id = queue.enqueue(my_task, args=(5, 10))

# Get result
result = queue.get_result(task_id)
print(f"Result: {result}")  # Result: 15
```