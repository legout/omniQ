# OpenSpec Implementation Order (Current Active Changes)

This document describes the recommended implementation order for the current active OpenSpec changes in `openspec/changes/`, and which ones can be implemented in parallel with low merge-risk.

## Active Change Set
- `fix-retry-state-machine-consistency`
- `implement-worker-concurrency`
- `refactor-sqlite-storage-backend`
- `update-public-api-docs`
- `consolidate-test-code-bloat`

## Recommended Order (Single-Threaded)

### 1) `fix-retry-state-machine-consistency`
**Why first**
- Fixes a hard correctness bug (FileStorage retries can fail depending on ordering).
- Defines/aligns the lifecycle contract (attempt counting, RUNNING marking, retry reschedule) that other changes should build on.

**Primary touched areas**
- `src/omniq/queue.py`, `src/omniq/storage/file.py`, and (likely) parts of `src/omniq/models.py`.

**Exit criteria**
- FileStorage + queue retry flow is correct and consistent with the simplified status machine.

### 2) `implement-worker-concurrency`
**Why second**
- Worker behavior is currently misleading (`concurrency` isn’t honored), and fixing it early makes downstream behavior-based tests meaningful.
- Low overlap with sqlite work (mostly contained to worker code).

**Primary touched areas**
- `src/omniq/worker.py` (and minimal wiring in `src/omniq/core.py` if needed).

**Exit criteria**
- `AsyncWorkerPool` runs up to `N` tasks concurrently and stops cleanly.
- `WorkerPool.start()` semantics match the updated spec (non-blocking startup).

### 3) `refactor-sqlite-storage-backend`
**Why third**
- SQLite changes should match the finalized lifecycle rules from (1) (attempt increment once per claim; avoid double mark_running).
- It’s a deep refactor; doing it after the lifecycle contract is settled reduces churn.

**Primary touched areas**
- `src/omniq/storage/sqlite.py`, `src/omniq/storage/_async_sqlite.py`.

**Exit criteria**
- `SQLiteStorage.dequeue()` is single-path, transaction-safe, and consistent with attempt semantics.
- Async sqlite strategy is reliable (aiosqlite with timeouts and/or a complete sqlite3+executor fallback).

### 4) `consolidate-test-code-bloat`
**Why fourth**
- Converting tests to pytest before (1–3) stabilizes risks rework.
- After core behavior settles, test rewrites can encode the “new truth” once.

**Exit criteria**
- Tests run via pytest without `sys.path` hacks and without timing flakiness.

### 5) `update-public-api-docs`
**Why last**
- The README and spec text should reflect the final behavior and any API adjustments made while implementing (1–4).
  - If implementation of (1–3) triggers any API surface decisions, docs should follow the implemented truth.

**Exit criteria**
- README/examples/OpenSpec are aligned with the actual façade behavior (`enqueue` callable vs string decision).

## Parallel Implementation (Low Merge-Risk Workstreams)

You can implement some changes in parallel if you keep the workstreams mostly disjoint:

### Workstream A (Queue/Retry)
- Implement: `fix-retry-state-machine-consistency`
- Avoid editing: `src/omniq/worker.py` and sqlite modules unless required by the retry contract

### Workstream B (Worker)
- Implement: `implement-worker-concurrency`
- Avoid editing: `src/omniq/storage/*` and queue retry logic

### Workstream C (SQLite)
- Implement: `refactor-sqlite-storage-backend`
- Coordinate with Workstream A on attempt-counting + RUNNING-marking semantics to avoid conflicting behavior

### Workstream D (Docs/Tests)
- Safer after Workstreams A–C land, but can start earlier with scaffolding:
  - Create pytest structure + minimal conftest without touching behavior-heavy tests yet
  - Avoid rewriting retry/worker/sqlite behavior tests until A–C stabilize

## Practical Merge Guidance
- Do **not** run “mass reformat” or broad file moves while core behavior is still changing.
- Prefer small PRs per change-id; land (1) before making attempt semantics assumptions in sqlite or worker tests.
- [ ] TaskError model implemented and tested
- [ ] All storage backends support new interface

### After Phase 2:
- [ ] Existing user code works without changes
- [ ] Full v1 API compliance achieved
- [ ] Configuration and serialization work correctly
- [ ] Migration path is clear for users

### After Phase 3:
- [ ] Performance improvements validated (≥40% improvement)
- [ ] Status transitions simplified and tested
- [ ] All tests passing with >90% coverage
- [ ] Documentation updated for all changes

## Rollback Considerations

### Phase 1 Changes
- **Storage Interface**: Easy rollback (remove new methods)
- **Task Interval Type**: Complex rollback (model changes, data migration)
- **TaskError Model**: Medium rollback (model changes)

### Phase 2 Changes
- **Worker Compatibility**: Simple rollback (revert constructor)
- **API Compliance**: Medium rollback (multiple config changes)

### Phase 3 Changes
- **Status Transitions**: Simple rollback (revert validation logic)

## Final Notes

This implementation order prioritizes:
1. **Fixing broken functionality first** (storage, task models)
2. **Achieving compliance second** (API, worker compatibility)
3. **Optimizing last** (performance, simplicity)

The order minimizes risk by building functionality incrementally, ensuring each change enables the next one while maintaining system stability throughout the process.
