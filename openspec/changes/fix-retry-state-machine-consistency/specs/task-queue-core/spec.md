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

