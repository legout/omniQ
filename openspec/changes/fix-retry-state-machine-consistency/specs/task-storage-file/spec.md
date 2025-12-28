## MODIFIED Requirements

### Requirement: Safe dequeue semantics
The file-based backend MUST support safe dequeueing and retry rescheduling without corrupting task state.

#### Scenario: Retry does not lose claim state
- **GIVEN** a task has been dequeued and is in a claimed/running state
- **WHEN** the system records a retryable failure and reschedules the task
- **THEN** the backend MUST persist the failure result
- **AND** MUST ensure subsequent retry attempts can be dequeued (the task MUST be placed back into a pending state with a future `eta`)
- **AND** MUST NOT fail due to missing intermediate files (e.g., `.running`) during the retry transition.

