# task-storage-file Specification

## Purpose
TBD - created by archiving change add-storage-abstraction-and-file-backend. Update Purpose after archive.
## Requirements
### Requirement: File Storage Layout
The file-based storage backend MUST persist tasks and results on a local filesystem using a simple, predictable directory structure.

#### Scenario: Persist task and result files
- **GIVEN** a `FileStorage` instance configured with a base directory
- **WHEN** a task is enqueued
- **THEN** the backend MUST write the serialized task to a file under a `queue/` subdirectory
- **AND** file naming MUST allow uniquely identifying tasks by `id`.

- **GIVEN** a task has completed with a recorded `TaskResult`
- **WHEN** the result is stored
- **THEN** the backend MUST write the serialized result to a file under a `results/` subdirectory
- **AND** file naming MUST allow looking up results by `task_id`.

### Requirement: Safe dequeue semantics
The file-based backend MUST support safe dequeueing in the presence of multiple worker processes.

#### Scenario: Atomically claim a task
- **GIVEN** multiple workers polling the same `FileStorage` base directory
- **WHEN** two workers attempt to dequeue the same due task concurrently
- **THEN** the backend MUST ensure that at most one worker successfully claims the task
- **AND** the other worker MUST either dequeue a different task or receive `None` if no other tasks are available.

#### Scenario: Handle empty queue
- **GIVEN** no due tasks are present in the `queue/` directory
- **WHEN** `dequeue(now)` is called
- **THEN** the backend MUST return `None`
- **AND** MUST NOT create or modify any task or result files.

### Requirement: Retry-safe state transitions
The file-based backend MUST handle retry scenarios safely, ensuring tasks can be rescheduled without losing state or raising errors due to file state mismatches.

#### Scenario: Mark task as failed with retry
- **GIVEN** a task in `RUNNING` state with file named `{id}.running`
- **WHEN** `mark_failed(task_id, error, will_retry=True)` is called
- **THEN** the backend MUST:
  - Search for the task file in any of these locations: `{id}.running`, `{id}.task`, `{id}.done`
  - Transition the task status to `FAILED`
  - Write the task with `FAILED` status back to `{id}.task` file (for rescheduling)
  - Remove the original task file if it was in a different location
  - Store the failure result in the `results/` directory

#### Scenario: Mark task as permanently failed
- **GIVEN** a task in `RUNNING` state with file named `{id}.running`
- **WHEN** `mark_failed(task_id, error, will_retry=False)` is called
- **THEN** the backend MUST:
  - Search for the task file in any of these locations: `{id}.running`, `{id}.task`, `{id}.done`
  - Transition the task status to `FAILED`
  - Write the task with `FAILED` status to `{id}.done` file (final state)
  - Remove the original task file if it was in a different location
  - Store the failure result in the `results/` directory

#### Scenario: Reschedule task for retry
- **GIVEN** a task in `FAILED` state (after `mark_failed` with `will_retry=True`)
- **WHEN** `reschedule(task_id, new_eta)` is called
- **THEN** the backend MUST:
  - Read the task from `{id}.task` file
  - Update the task's `schedule.eta` to the new retry time
  - Transition the task status from `FAILED` to `PENDING`
  - Write the updated task back to `{id}.task` file

#### Scenario: Handle task not found during mark_failed
- **GIVEN** a task_id that does not exist in any state file (`.running`, `.task`, `.done`)
- **WHEN** `mark_failed(task_id, error, will_retry=True/False)` is called
- **THEN** the backend MUST raise `NotFoundError`
