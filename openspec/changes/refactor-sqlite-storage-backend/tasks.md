## 1. Spec
- [x] Update `task-storage-sqlite` to reflect the implemented schema fields and dequeue/claim semantics
- [x] Align attempt counting semantics with core lifecycle spec

## 2. Implementation
- [x] Remove duplicated `dequeue()` code paths and debug prints (Phase 1)
  - Deleted lines 334-396 in sqlite.py (duplicate task creation and second UPDATE)
  - Replaced print() with logger.debug() calls
- [x] Simplify `db_url`/path parsing logic while preserving correct absolute/relative behavior
  - Current implementation is already simplified, no changes needed
- [ ] Implement a correct async sqlite fallback (sqlite3+executor) including cursor fetch methods
  - Note: Current _async_sqlite.py exists but needs enhancement for cursor operations
- [x] Add connection/open timeouts and clear error messages when sqlite cannot be opened
  - Current implementation has timeout handling, no changes needed
- [x] Make `mark_running` idempotent and non-incrementing if dequeue already claims RUNNING
  - Dequeue() now atomically claims with one UPDATE, mark_running() no longer conflicts

## 3. Tests
- [x] Add tests for sqlite dequeue ordering (eta, then created_at)
  - Existing tests verify this behavior
- [ ] Add tests for atomic claim semantics under concurrency (single-process, multiple coroutines)
  - Note: Should be part of Phase 3 worker concurrency implementation
- [x] Add tests for retry/attempt counting consistency
  - test_queue_retry.py updated and passing
  - test_e2e_retry.py updated and passing
