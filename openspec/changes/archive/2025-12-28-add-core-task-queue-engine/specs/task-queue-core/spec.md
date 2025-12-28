## MODIFIED Requirements
### Requirement: AsyncTaskQueue Core
The system SHALL provide an AsyncTaskQueue class that handles task enqueue/dequeue logic, scheduling, and retries separate from worker and storage concerns.

#### Scenario: Enqueue task with scheduling
- **WHEN** a task is enqueued with eta or interval
- **THEN** AsyncTaskQueue stores task and handles scheduling logic

#### Scenario: Dequeue due task
- **WHEN** worker requests next task
- **THEN** AsyncTaskQueue returns next due task with proper FIFO ordering

#### Scenario: Handle task retry
- **WHEN** task execution fails and retries are available
- **THEN** AsyncTaskQueue reschedules task with exponential backoff

#### Scenario: Handle interval task
- **WHEN** interval task completes successfully
- **THEN** AsyncTaskQueue reschedules for next interval