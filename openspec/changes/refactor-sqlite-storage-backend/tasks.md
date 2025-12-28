## 1. Spec
- [ ] Update `task-storage-sqlite` to reflect the implemented schema fields and dequeue/claim semantics
- [ ] Align attempt counting semantics with core lifecycle spec

## 2. Implementation
- [ ] Remove duplicated `dequeue()` code paths and debug prints
- [ ] Simplify `db_url`/path parsing logic while preserving correct absolute/relative behavior
- [ ] Implement a correct async sqlite fallback (sqlite3+executor) including cursor fetch methods
- [ ] Add connection/open timeouts and clear error messages when sqlite cannot be opened
- [ ] Make `mark_running` idempotent and non-incrementing if dequeue already claims RUNNING

## 3. Tests
- [ ] Add tests for sqlite dequeue ordering (eta, then created_at)
- [ ] Add tests for atomic claim semantics under concurrency (single-process, multiple coroutines)
- [ ] Add tests for retry/attempt counting consistency
