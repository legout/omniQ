# Change: Modernize and consolidate the test suite

## Why
The repo's tests are currently a set of runnable scripts at the project root, with inconsistent import styles (`src.omniq...` vs package-style imports), `sys.path` manipulation, and time-based sleeps in async scenarios. This makes the suite harder to run consistently (local vs CI), harder to refactor safely, and encourages copy/paste patterns.

## What Changes
- **COMPLETED**: Create `tests/` directory structure with organized categories
  - `tests/api/` - Public API tests
  - `tests/integration/` - End-to-end workflow tests
  - `tests/unit/` - Minimal unit tests for complex logic
  - `tests/utils.py` - Common test utilities (moved to conftest.py)
- **COMPLETED**: Create `conftest.py` with shared fixtures
  - `temp_dir()` fixture for temporary test directories
  - `sqlite_storage()` and `file_storage()` fixtures
  - `queue()` and `worker_pool()` fixtures for easy test setup
- **COMPLETED**: Add pytest configuration (`pytest.ini`)
  - Enable pytest test discovery
  - Configure asyncio support
- **COMPLETED**: Add contract tests for core invariants
  - Atomic claim correctness (TestAtomicClaim)
  - Attempt counting consistency (TestAttemptCounting)
  - Retry budget enforcement (`attempts < max_retries`) (TestRetryBudgetEnforcement)
  - No-double-reschedule (TestNoDoubleReschedule)
- **COMPLETED**: Remove sys.path hacks
  - Tests now use proper package imports (`omniq.*` instead of `src.omniq.*`)
- **IN PROGRESS**: Replace root-level test scripts with organized pytest tests
  - Legacy tests still exist at root (test_*.py)
  - Legacy tests still use `time.sleep()` (acceptable for now)
  - Legacy tests still have duplication (acceptable for now)

## Impact
- **Affected specs**: None (test-only changes)
- **Affected code**: tests/, pytest.ini, existing test_*.py files
- **Benefits**:
  - Maintainability: Easier to navigate and modify test suite
  - Development Speed: Faster CI/CD and test execution
  - Clarity: Clear focus on what the public API should do
  - Simplicity: Less cognitive load for developers
  - **Regression Protection**: Contract tests validate core invariants
- **Risks**:
  - Legacy tests at root still work (no breaking change)
  - Some test duplication exists (acceptable during transition)
  - Some tests still use `time.sleep()` (acceptable for now)

## Non-Goals for v1
- Migrate all legacy tests to pytest (can be v2 work)
- Remove all `time.sleep()` usage (requires extensive refactoring)
- Eliminate all test duplication (can be v2 work)
- Add comprehensive unit tests for all internal components

