## MODIFIED Requirements

### Requirement: Dequeue and update semantics
The SQLite backend MUST support safe dequeue, status updates, and result recording using transactions.

#### Scenario: Dequeue next due task increments attempts once
- **GIVEN** a task with `status=PENDING` and `eta <= now`
- **WHEN** `dequeue(now)` returns the task for execution
- **THEN** the backend MUST atomically claim the task for a single worker
- **AND** MUST set the persisted status to `RUNNING`
- **AND** MUST increment `attempts` exactly once for that claimed execution.

