## 1. Spec
- [x] Define `attempts` and `max_retries` semantics in proposal.md
- [x] Add explicit definitions in spec deltas
- [x] Create invariant table for retry budget in worker-pool-core spec

## 2. Implementation
- [x] Fix retry predicate in queue.py (`<=` → `<`)
- [x] Ensure models.py uses `<` consistently
- [x] Remove worker-side `_calculate_backoff()` method (dead code cleanup)
- [x] Update worker logging to use queue-computed eta (not worker-calculated)
- [x] Update all docs/examples to clarify retry budget semantics
  - README.md lines 311-353 have comprehensive retry budget documentation
  - Examples demonstrate correct semantics

## 3. Tests
- [x] Add tests validating invariant table across queue/storage/worker
  - Created invariant-coverage.md documenting all test coverage
- [x] Verify attempts increment exactly once per dequeue
  - tests/integration/test_contract_invariants.py::TestAtomicClaim
- [x] Verify retry predicate `<` works correctly (no off-by-one errors)
  - tests/integration/test_contract_invariants.py::TestRetryBudgetEnforcement
- [x] Verify queue computes retry delay, not worker
  - tests/integration/test_queue_retry.py::test_exponential_backoff
