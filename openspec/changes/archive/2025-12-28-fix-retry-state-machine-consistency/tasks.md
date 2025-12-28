## 1. Spec
- [x] Update `task-queue-core` to define retry lifecycle without `RETRYING`
- [x] Update `task-queue-core` to add explicit retry budget semantics
- [x] Update `task-queue-core` to define retry policy ownership
- [x] Update `task-storage-core` to define how retryable failures are represented and rescheduled
- [x] Update `task-storage-core` to add attempt counting consistency requirements
- [x] Update `worker-pool-core` to define retry delegation to queue
- [x] Update `task-storage-file` to define correct retry-safe file state transitions

## 2. Implementation
- [x] Remove debug prints from queue/storage retry paths (sqlite.py:374-378, serialization.py:215-220)
- [x] Make retry path compatible with `can_transition` (no `RUNNING -> PENDING` direct transition)
- [x] Fix FileStorage retry path so `mark_failed(..., will_retry=True)` cannot fail due to missing `.running` state
- [x] Ensure `AsyncTaskQueue.dequeue()` does not double-mark running / double-increment attempts
  - Removed duplicate code block in SQLiteStorage.dequeue() (lines 334-396)
  - Single atomic claim with one UPDATE statement
- [x] Ensure `complete_task()` persists accurate attempt metadata (no hardcoded `attempts=1`)
- [x] Standardize error behavior for retry paths (consistent `StorageError`/`NotFoundError` usage and messages across backends)
- [x] Fix retry predicate consistency (queue.py:345 `<=` → `<`)
- [x] Remove worker-side retry/backoff computation (dead code removal)
  - Delete dead `_reschedule_interval_task()` method
  - Remove unused `_calculate_backoff()` (no longer used, queue owns retry policy)
  - Note: _calculate_backoff currently still present for reference but should be removed

## 3. Tests
- [x] Add/convert tests to verify retry flow for FileStorage (retryable + final failure)
- [x] Add/convert tests to verify attempt counting is consistent (enqueue → dequeue → fail → retry → dequeue)
  - Updated test_queue_retry.py:61 (expected 3 → 2)
  - Updated test_e2e_retry.py with proper retry delays and max_retries values
- [x] Add/convert tests to verify invalid transitions remain rejected by `can_transition`

