## ADDED Requirements

### Requirement: Task execution timeouts
The worker pool MUST enforce per-task execution timeouts when a positive `timeout` is configured on the task (or derived from settings).

#### Scenario: Fail task that exceeds timeout
- **GIVEN** a task with a `timeout` value greater than zero
- **AND** an `AsyncWorkerPool` executing that task
- **WHEN** the callable runs longer than the configured `timeout`
- **THEN** the worker MUST cancel or abort the execution of the callable
- **AND** MUST record a `TaskResult` with a failure status and an error indicating that a timeout occurred
- **AND** MUST treat the timeout as a failure for the purposes of retry logic (including backoff and `max_retries` limits).

#### Scenario: No per-task timeout when unset
- **GIVEN** a task whose `timeout` is unset or explicitly `None`
- **WHEN** the worker executes the task
- **THEN** the worker MUST NOT enforce a per-task timeout based on this field
- **AND** any execution limits in this case MUST come only from broader worker or process-level constraints, not from the task's `timeout`.

