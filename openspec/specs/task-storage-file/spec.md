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

