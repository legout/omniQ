## MODIFIED Requirements

### Requirement: Async worker pool execution
The system MUST provide an async worker pool that polls for due tasks and executes them concurrently.

#### Scenario: Process tasks up to concurrency limit
- **GIVEN** an `AsyncWorkerPool` configured with `concurrency=N > 0`
- **AND** a backend with more than `N` due tasks
- **WHEN** the worker pool is started
- **THEN** it MUST schedule up to `N` tasks to execute concurrently
- **AND** MUST continue polling and scheduling additional tasks as capacity becomes available
- **AND** MUST NOT exceed `N` in-flight tasks at any moment.

### Requirement: Sync worker wrapper
The system MUST provide a sync wrapper that starts and stops the async worker pool from synchronous code.

#### Scenario: Start workers without blocking application startup
- **GIVEN** a `WorkerPool` wrapper around an `AsyncWorkerPool`
- **WHEN** `start()` is called from synchronous user code
- **THEN** the wrapper MUST start the worker pool in a dedicated thread (or equivalent)
- **AND** MUST return control to the caller once workers are running.

