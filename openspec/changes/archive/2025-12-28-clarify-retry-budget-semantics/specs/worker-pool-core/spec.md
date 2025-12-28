## MODIFIED Requirements

### Requirement: Retry with exponential backoff
The worker pool MUST delegate retry policy to AsyncTaskQueue.

#### Scenario: Worker delegates retry scheduling
- **GIVEN** a task with `max_retries > 0` that failed during execution
- **AND** a task is eligible for retry (`attempts < max_retries`)
- **WHEN** worker processes the failure
- **THEN** it MUST call `AsyncTaskQueue.fail_task()` to handle retry scheduling
- **AND** MUST NOT compute retry delay independently in worker
- **AND** MUST NOT contain any `_calculate_backoff()` or similar retry computation methods
- **AND** MAY log retry events but MUST use the queue-computed `eta` value

### Requirement: Invariant Table for Retry Semantics
All components MUST use consistent retry budget semantics.

| State | attempts | max_retries | Should Retry? | Next Action |
|-------|----------|--------------|----------------|--------------|
| PENDING | 0 | 3 | N/A | Dequeue and execute |
| RUNNING | 1 | 3 | 1 < 3 = YES | Compute backoff, reschedule |
| PENDING | 1 | 3 | N/A | Dequeue and execute |
| RUNNING | 2 | 3 | 2 < 3 = YES | Compute backoff, reschedule |
| PENDING | 2 | 3 | N/A | Dequeue and execute |
| RUNNING | 3 | 3 | 3 < 3 = NO | Mark FAILED, no retry |

#### Scenario: Verify invariant consistency
- **GIVEN** the invariant table defining retry budget semantics
- **WHEN** any component evaluates whether to retry a task
- **THEN** it MUST use `attempts < max_retries` comparison
- **AND** it MUST increment `attempts` only on PENDING→RUNNING transition
- **AND** it MUST NOT reset or decrement `attempts` for retries
