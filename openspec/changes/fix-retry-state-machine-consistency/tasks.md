## 1. Spec
- [ ] Update `task-queue-core` to define retry lifecycle without `RETRYING`
- [ ] Update `task-storage-core` to define how retryable failures are represented and rescheduled
- [ ] Update `task-storage-file` to define correct retry-safe file state transitions

## 2. Implementation
- [ ] Remove debug prints from queue/storage retry paths
- [ ] Make retry path compatible with `can_transition` (no `RUNNING -> PENDING` direct transition)
- [ ] Fix FileStorage retry path so `mark_failed(..., will_retry=True)` cannot fail due to missing `.running` state
- [ ] Ensure `AsyncTaskQueue.dequeue()` does not double-mark running / double-increment attempts
- [ ] Ensure `complete_task()` persists accurate attempt metadata (no hardcoded `attempts=1`)
- [ ] Standardize error behavior for retry paths (consistent `StorageError`/`NotFoundError` usage and messages across backends)

## 3. Tests
- [ ] Add/convert tests to verify retry flow for FileStorage (retryable + final failure)
- [ ] Add/convert tests to verify attempt counting is consistent (enqueue → dequeue → fail → retry → dequeue)
- [ ] Add/convert tests to verify invalid transitions remain rejected by `can_transition`
