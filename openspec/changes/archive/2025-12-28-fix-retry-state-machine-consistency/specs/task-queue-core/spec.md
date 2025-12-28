## MODIFIED Requirements

### Requirement: Task Status Lifecycle
Task statuses MUST follow a simple, well-defined lifecycle to support retries and observability, using only:
`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`.

#### Scenario: Status transition on failure with retry (simplified state machine)
- **GIVEN** a task in `RUNNING` status with remaining retry budget
- **WHEN** execution raises an error
- **THEN** the system MUST record the failure and transition the task to `FAILED`
- **AND** MUST compute a future retry `eta` using the configured backoff policy
- **AND** MUST reschedule the task for a future attempt by transitioning it back to `PENDING` with the new `eta`
- **AND** MUST NOT make the task due before the new `eta`.

#### Scenario: Status transition on final failure
- **GIVEN** a task in `RUNNING` status that has exhausted its retry budget
- **WHEN** execution raises an error
- **THEN** the system MUST transition the task to `FAILED`
- **AND** MUST persist a corresponding `TaskResult` with `status=FAILED`
- **AND** MUST NOT schedule additional retries.

### Requirement: Retry Budget Semantics
The system MUST use consistent retry budget semantics across all components.

#### Scenario: Attempts count total executions
- **GIVEN** a task with `attempts=0` on enqueue
- **WHEN** the task is dequeued and transitions to `RUNNING`
- **THEN** `attempts` MUST increment to `1`
- **AND** `attempts` MUST represent total number of times task has been claimed for execution
- **AND** MUST NOT decrement or reset attempts for retry tasks

#### Scenario: Retry budget enforcement
- **GIVEN** a task with `max_retries=3` and `attempts=2`
- **WHEN** the task fails and is evaluated for retry
- **THEN** the system MUST allow retry because `2 < 3` evaluates to `True`
- **AND** MUST stop retrying when `attempts=3` because `3 < 3` evaluates to `False`

### Requirement: Retry Policy Ownership
The system MUST define clear ownership boundaries for retry scheduling logic.

#### Scenario: Queue computes retry delay
- **GIVEN** a task has failed and is eligible for retry
- **WHEN** the queue processes the failure
- **THEN** the queue MUST compute the retry delay using exponential backoff
- **AND** MUST calculate the retry `eta` as `now + delay`
- **AND** MUST reschedule the task with the computed `eta`

#### Scenario: Worker delegates to queue
- **GIVEN** a worker processing a failed task
- **WHEN** the worker determines the task should be retried
- **THEN** the worker MUST delegate retry scheduling to `AsyncTaskQueue.fail_task()`
- **AND** MUST NOT compute retry delay independently in the worker
- **AND** MAY log retry events but MUST use the queue-computed `eta` for logging
