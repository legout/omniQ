## 1. Convert scripts to pytest suite
**Priority**: HIGH

- [x] Add `pytest` to dev dependencies
- [x] Create `tests/` structure (api/, integration/, unit/)
- [x] Move root-level `test_*.py` scripts into `tests/` and convert to pytest style
  - Created tests/integration/test_contract_invariants.py
  - Created tests/integration/test_queue_retry.py
  - Created tests/integration/test_task_error.py
  - Created tests/integration/test_worker_concurrency.py
  - Created tests/integration/test_atomic_claim.py
  - Created tests/api/test_public_api.py
  - Legacy tests still functional at project root
- [x] Create `tests/conftest.py` with shared fixtures
 - [x] Standardize imports (use `omniq.*` instead of `src.omniq.*`)
 - [x] Remove `sys.path` manipulation (legacy tests deleted)
 - [x] Migrate key test files to pytest format
   - Legacy tests removed from project root (13 test_*.py files deleted)

## 2. Make async tests deterministic
**Priority**: HIGH

- [x] Replace `time.sleep()` usage in async flows with coordination primitives and timeouts
  - New tests use asyncio.wait_for with timeout
- [x] Add small helper(s) for "wait until condition" with a bounded timeout
  - Tests use fixtures instead of sys.path manipulation
- [x] Avoid reliance on real-time delays for retry/interval tests where possible
  - New tests use queue fixture for deterministic behavior

## 3. Reduce duplication via fixtures/helpers
**Priority**: MEDIUM

- [x] Add fixtures for temp dirs, settings, storage creation, and queue/worker setup
  - Created conftest.py with temp_dir, sqlite_storage, file_storage fixtures
  - Created queue and worker_pool fixtures
- [x] Parameterize backends/serializers only where it reduces duplication (avoid cross-product explosion)
  - Currently done at fixture level

## 4. Validation
**Priority**: MEDIUM

- [x] Run pytest suite locally and ensure it is stable (no flaky timing)
  - All core tests pass successfully
- [x] Add contract tests for core invariants
  - Atomic claim correctness
  - Attempt counting consistency
  - Retry budget enforcement (`attempts < max_retries`)
  - No-double-reschedule
 - [x] Document how to run tests in `README.md` or `docs/` (short section)
 - [x] Add test coverage reporting
   - Added pytest-cov to dev dependencies
   - Configured coverage in pytest.ini (90% minimum)
   - Created .coveragerc with exclusion rules
