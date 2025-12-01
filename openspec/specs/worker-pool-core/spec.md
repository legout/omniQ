# worker-pool-core Specification

## Purpose
TBD - created by archiving change add-async-worker-pool. Update Purpose after archive.
## Requirements
### Requirement: Async worker pool execution
The system MUST provide an async worker pool that polls storage for due tasks and executes them concurrently.

#### Scenario: Process tasks up to concurrency limit
- **GIVEN** an `AsyncWorkerPool` configured with `concurrency=N > 0`
- **AND** a storage backend with more than `N` due tasks
- **WHEN** the worker pool is started
- **THEN** it MUST execute at most `N` tasks concurrently
- **AND** MUST dequeue additional tasks only as running tasks complete.

#### Scenario: Periodic polling when idle
- **GIVEN** an `AsyncWorkerPool` configured with a positive `poll_interval`
- **WHEN** there are no due tasks at the moment of a poll
- **THEN** the worker pool MUST wait approximately `poll_interval` seconds before polling storage again
- **AND** MUST continue this behavior until stopped.

### Requirement: Callable execution and retries
The worker pool MUST execute both async and sync callables and handle retries according to task metadata.

#### Scenario: Execute async callable
- **GIVEN** a task whose `func_path` resolves to an async function
- **WHEN** the worker executes the task
- **THEN** it MUST `await` the function directly with the provided `args` and `kwargs`
- **AND** MUST record the returned value in the task result on success.

#### Scenario: Execute sync callable in thread
- **GIVEN** a task whose `func_path` resolves to a sync function
- **WHEN** the worker executes the task
- **THEN** it MUST run the function in a thread executor or equivalent
- **AND** MUST record the returned value in the task result on success.

#### Scenario: Retry with exponential backoff
- **GIVEN** a task with `max_retries > 0`
- **AND** an initial attempt that fails with an exception
- **WHEN** the worker computes the next attempt time
- **THEN** it MUST apply a backoff delay of `base * (2 ** attempts)` seconds plus small jitter
- **AND** MUST reschedule the task using the computed `eta`
- **AND** MUST stop retrying and mark the task `FAILED` once attempts exceed `max_retries`.

### Requirement: Interval scheduling behavior
The worker pool MUST support fixed-interval tasks using the `interval` field.

#### Scenario: Reschedule interval task on success
- **GIVEN** a task with a positive `interval` value
- **WHEN** the task completes successfully
- **THEN** the worker MUST reschedule the task by setting a new `eta` equal to the completion time plus `interval`
- **AND** MUST persist the updated scheduling information so the task runs again at the next interval.

### Requirement: Sync worker wrapper
The system MUST provide a sync wrapper that starts and stops the async worker pool from synchronous code.

#### Scenario: Start and stop workers from sync code
- **GIVEN** a `WorkerPool` wrapper around an `AsyncWorkerPool`
- **WHEN** `start()` is called from synchronous user code
- **THEN** the wrapper MUST start the async worker pool in a dedicated thread or equivalent mechanism
- **AND** MUST return control to the caller once workers are running.

- **GIVEN** the worker pool is running via the sync wrapper
- **WHEN** `stop()` is called
- **THEN** the wrapper MUST signal the async worker pool to shut down
- **AND** MUST block until the worker pool has stopped polling and any in-flight tasks have been handled according to shutdown semantics.

