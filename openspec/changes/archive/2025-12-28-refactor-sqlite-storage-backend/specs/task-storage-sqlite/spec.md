## MODIFIED Requirements

### Requirement: Dequeue and update semantics
The SQLite backend MUST support safe dequeue, status updates, and result recording using transactions.

#### Scenario: Dequeue next due task increments attempts once
- **GIVEN** a task with `status=PENDING` and `eta <= now`
- **WHEN** `dequeue(now)` returns the task for execution
- **THEN** the backend MUST atomically claim the task for a single worker
- **AND** MUST set the persisted status to `RUNNING`
- **AND** MUST increment `attempts` exactly once for that claimed execution
- **AND** MUST execute a single UPDATE transaction with all changes (status, attempts, timestamps)
- **AND** MUST NOT execute multiple UPDATE statements for the same task
- **AND** MUST NOT call `transition_status()` after the initial claim

### Requirement: SQLite schema
The SQLite-based storage backend MUST use a minimal schema aligned with the core task and result models.

#### Scenario: Schema uses schedule dict with nested eta/interval
- **GIVEN** a task with interval scheduling
- **WHEN** `SQLiteStorage` is initialized or tasks are queried
- **THEN** it MUST store `schedule` as a JSON field containing:
  - `eta`: ISO timestamp string or null for immediate execution
  - `interval`: dict with `type="timedelta"` and numeric value or null for one-time tasks
- **AND** MUST NOT use separate `interval` column at database level

#### Scenario: Create indexes for efficient dequeue
- **GIVEN** the `tasks` table exists
- **WHEN** `SQLiteStorage` applies migrations
- **THEN** it MUST ensure indexes exist on `status` and `eta`
- **AND** these indexes MUST support efficient queries to fetch the next due task
