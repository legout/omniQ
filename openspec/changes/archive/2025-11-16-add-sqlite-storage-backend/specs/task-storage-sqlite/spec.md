## ADDED Requirements

### Requirement: SQLite schema
The SQLite-based storage backend MUST use a minimal schema aligned with the core task and result models.

#### Scenario: Create tasks and results tables
- **GIVEN** a new SQLite database for OmniQ
- **WHEN** `SQLiteStorage` is initialized
- **THEN** it MUST ensure a `tasks` table exists with columns for `id`, `func_path`, `args`, `kwargs`, `eta`, `status`, `attempts`, `max_retries`, `timeout`, `created_at`, `updated_at`, and `interval` as required by the PRD
- **AND** it MUST ensure a `results` table exists with columns for `task_id`, `status`, `result`, `error`, `finished_at`, and optional attempt metadata.

#### Scenario: Create indexes for efficient dequeue
- **GIVEN** the `tasks` table exists
- **WHEN** `SQLiteStorage` applies migrations
- **THEN** it MUST ensure indexes exist on `status` and `eta`
- **AND** these indexes MUST support efficient queries to fetch the next due task.

### Requirement: Dequeue and update semantics
The SQLite backend MUST support safe dequeue, status updates, and result recording using transactions.

#### Scenario: Dequeue next due task
- **GIVEN** multiple tasks stored in SQLite with varying `eta` values and statuses
- **WHEN** `dequeue(now)` is called
- **THEN** the backend MUST select a single task with `status=PENDING` (or equivalent) and `eta <= now`
- **AND** MUST prefer the smallest `eta` value, breaking ties in insertion order when possible
- **AND** MUST mark the task as claimed so it is not concurrently dequeued by another worker.

#### Scenario: Record running and completion in SQLite
- **GIVEN** a task row that has been dequeued for execution
- **WHEN** `mark_running(task_id)` is called
- **THEN** the backend MUST update the row's status to `RUNNING` and update its timestamp.

- **GIVEN** a task row that completes successfully
- **WHEN** `mark_done(task_id, result)` is called inside a transaction
- **THEN** the backend MUST insert or update a row in the `results` table for the `task_id`
- **AND** MUST update the task row's status to `SUCCESS`.

