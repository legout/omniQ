## 1. SQLite Storage Implementation
- [ ] 1.1 Implement `SQLiteStorage` in `src/omniq/storage/sqlite.py` conforming to `BaseStorage`.
- [ ] 1.2 Define and migrate a minimal schema for `tasks` and `results` with appropriate indexes.
- [ ] 1.3 Implement enqueue, dequeue, mark_running, mark_done, mark_failed, get_result, purge_results, and optional reschedule methods using `aiosqlite`.

## 2. Tests and Validation
- [ ] 2.1 Add tests covering enqueue/dequeue and mark_* operations for `SQLiteStorage`, including empty-queue behavior.
- [ ] 2.2 Add tests verifying basic scheduling (`eta`), retries, and TTL cleanup behavior using the SQLite backend.

