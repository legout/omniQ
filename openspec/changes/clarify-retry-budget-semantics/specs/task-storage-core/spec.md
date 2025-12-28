## MODIFIED Requirements

### Requirement: Retry and Rescheduling Support
Storage backends MUST support recording failures and rescheduling tasks for retries and fixed-interval execution.

#### Scenario: Dequeue increments attempts exactly once
- **GIVEN** a task with `status=PENDING` and `attempts=0`
- **WHEN** `dequeue(now)` is called
- **THEN** the backend MUST execute a single atomic transaction that:
  - Updates `status` to `RUNNING`
  - Increments `attempts` to `1`
  - Updates `last_attempt_at` to now
  - Returns the claimed task
- **AND** MUST NOT execute multiple UPDATE statements for the same task
- **AND** MUST NOT execute separate `transition_status()` calls after initial claim

#### Scenario: Record retryable failure without incrementing attempts
- **GIVEN** a task that has been dequeued with `attempts=1`
- **WHEN** `mark_failed(task_id, error, will_retry=True)` is called
- **THEN** the backend MUST record the error details
- **AND** MUST transition the task to `FAILED` (to represent a completed attempt)
- **AND** MUST preserve `attempts=1` without incrementing
- **AND** MUST support rescheduling by updating `eta` and transitioning the task back to `PENDING`.
