## MODIFIED Requirements

### Requirement: Retry and Rescheduling Support
Storage backends MUST support recording failures and rescheduling tasks for retries and fixed-interval execution.

#### Scenario: Record retryable failure and reschedule
- **GIVEN** a task that failed during an execution attempt
- **WHEN** the system records the failure as retryable
- **THEN** the backend MUST persist the failure details
- **AND** MUST transition the task to `FAILED` (to represent a completed attempt)
- **AND** MUST support rescheduling by updating `eta` and transitioning the task back to `PENDING`.
- **AND** MUST NOT increment `attempts` when recording failure (only increment on PENDING→RUNNING transition)

#### Scenario: Reschedule task for future attempt
- **GIVEN** a task that should be retried after a delay
- **WHEN** `BaseStorage.reschedule(task_id, new_eta)` is called
- **THEN** the backend MUST set `eta` to `new_eta` and set `status=PENDING`
- **AND** MUST ensure the task is not dequeued before `new_eta`
- **AND** MUST preserve attempt counters and retry metadata.

### Requirement: Attempt Counting Consistency
Storage backends MUST increment attempts exactly once per claimed execution.

#### Scenario: Dequeue increments attempts atomically
- **GIVEN** a task with `status=PENDING` and `attempts=0`
- **WHEN** `dequeue(now)` is called
- **THEN** the backend MUST execute a single atomic transaction that:
  - Updates `status` to `RUNNING`
  - Increments `attempts` to `1`
  - Updates `last_attempt_at` to now
  - Returns the claimed task
- **AND** MUST NOT execute multiple UPDATE statements for the same task
- **AND** MUST NOT execute separate `transition_status()` calls after the initial claim
