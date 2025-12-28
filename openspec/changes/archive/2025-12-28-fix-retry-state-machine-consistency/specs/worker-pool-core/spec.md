## MODIFIED Requirements

### Requirement: Retry with exponential backoff
The worker pool MUST delegate retry policy to AsyncTaskQueue.

#### Scenario: Worker delegates retry scheduling
- **GIVEN** a task with `max_retries > 0` that failed during execution
- **AND** the task is eligible for retry
- **WHEN** the worker processes the failure
- **THEN** it MUST call `AsyncTaskQueue.fail_task()` to handle retry scheduling
- **AND** MUST NOT compute retry delay independently in the worker
- **AND** MAY log retry events using the queue-computed `eta` value

### Requirement: Interval scheduling behavior
The worker pool MUST support fixed-interval tasks using the `interval` field.

#### Scenario: Reschedule interval task on success
- **GIVEN** a task with a positive `interval` value
- **WHEN** the task completes successfully
- **THEN** the worker MUST call `AsyncTaskQueue.complete_task()` which reschedules the task
- **AND** MUST NOT attempt to reschedule the interval task independently
- **AND** MUST NOT contain any duplicate interval scheduling logic
