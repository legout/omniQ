# OmniQ v1 Implementation Order

This document outlines the recommended implementation order for OmniQ v1 change proposals, considering dependencies, logical flow, and development efficiency.

## Summary

| Phase | Change Proposal | Status | Dependencies | Priority |
|-------|----------------|--------|-------------|----------|
| 1 | Core Task Queue | ✅ Complete | None | High |
| 2 | Storage Abstraction + File Backend | 🔄 Mostly Complete | Core Task Queue | High |
| 3 | SQLite Storage Backend | ⏳ Pending | Storage Abstraction | High |
| 4 | Public API, Config & Serialization | ⏳ Pending | Storage Abstraction | High |
| 5 | Async Worker Pool | ⏳ Pending | Public API, Storage | High |

## Phase 1: Core Task Queue ✅ COMPLETE

**Change ID:** `add-core-task-queue`
**Status:** All implementation tasks completed
**Impact:** Establishes the foundational task model that all other components depend on

### What's Been Implemented
- Core task models (`Task`, `TaskStatus`, `TaskResult`, `Schedule`) in `src/omniq/models.py`
- Task creation and validation helpers
- Basic status transition logic
- Result handling for success/error cases

### Why This Was First
All other components (storage, worker pool, public API) depend on having a well-defined task model to work with.

---

## Phase 2: Storage Abstraction + File Backend 🔄 MOSTLY COMPLETE

**Change ID:** `add-storage-abstraction-and-file-backend`
**Status:** Implementation complete, tests pending
**Dependencies:** Core Task Queue (✅ Complete)
**Priority:** High

### Remaining Work
- [ ] 3.1 Add tests for `FileStorage` enqueue/dequeue operations
- [ ] 3.2 Add tests for basic scheduling behavior using `FileStorage`

### What This Provides
- `BaseStorage` async interface definition
- `FileStorage` implementation with atomic operations
- Foundation for multiple storage backends

### Why This Is Next
The storage interface is needed by both the worker pool (to fetch/execute tasks) and the public API (to enqueue/retrieve results). The file backend provides an immediate working implementation.

---

## Phase 3: SQLite Storage Backend ⏳ PENDING

**Change ID:** `add-sqlite-storage-backend`
**Dependencies:** Storage Abstraction (🔄 Complete)
**Priority:** High

### Implementation Tasks
- [ ] 1.1 Implement `SQLiteStorage` in `src/omniq/storage/sqlite.py`
- [ ] 1.2 Define and migrate database schema with indexes
- [ ] 1.3 Implement all storage methods using `aiosqlite`
- [ ] 2.1 Add tests for SQLite storage operations
- [ ] 2.2 Add tests for scheduling, retries, and TTL cleanup

### Why This Follows Storage Abstraction
SQLite requires the `BaseStorage` interface to be fully defined and the file backend to serve as a reference implementation.

---

## Phase 4: Public API, Config & Serialization ⏳ PENDING

**Change ID:** `add-public-api-config-and-serialization`
**Dependencies:** Storage Abstraction (🔄 Complete)
**Priority:** High

### Implementation Tasks
- [ ] 1.1 Implement `AsyncOmniQ` and `OmniQ` in `src/omniq/core.py`
- [ ] 1.2 Add sync wrappers with centralized async runner
- [ ] 1.3 Add public re-exports in `src/omniq/__init__.py`
- [ ] 2.1 Define `Settings` type in `src/omniq/config.py`
- [ ] 2.2 Implement environment variable loading
- [ ] 2.3 Document configuration behavior
- [ ] 3.1 Implement serialization protocol and implementations
- [ ] 3.2 Wire serializer selection into settings
- [ ] 3.3 Configure logging with `OMNIQ_LOG_LEVEL` support

### Why This Is Needed Early
The public API is the primary user interface and is needed to test and validate the entire system. It also provides configuration management that other components will use.

---

## Phase 5: Async Worker Pool ⏳ PENDING

**Change ID:** `add-async-worker-pool`
**Dependencies:** Public API, Config & Serialization (⏳ Pending), Storage Abstraction (🔄 Complete)
**Priority:** High

### Implementation Tasks
- [ ] 1.1 Implement `AsyncWorkerPool` with configurable concurrency
- [ ] 1.2 Implement background polling loop
- [ ] 1.3 Add graceful shutdown semantics
- [ ] 2.1 Execute both async and sync callables
- [ ] 2.2 Implement retry handling with exponential backoff
- [ ] 2.3 Handle interval task rescheduling
- [ ] 3.1 Implement sync `WorkerPool` wrapper
- [ ] 3.2 Provide blocking start/stop methods

### Why This Is Last
The worker pool depends on having:
1. Task models (✅ Complete)
2. Storage abstraction (🔄 Complete)
3. Public API for configuration (⏳ Pending)

The worker pool is the execution engine that ties everything together.

---

## Implementation Guidelines

### Development Strategy
1. **Complete Phase 2 tests first** - This unblocks SQLite and worker pool development
2. **Implement phases in parallel where possible** - SQLite and Public API can be developed concurrently once storage abstraction is complete
3. **Test each phase independently** - Each phase should have working tests before moving to the next
4. **Validate integration progressively** - Test how each new phase integrates with completed phases

### Testing Dependencies
- **Phase 2** tests needed for Phase 3 (SQLite) development
- **Phase 3** tests needed for Phase 5 (Worker Pool) development
- **Phase 4** tests needed for end-to-end integration validation

### Risk Mitigation
- **Storage Backend**: Keep the file backend as a fallback during SQLite development
- **Configuration**: Use environment-based config for testing different backends
- **Worker Pool**: Ensure worker pool works with both storage backends

## Estimated Timeline

| Phase | Estimated Effort | Key Risks |
|-------|-----------------|-----------|
| Phase 2 (complete tests) | 1-2 days | File operation edge cases |
| Phase 3 (SQLite) | 3-4 days | Database schema migrations, concurrency |
| Phase 4 (Public API) | 2-3 days | API design, configuration validation |
| Phase 5 (Worker Pool) | 4-5 days | Async execution, retry logic, graceful shutdown |

**Total Estimated Effort:** 10-14 days

## Success Criteria

Each phase is considered complete when:
- [ ] All implementation tasks are finished
- [ ] All tests pass
- [ ] Integration tests with previous phases work
- [ ] Documentation is updated
- [ ] OpenSpec validation passes

## Next Steps

1. **Immediate:** Complete Phase 2 tests
2. **Week 1:** Implement Phase 3 (SQLite) and Phase 4 (Public API) in parallel
3. **Week 2:** Implement Phase 5 (Worker Pool) and conduct integration testing
4. **Week 3:** End-to-end testing, documentation, and OpenSpec archiving