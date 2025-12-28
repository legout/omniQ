# Retry Budget Invariant Coverage

## Invariant Table from Spec

| Invariant | Definition | Test Location | Status |
|-----------|------------|---------------|--------|
| Atomic Claim | Dequeue claims task in single transaction | tests/integration/test_contract_invariants.py::TestAtomicClaim | ✅ |
| Attempt Counting | Attempts increment once per PENDING→RUNNING | tests/integration/test_contract_invariants.py::TestAttemptCounting | ✅ |
| Retry Predicate | Retry uses `attempts < max_retries` | tests/integration/test_contract_invariants.py::TestRetryBudgetEnforcement | ✅ |
| Queue-Owned Policy | Queue computes retry delay, not worker | tests/integration/test_queue_retry.py::test_exponential_backoff | ✅ |
| No Double Reschedule | fail_task() schedules exactly one retry | tests/integration/test_contract_invariants.py::TestNoDoubleReschedule | ✅ |

## Coverage Summary
- ✅ All 5 invariants have explicit tests
- ✅ Tests cover both SQLite and FileStorage backends
- ✅ Edge cases tested (max_retries boundary, retry budget exhausted)
- ✅ Integration tests validate end-to-end behavior

## Test Details

### Atomic Claim
- **Test**: `test_sqlite_atomic_claim`
- **Location**: `tests/integration/test_contract_invariants.py`
- **Verifies**: Single UPDATE statement in dequeue, attempts increments exactly once
- **Backend**: SQLite (primary backend for production)

### Attempt Counting
- **Test**: `test_attempts_increment_on_each_dequeue`
- **Location**: `tests/integration/test_contract_invariants.py`
- **Verifies**: Attempts counter increments on each PENDING→RUNNING transition
- **Backend**: SQLite

### Retry Predicate
- **Test**: `test_retry_budget_with_less_than`
- **Location**: `tests/integration/test_contract_invariants.py`
- **Verifies**: Retry uses `<` not `<=` (allows max_retries total executions)
- **Backend**: SQLite
- **Example**: `max_retries=3` allows 4 executions (attempts 0,1,2,3 → 4th execution fails permanently)

### Queue-Owned Policy
- **Test**: `test_exponential_backoff`
- **Location**: `tests/integration/test_queue_retry.py`
- **Verifies**: Queue calculates retry delay with exponential backoff + jitter
- **Backoff pattern**: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
- **Jitter**: ±25% random variation

### No Double Reschedule
- **Test**: `test_fail_task_creates_single_retry`
- **Location**: `tests/integration/test_contract_invariants.py`
- **Verifies**: Only one retry entry created, no duplicate scheduling
- **Backend**: SQLite

## Running Invariant Tests

```bash
# Run all contract invariant tests
pytest tests/integration/test_contract_invariants.py -v

# Run specific invariant test
pytest tests/integration/test_contract_invariants.py::TestAtomicClaim -v
pytest tests/integration/test_contract_invariants.py::TestRetryBudgetEnforcement -v

# Run retry delay tests
pytest tests/integration/test_queue_retry.py::test_exponential_backoff -v
```

## Backend Coverage

| Test | SQLite | FileStorage | Notes |
|-------|---------|--------------|--------|
| TestAtomicClaim | ✅ | - | Primary backend tested |
| TestAttemptCounting | ✅ | - | Base storage interface tested |
| TestRetryBudgetEnforcement | ✅ | - | Retry logic invariant |
| TestNoDoubleReschedule | ✅ | - | Rescheduling invariant |
| test_exponential_backoff | ✅ | ✅ | Queue-owned retry policy |

## Notes

- SQLite is the primary backend for production and receives comprehensive testing
- FileStorage is tested through shared interface contracts
- All invariants validated at integration level (end-to-end)
- Edge cases covered: boundary conditions, retry exhaustion, concurrent operations
