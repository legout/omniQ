# OmniQ Implementation Order

This document outlines the recommended implementation order for OpenSpec proposals based on their dependencies.

## V1 Compliance Implementation Order (Current Priority)

Since OmniQ already has a working implementation, the immediate priority is achieving v1 compliance through these 5 proposals:

### 1. **Simplify Logging for v1 Compliance** (`simplify-logging-v1-compliance`)
**Priority: Critical** - Highest impact, lowest risk

**Dependencies:** None

**What it fixes:**
- Replaces 300+ line Loguru system with simple Python logging
- Reduces complexity by ~70%
- Improves performance and maintainability
- Meets "simple enough to understand in a day" requirement

**Why first:** Highest impact with lowest risk - removes over-engineering while maintaining functionality.

---

### 2. **Add Core Task Queue Engine** (`add-core-task-queue-engine`)
**Priority: Critical** - Missing core architecture

**Dependencies:** None

**What it adds:**
- `AsyncTaskQueue` class (currently missing)
- Proper task queue architecture
- Core task management functionality
- Foundation for worker coordination

**Why second:** Fixes critical missing component required by v1 PRD.

---

### 3. **Fix v1 API Compliance** (`fix-v1-api-compliance`)
**Priority: High** - API violations

**Dependencies:** Core Task Queue Engine

**What it fixes:**
- Default serializer (should be "msgspec" not "json")
- Missing `OmniQ.from_env()` constructor
- Incomplete storage backend factory
- Configuration validation issues

**Why third:** Resolves API compliance issues that could cause runtime errors.

---

### 4. **Add Missing Task Models** (`add-missing-task-models`)
**Priority: High** - Incomplete error handling

**Dependencies:** Fix v1 API Compliance

**What it adds:**
- `TaskError` model (missing from PRD)
- Structured error handling throughout codebase
- Consistent error patterns
- Backward compatibility for existing tasks

**Why fourth:** Completes missing models required by v1 specification.

---

### 5. **Simplify Task Status Transitions** (`simplify-task-status-transitions`)
**Priority: Medium** - Performance optimization

**Dependencies:** Add Missing Task Models

**What it fixes:**
- Over-complex status validation (300+ lines → <50 lines)
- Performance improvements (≥40% faster)
- Simplified state machine
- Clearer error messages

**Why fifth:** Optimizes performance and simplicity after core functionality is complete.

---

## Original Implementation Order (For Reference)

*The following order applies to new implementations or major rewrites:*

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

## V1 Compliance Dependency Graph

```
simplify-logging-v1-compliance (independent)
├── add-core-task-queue-engine (independent)
├── fix-v1-api-compliance (depends on core queue)
├── add-missing-task-models (depends on API fixes)
└── simplify-task-status-transitions (depends on task models)
```

## Original Implementation Dependency Graph

```
Core Task Models
├── Storage Abstraction & File Backend
│   ├── Public API, Config & Serialization
│   │   └── Async Worker Pool
│   └── SQLite Storage Backend (parallel)
```

## V1 Compliance Implementation Strategy

### Phase 1: Foundation Cleanup (Steps 1-2)
- Simplify logging system (remove over-engineering)
- Add missing core task queue architecture
- Establishes clean foundation for remaining work

### Phase 2: API Compliance (Steps 3-4)
- Fix API compliance issues and missing constructors
- Add missing TaskError model and error handling
- Ensures public API meets v1 specification

### Phase 3: Optimization (Step 5)
- Simplify status transitions for performance
- Completes v1 compliance goals
- Optimizes for simplicity and maintainability

## Original Implementation Strategy

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
- Completes core task execution loop
- Enables end-to-end functionality

### Phase 4: Additional Features (Step 5)
- Add SQLite backend
- Provides alternative storage option
- Can be developed in parallel with Phase 3

## Notes

### V1 Compliance Notes
- **Steps 1-2 are independent** and can be implemented in parallel
- **Critical path**: Steps 3 → 4 → 5 have dependencies
- **Testing**: Each step should include comprehensive tests before moving to next
- **Goal**: Achieve 100% v1 compliance while maintaining backward compatibility
- **Timeline**: Estimated 2-3 weeks for full v1 compliance

### General Notes
- **SQLite Backend** could be implemented after Step 2 or in parallel with Steps 3-4 since it's an alternative storage implementation.
- Each step should include comprehensive tests before moving to the next.
- The order minimizes blocking dependencies while ensuring each step builds on a solid foundation.
- This approach allows for incremental delivery and testing of functionality.