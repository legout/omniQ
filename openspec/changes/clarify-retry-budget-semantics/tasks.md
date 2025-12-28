## 1. Spec
- [x] Define `attempts` and `max_retries` semantics in proposal.md
- [x] Add explicit definitions in spec deltas
- [x] Create invariant table for retry budget in worker-pool-core spec

## 2. Implementation
- [x] Fix retry predicate in queue.py (`<=` → `<`)
- [x] Ensure models.py uses `<` consistently
- [x] Remove worker-side `_calculate_backoff()` method (dead code cleanup)
- [ ] Update worker logging to use queue-computed eta (not worker-calculated)
- [ ] Update all docs/examples to clarify retry budget semantics

## 3. Tests
- [ ] Add tests validating invariant table across queue/storage/worker
- [ ] Verify attempts increment exactly once per dequeue
- [ ] Verify retry predicate `<` works correctly (no off-by-one errors)
- [ ] Verify queue computes retry delay, not worker
