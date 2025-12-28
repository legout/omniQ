# Change: Modernize and consolidate the test suite

## Why
The repo’s tests are currently a set of runnable scripts at the project root, with inconsistent import styles (`src.omniq...` vs package-style imports), `sys.path` manipulation, and time-based sleeps in async scenarios. This makes the suite harder to run consistently (local vs CI), harder to refactor safely, and encourages copy/paste patterns.

## Summary
Convert the existing test scripts into a small pytest suite organized by behavior (API, storage, worker, models), reduce duplication with shared helpers/fixtures, and make async timing deterministic.

## What Changes
- Move root-level test scripts into `tests/` and run them with pytest
- Standardize imports to use the package surface (`omniq.*`) consistently
- Replace `time.sleep()` with deterministic async-friendly patterns (timeouts, event coordination, controllable clock where practical)
- Consolidate repeated setup (temp dirs, settings, storage creation) into fixtures/helpers
- Keep coverage focused on public behavior (task lifecycle, retries, interval scheduling, concurrency) while retaining minimal unit tests for complex logic (e.g., status transitions)

## Problem Statement

### Current Test Code Issues
- Tests are root-level scripts, not a pytest suite
- Inconsistent imports and `sys.path` manipulation
- Use of sleeps in async tests makes results timing-sensitive
- Repeated boilerplate for temp dirs, storage setup, and fixtures

## Proposed Solution (v1-appropriate)

### 1. Shared fixtures/helpers
Create small helpers/fixtures for:
- temp storage dirs
- settings creation (file/sqlite)
- queue/worker creation
- deterministic async waiting (timeouts, events)

### 2. Behavior-oriented organization
Organize tests by user-visible behavior:
- API façade behavior (`AsyncOmniQ`/`OmniQ`)
- Storage behavior (file/sqlite)
- Queue behavior (retry/interval)
- Worker behavior (concurrency/shutdown)

### 3. Parameterize only where it pays off
Use pytest parametrization for:
- file vs sqlite backends
- serializer choice (json/msgspec/cloudpickle)
Avoid combinatorial explosion; keep the suite fast and deterministic.

### 4. Test layout (proposed)
```
tests/
  conftest.py
  api/
  storage/
  queue/
  worker/
  unit/
```

### 5. “Consolidation” means deduplication, not fewer checks
The goal is not to reduce coverage, but to reduce repeated boilerplate and make tests reliable.

## Impact Analysis

### Benefits
- **Maintainability**: Easier to navigate and modify test suite
- **Development Speed**: Faster CI/CD and test execution
- **Clarity**: Clear focus on what the public API should do
- **Simplicity**: Less cognitive load for developers

### Risks
- **Coverage Reduction**: Some edge cases may not be tested
- **Refactoring Flexibility**: Less internal testing may make some refactoring harder
- **Legacy Tests**: Some existing tests may need to be rewritten

## Implementation Plan

### Phase 1: Test Utilities Creation
1. Create common test utilities and patterns
2. Extract repeated test setup code
3. Create parameterized test helpers

### Phase 2: Test Organization
1. Reorganize test files by functionality
2. Remove implementation detail tests
3. Focus tests on public API behavior

### Phase 3: Code Consolidation
1. Merge duplicate test patterns
2. Create parameterized tests
3. Remove redundant edge case tests

## Success Criteria
- [ ] Tests run via `pytest` in a clean environment
- [ ] No `sys.path` hacks required for tests to import the package
- [ ] Retry/interval/concurrency tests are deterministic (no flaky sleeps)
- [ ] Test organization is behavior-based and easy to navigate

## Files to Change

### New Test Structure
- `tests/api/` - Public API tests
- `tests/integration/` - End-to-end tests
- `tests/unit/` - Minimal unit tests for complex logic
- `tests/utils.py` - Common test utilities

### Modified Test Files
- Consolidate existing test files by functionality
- Remove implementation detail tests
- Create parameterized test suites

### Removed Files
- Remove duplicate test patterns
- Remove internal state verification tests
- Remove implementation detail edge case tests

## Testing Strategy

### New Test Approach
1. **Public API Tests**: Comprehensive coverage of external interfaces
2. **Integration Tests**: End-to-end workflow validation
3. **Critical Path Tests**: Focus on most important user scenarios
4. **Error Path Tests**: Verify proper error handling

### Validation
- Run all tests to ensure public API works correctly
- Verify that critical workflows are tested
- Ensure error scenarios are properly handled
- Test performance remains acceptable

## Migration Guide

### For Existing Tests
1. **Identify Implementation Tests**: Mark tests that verify internal state
2. **Review Value**: Keep only tests that verify important behavior
3. **Consolidate**: Merge similar tests using parameterized approach
4. **Update Imports**: Use proper package imports instead of `src.*`

### For Developers
1. **Focus on Public API**: Test what users interact with
2. **Use Utilities**: Leverage common test patterns
3. **Parameterize**: Create parameterized tests for combinations
4. **Simplify**: Remove tests that don't add value

## OpenSpec Validation

```bash
openspec validate --strict
```

## Approval

- [ ] Technical review completed
- [ ] Test coverage analysis done
- [ ] Performance impact assessed
- [ ] Developer workflow impact reviewed
- [ ] Public API testing adequacy confirmed

---

**Change ID**: `consolidate-test-code-bloat`  
**Priority**: HIGH (v1 compliance)  
**Breaking Change**: None (test-only changes)
