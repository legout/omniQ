# task-queue-core Specification

## Purpose
TBD - created by archiving change add-core-task-queue. Update Purpose after archive.
## Requirements
### Requirement: Task Model
The system MUST represent each enqueued unit of work as a `Task` with well-defined fields and semantics.

#### Scenario: Create pending task from callable
- **GIVEN** a Python callable and serializable arguments
- **WHEN** a task is created for immediate execution with default settings
- **THEN** the task MUST be assigned a unique `id`
- **AND** MUST store the callable reference as a string `func_path`
- **AND** MUST store `args` and `kwargs` in serialized form
- **AND** MUST have `eta` unset or set to the current time
- **AND** MUST set `max_retries` and `timeout` from default settings
- **AND** MUST set `status` to `PENDING`
- **AND** MUST record `created_at` and `updated_at` timestamps.

#### Scenario: Schedule task for future execution
- **GIVEN** a Python callable and arguments
- **WHEN** a task is created with an explicit future `eta`
- **THEN** the task MUST store the provided `eta`
- **AND** MUST remain in `PENDING` status until `eta <= now`
- **AND** storage and workers MUST NOT treat the task as due before `eta`.

#### Scenario: Configure repeating task with interval
- **GIVEN** a Python callable and arguments
- **WHEN** a task is created with an `interval` greater than zero
- **THEN** the task MUST store the `interval` value
- **AND** workers MUST treat the task as eligible for rescheduling after each successful run using that `interval`.

### Requirement: Task Status Lifecycle
Task statuses MUST follow a simple, well-defined lifecycle to support retries and observability.

#### Scenario: Status transition on successful completion
- **GIVEN** a task in `PENDING` or `RUNNING` status
- **WHEN** the worker completes execution without raising an error
- **THEN** the task status MUST be set to `SUCCESS`
- **AND** a corresponding `TaskResult` MUST be recorded with `status=SUCCESS`
- **AND** the task's `updated_at` and the result's `finished_at` timestamps MUST be updated to the completion time.

#### Scenario: Status transition on failure with retry
- **GIVEN** a task in `RUNNING` status with `max_retries` greater than the number of attempts so far
- **WHEN** execution raises an error
- **THEN** the task status MUST transition to `RETRYING`
- **AND** the failure MUST increment the attempt counter
- **AND** the error MUST be recorded in a `TaskResult` or equivalent error field
- **AND** the task MUST be eligible to be rescheduled for a future attempt.

#### Scenario: Status transition on final failure
- **GIVEN** a task in `RUNNING` or `RETRYING` status that has exhausted `max_retries`
- **WHEN** execution fails again
- **THEN** the task status MUST transition to `FAILED`
- **AND** the error details MUST be recorded in a `TaskResult`
- **AND** the task MUST NOT be scheduled for additional retries.

#### Scenario: Cancelled task
- **GIVEN** a task in `PENDING` or `RETRYING` status
- **WHEN** it is explicitly cancelled by the system or user
- **THEN** the task status MUST transition to `CANCELLED`
- **AND** workers MUST NOT execute the task after cancellation
- **AND** the cancellation MUST be reflected in the task's timestamps and any associated result metadata.

### Requirement: Task Result Model
Task results MUST capture the outcome of execution, including success values, errors, and timing information.

#### Scenario: Store success result
- **GIVEN** a task that completes successfully
- **WHEN** the worker records the outcome
- **THEN** a `TaskResult` MUST be created with the corresponding `task_id`
- **AND** MUST set `status` to `SUCCESS`
- **AND** MUST store the serialized return value in `result`
- **AND** MUST leave any error field unset or null
- **AND** MUST record `finished_at` as the completion time
- **AND** MAY store the final attempt count and `last_attempt_at` if available.

#### Scenario: Store failure result
- **GIVEN** a task that ends in a non-retriable failure
- **WHEN** the worker records the outcome
- **THEN** a `TaskResult` MUST be created with the corresponding `task_id`
- **AND** MUST set `status` to `FAILED`
- **AND** MUST leave any success `result` field unset or null
- **AND** MUST store a human-readable error message or structured error payload in `error`
- **AND** MUST record `finished_at` as the time of the final failed attempt
- **AND** MAY store the final attempt count and `last_attempt_at` if available.

