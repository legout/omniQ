# Change: Clarify and normalize retry budget semantics across layers

## Why
The system currently lacks a crisp definition of `max_retries` vs `attempts`, causing:
- Inconsistent retry predicates (`<=` vs `<` in queue vs models)
- Ambiguous attempt counting (increment on dequeue vs on completion)
- Double retry logic across worker and queue layers
- Non-deterministic retry behavior under failure

## What Changes
- Define `attempts` as number of claimed executions (starts at 0, increments on each PENDING→RUNNING transition)
- Define `max_retries` as maximum total executions allowed
- Standardize retry predicate to `attempts < max_retries` across all components
- Establish queue as single source of truth for retry policy (backoff computation, eta scheduling)
- Remove worker-side retry delay computation (worker delegates to queue)

## Impact
- **Affected specs**: task-queue-core, task-storage-core, worker-pool-core
- **Affected code**: queue.py, worker.py, storage/*.py, models.py
- **Breaking**: None (clarifies existing intended behavior)
- **Risk**: Low (restores consistency to spec compliance)

