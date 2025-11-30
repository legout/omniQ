# OmniQ Implementation Order

This document outlines the recommended implementation order for the OpenSpec proposals based on their dependencies.

## Implementation Order

### 1. **Core Task Models** (`add-core-task-queue`)
**Priority: High** - Foundation for everything else

**Dependencies:** None

**What it provides:**
- `Task`, `TaskStatus`, `TaskResult`, `Schedule` types
- Task creation and validation helpers
- Result handling helpers
- Status transition logic

**Why first:** All other components depend on having a well-defined task model.

---

### 2. **Storage Abstraction & File Backend** (`add-storage-abstraction-and-file-backend`)
**Priority: High** - Required by worker pool and API

**Dependencies:** Core Task Models

**What it provides:**
- `BaseStorage` async interface
- `FileStorage` implementation
- Atomic file operations for task persistence
- Serialization hooks at storage boundary

**Why second:** Workers and API need a storage backend to function.

---

### 3. **Public API, Config & Serialization** (`add-public-api-config-and-serialization`)
**Priority: High** - Main user interface

**Dependencies:** Core Task Models, Storage Abstraction

**What it provides:**
- `AsyncOmniQ` and `OmniQ` façade classes
- `Settings` model with environment variable support
- Serializer abstraction (msgspec default, cloudpickle opt-in)
- Logging configuration

**Why third:** Provides the main interface users will interact with.

---

### 4. **Async Worker Pool** (`add-async-worker-pool`)
**Priority: High** - Task execution engine

**Dependencies:** Core Task Models, Storage Abstraction, Public API

**What it provides:**
- `AsyncWorkerPool` with configurable concurrency
- Support for async and sync callable execution
- Retry logic with exponential backoff
- Sync `WorkerPool` wrapper

**Why fourth:** The core task execution engine that uses all previous components.

---

### 5. **SQLite Storage Backend** (`add-sqlite-storage-backend`)
**Priority: Medium** - Alternative storage

**Dependencies:** Core Task Models, Storage Abstraction

**What it provides:**
- `SQLiteStorage` implementation
- Transactional task and result storage
- SQL-based querying capabilities

**Why fifth:** Alternative storage backend that can be implemented after core functionality.

## Dependency Graph

```
Core Task Models
├── Storage Abstraction & File Backend
│   ├── Public API, Config & Serialization
│   │   └── Async Worker Pool
│   └── SQLite Storage Backend (parallel)
```

## Implementation Strategy

### Phase 1: Foundation (Steps 1-2)
- Implement core models and storage
- Enables basic task enqueue/dequeue functionality
- Provides foundation for testing

### Phase 2: User Interface (Step 3)
- Add public API and configuration
- Makes the library usable by developers
- Enables integration testing

### Phase 3: Execution Engine (Step 4)
- Implement worker pool
- Completes the core task execution loop
- Enables end-to-end functionality

### Phase 4: Additional Features (Step 5)
- Add SQLite backend
- Provides alternative storage option
- Can be developed in parallel with Phase 3

## Notes

- **SQLite Backend** could be implemented after Step 2 or in parallel with Steps 3-4 since it's an alternative storage implementation.
- Each step should include comprehensive tests before moving to the next.
- The order minimizes blocking dependencies while ensuring each step builds on a solid foundation.
- This approach allows for incremental delivery and testing of functionality.