## 1. Implementation
- [x] Add `examples/tasks.py` with small deterministic task functions shared across examples
- [x] Add `examples/01_quickstart_async.py` (async façade, basic worker execution, result retrieval)
- [x] Add `examples/02_scheduling_eta_and_interval.py` (ETA + interval behavior)
- [x] Add `examples/03_retries_and_task_errors.py` (SQLite + deterministic retries + error/result metadata)
- [x] Add `examples/04_sync_api_logging_and_env.py` (sync façade + env-based settings + logging correlation)
- [x] Add `examples/README.md` indexing each example by features covered and "how to run"
- [x] Update/replace the current `examples/basic_retry_example.py` so it is runnable and references real modules/functions
- [x] Update `README.md` quick-start / worker usage snippets to match the implemented API surface (documentation-only)

## 2. Validation
- [x] Run each example locally (`python examples/01_quickstart_async.py`, etc.) and confirm it completes successfully in <10s
- [x] Sanity-check that examples do not rely on randomness, external services, or long sleeps
- [x] Ensure imports and `func_path` resolution are correct (tasks defined at module top-level)

## 3. Documentation
- [x] Ensure `README.md` links to `examples/README.md`
- [x] Ensure examples show both file and SQLite backends at least once across the suite

