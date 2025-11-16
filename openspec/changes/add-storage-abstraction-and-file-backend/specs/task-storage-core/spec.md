## ADDED Requirements

### Requirement: Base Storage Interface
The system MUST provide an async storage interface that covers queue and result operations used by the task queue and worker pool.

#### Scenario: Enqueue and dequeue task
- **GIVEN** a valid `Task` in `PENDING` status
- **WHEN** `BaseStorage.enqueue` is called
- **THEN** the storage backend MUST persist the task and return its `id`
- **AND** MUST make the task eligible for dequeue when its `eta` is less than or equal to the current time.

- **GIVEN** there is at least one due task in storage
- **WHEN** `BaseStorage.dequeue(now)` is called with `now` at or after the task's `eta`
- **THEN** the backend MUST return a single due task instance
- **AND** MUST ensure that the same task is not concurrently dequeued by another worker in the same backend.

#### Scenario: Record running and completion
- **GIVEN** a task that has been dequeued for execution
- **WHEN** `BaseStorage.mark_running(task_id)` is called
- **THEN** the backend MUST update the persisted task status to `RUNNING`
- **AND** MUST update the task's `updated_at` timestamp.

- **GIVEN** a task that has completed successfully
- **WHEN** `BaseStorage.mark_done(task_id, result)` is called
- **THEN** the backend MUST persist the provided `TaskResult`
- **AND** MUST update the task status to `SUCCESS`
- **AND** MUST make the result retrievable via `BaseStorage.get_result(task_id)`.

### Requirement: Result Retrieval and Cleanup
Storage backends MUST support retrieving task results and cleaning up old results based on age.

#### Scenario: Retrieve result by task ID
- **GIVEN** a task has a persisted `TaskResult`
- **WHEN** `BaseStorage.get_result(task_id)` is called
- **THEN** the backend MUST return the corresponding `TaskResult`
- **AND** MUST return `None` if no result exists for that `task_id`.

#### Scenario: Purge old results
- **GIVEN** the system is configured with a result TTL
- **WHEN** `BaseStorage.purge_results(older_than)` is called with a cutoff timestamp
- **THEN** the backend MUST remove or mark as deleted any results older than the cutoff
- **AND** MUST return the count of results purged.

### Requirement: Retry and Rescheduling Support
Storage backends MUST support marking failures and optionally rescheduling tasks for retries or fixed-interval execution.

#### Scenario: Mark failed task with retry
- **GIVEN** a task that failed but is eligible for retry
- **WHEN** `BaseStorage.mark_failed(task_id, error, will_retry=True)` is called
- **THEN** the backend MUST record the error details
- **AND** MUST update the task status to `RETRYING`
- **AND** MUST leave the task available for rescheduling by the queue or worker logic.

#### Scenario: Reschedule task for future attempt
- **GIVEN** a task that should be retried after a delay or at a fixed interval
- **WHEN** `BaseStorage.reschedule(task_id, new_eta)` is called
- **THEN** the backend MUST update the task's `eta` to `new_eta`
- **AND** MUST ensure the task does not appear as due before `new_eta`
- **AND** MUST preserve any existing attempt counters and retry metadata.

