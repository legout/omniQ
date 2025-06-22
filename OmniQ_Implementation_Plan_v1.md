# Enhanced Implementation Plan for the `OmniQ` Python Library

This plan outlines the development of `OmniQ`, a modular Python task queue library designed for both local and distributed task processing with scheduling, task dependencies, callbacks, event logging, and a dashboard.

---

## 1. Architecture Overview

### Core Design Principles
- **Separation of Concerns**: Task storage, event logging, and execution are decoupled
- **Interface-Driven**: All storage backends implement common interfaces
- **Async-First**: Built around asyncio with sync task support
- **Minimal Dependencies**: Core library uses only standard library + essential packages

### System Architecture
```
TaskQueue (Orchestrator)
├── Task Management Layer
│   ├── Task (data model)
│   ├── Schedule (timing logic)
│   └── TaskDependencyGraph (dependency resolution)
├── Storage Layer
│   ├── Storage Interface (tasks/schedules)
│   └── EventStorage Interface (monitoring)
├── Execution Layer
│   ├── WorkerPool (async/sync execution)
│   └── CallbackManager (lifecycle hooks)
└── Dashboard Layer
    └── WebInterface (Litestar + htpy + datastar-py)
```

### Data Flow
1. Tasks → Storage Backend → TaskQueue → WorkerPool → Execution
2. Events → EventStorage → Dashboard/Monitoring
3. Schedules → Scheduler → Task Creation → Queue

---

## 2. Module Architecture

### 2.1 Core Models (`omniq.models`)
**Purpose**: Define data structures and business logic

**Components**:
- `Task`: Serializable task with metadata, dependencies, callbacks
- `Schedule`: Timing logic (cron, interval, timestamp)
- `TaskResult`: Execution outcome storage
- `TaskEvent`: Event logging data model

**Key Design Decisions**:
- Use `dataclasses` for serialization
- Implement `__hash__` and `__eq__` for dependency tracking
- Store callable references as strings for distributed execution

### 2.2 Storage Interfaces (`omniq.storage`)
**Purpose**: Abstract storage backends for pluggability

**Components**:
- `BaseStorage`: Abstract interface for tasks/schedules
- `BaseEventStorage`: Abstract interface for event logging
- Storage implementations: RAM, SQLite, File, Redis, PostgreSQL, NATS
- EventStorage implementations: SQL, JSON+DuckDB

**Key Design Decisions**:
- Async-first interfaces with sync wrappers
- Connection pooling for distributed backends
- Transaction support for consistency
- Bulk operations for performance

### 2.3 Task Queue Engine (`omniq.queue`)
**Purpose**: Core orchestration and execution logic

**Components**:
- `TaskQueue`: Main orchestrator class
- `WorkerPool`: Async/sync task execution management
- `Scheduler`: Schedule processing and task queuing
- `DependencyResolver`: Graph-based dependency management
- `RetryManager`: Exponential backoff and failure handling

**Key Design Decisions**:
- Event-driven architecture using asyncio queues
- Graceful shutdown with task completion
- Worker isolation with separate contexts
- Circuit breaker pattern for fault tolerance

### 2.4 Event System (`omniq.events`)
**Purpose**: Task lifecycle tracking and monitoring

**Components**:
- `EventLogger`: Central event collection
- `EventProcessor`: Async event handling
- Event types: ENQUEUED, EXECUTING, COMPLETE, ERROR, RETRY, CANCELLED

**Key Design Decisions**:
- Non-blocking event logging
- Structured logging with metadata
- Configurable event retention policies

### 2.5 Dashboard (`omniq.dashboard`)
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

---

## 3. Implementation Tasks with Architecture Context

### Phase 1: Foundation (Weeks 1-2)

**Task 1: Core Models**
- Implement `Task`, `Schedule`, `TaskResult`, `TaskEvent`
- Add serialization support (pickle, json)
- Design dependency tracking mechanisms
- *Architecture*: Foundation for all other components

**Task 2: Storage Interfaces**
- Define `BaseStorage` and `BaseEventStorage` contracts
- Implement connection management patterns
- Add async context manager support
- *Architecture*: Enables pluggable backends

**Task 3: RAM Storage Implementation**
- Build in-memory storage for development/testing
- Implement thread-safe operations
- Add TTL support for results
- *Architecture*: Reference implementation and testing backend

**Task 4: TaskQueue Core**
- Build main orchestrator with worker management
- Implement task queuing and dequeuing
- Add graceful shutdown mechanisms
- *Architecture*: Central coordination point

### Phase 2: Local Persistence (Week 3)

**Task 5: SQLite Storage**
- Design schema for tasks, schedules, events
- Implement migrations and indexing
- Add connection pooling
- *Architecture*: Production-ready local storage

**Task 6: File Storage**
- Implement directory-based task storage
- Add file locking for concurrent access
- Support atomic operations
- *Architecture*: Simple deployment option

**Task 7: Event Storage Backends**
- Build SQL-based event storage
- Implement JSON+DuckDB storage
- Add query optimization
- *Architecture*: Monitoring foundation

### Phase 3: Scheduling & Dependencies (Week 4)

**Task 8: Scheduler Integration**
- Implement schedule processing loop
- Add timezone support and DST handling
- Build schedule persistence layer
- *Architecture*: Temporal task management

**Task 9: Dependency System**
- Build task dependency graph
- Implement cycle detection
- Add parallel execution optimization
- *Architecture*: Complex workflow support

**Task 10: Retry & Fault Tolerance**
- Implement exponential backoff
- Add circuit breaker for storage failures
- Build dead letter queue
- *Architecture*: Production resilience

### Phase 4: Advanced Features (Week 5)

**Task 11: Callback System**
- Implement lifecycle hooks
- Add callback chaining
- Support async callbacks
- *Architecture*: Extensible task behavior

**Task 12: Result Management**
- Build result storage with expiration
- Implement result aggregation
- Add result streaming for large datasets
- *Architecture*: Task output handling

### Phase 5: Distributed Storage (Week 6)

**Task 13: Redis Backend**
- Implement Redis-based storage
- Add pub/sub for real-time updates
- Support Redis Cluster
- *Architecture*: Horizontal scaling

**Task 14: PostgreSQL Backend**
- Build robust SQL storage
- Implement connection pooling
- Add transaction support
- *Architecture*: Enterprise-grade persistence

**Task 15: NATS Backend**
- Implement JetStream integration
- Add subject-based routing
- Support NATS clustering
- *Architecture*: Cloud-native messaging

### Phase 6: Dashboard & Monitoring (Week 7)

**Task 16: Web Dashboard**
- Build Litestar application
- Implement real-time task monitoring
- Add schedule management UI
- *Architecture*: User interface layer

**Task 17: Testing & Integration**
- Write comprehensive test suite
- Add performance benchmarks
- Build integration scenarios
- *Architecture*: Quality assurance

---

## 4. Technical Decisions & Rationale

### Storage Strategy
- **Dual Storage**: Separate task/schedule storage from event logging for performance
- **Interface Abstraction**: Enables easy backend switching and testing
- **Connection Management**: Pooling and reconnection for distributed backends

### Execution Model
- **Async Core**: Built on asyncio for high concurrency
- **Sync Compatibility**: Wrapper for synchronous task execution
- **Worker Isolation**: Separate contexts prevent task interference

### Event Architecture
- **Non-blocking Logging**: Events don't slow down task execution
- **Structured Events**: Rich metadata for monitoring and debugging
- **Pluggable Storage**: SQL for queries, JSON for simplicity

### Fault Tolerance
- **Circuit Breaker**: Prevents cascade failures in distributed storage
- **Retry Logic**: Exponential backoff with jitter
- **Graceful Degradation**: System continues with reduced functionality

---

## 5. Development Approach

### Build Order Rationale
1. **Models First**: Stable data structures enable everything else
2. **Storage Next**: Data persistence before complex logic
3. **Core Engine**: Basic task execution before advanced features
4. **Features Last**: Dependencies, callbacks, scheduling build on core

### Testing Strategy
- Unit tests for each module
- Integration tests for storage backends
- End-to-end tests for complete workflows
- Performance tests for scalability validation

### Dependency Management
- Core library: asyncio, sqlite3 (stdlib)
- Optional dependencies: redis, psycopg2, nats-py, duckdb
- Dashboard: litestar, htpy, datastar-py

---

This architecture provides a solid foundation for building a production-ready task queue system with clear separation of concerns and extensible design patterns.