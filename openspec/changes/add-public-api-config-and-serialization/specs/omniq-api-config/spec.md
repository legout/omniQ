## ADDED Requirements

### Requirement: Async and sync interfaces
The library MUST expose async-first and sync-friendly APIs for enqueuing tasks, retrieving results, and running workers.

#### Scenario: Enqueue and await result using AsyncOmniQ
- **GIVEN** an `AsyncOmniQ` instance configured with a storage backend and settings
- **WHEN** `await enqueue(func, *args, **kwargs)` is called
- **THEN** the method MUST enqueue a task and return a task ID.

- **GIVEN** a valid task ID for a completed task
- **WHEN** `await get_result(task_id, wait=False)` is called
- **THEN** the method MUST return a `TaskResult` if one exists
- **AND** MUST return `None` if no result has been recorded.

#### Scenario: Use sync wrapper from blocking code
- **GIVEN** an `OmniQ` instance configured from the same settings
- **WHEN** `enqueue(func, *args, **kwargs)` is called from synchronous code
- **THEN** the wrapper MUST run the underlying async enqueue via a centralized async runner
- **AND** MUST return the task ID as a blocking call.

- **GIVEN** a task expected to complete within a timeout
- **WHEN** `get_result(task_id, wait=True, timeout=T)` is called on `OmniQ`
- **THEN** the call MUST block until either the result is available or the timeout elapses
- **AND** MUST return the `TaskResult` on success
- **AND** MAY raise a timeout error or return `None` if the timeout expires, as defined by the implementation.

### Requirement: Settings and environment configuration
The system MUST provide a small `Settings` model with environment variable overrides to configure backends and defaults.

#### Scenario: Construct settings from environment
- **GIVEN** process environment variables `OMNIQ_BACKEND`, `OMNIQ_DB_URL`, `OMNIQ_BASE_DIR`, `OMNIQ_DEFAULT_TIMEOUT`, `OMNIQ_DEFAULT_MAX_RETRIES`, `OMNIQ_RESULT_TTL`, and `OMNIQ_SERIALIZER`
- **WHEN** `Settings.from_env()` (or equivalent helper) is called
- **THEN** it MUST read these variables, apply reasonable defaults when values are missing
- **AND** MUST validate and coerce values into the correct types
- **AND** MUST construct a `Settings` instance that can be passed directly to `AsyncOmniQ` and `OmniQ`.

#### Scenario: Switch backends between environments
- **GIVEN** a development environment with `OMNIQ_BACKEND=file` and a staging environment with `OMNIQ_BACKEND=sqlite`
- **WHEN** the same codebase calls `Settings.from_env()` in both environments
- **THEN** it MUST produce settings that select the file backend in development and the SQLite backend in staging
- **AND** the rest of the application code MUST NOT need to change.

### Requirement: Serializer selection
The system MUST support a safe default serializer and an unsafe opt-in mode as described in the PRD.

#### Scenario: Use msgspec as default serializer
- **GIVEN** no explicit serializer override in settings or environment
- **WHEN** OmniQ is initialized
- **THEN** it MUST use a msgspec-based serializer for tasks and results
- **AND** MUST raise a clear error if task arguments or results cannot be encoded.

#### Scenario: Enable unsafe cloudpickle mode
- **GIVEN** settings or environment specifying `serializer="cloudpickle"` (or equivalent)
- **WHEN** OmniQ is initialized
- **THEN** it MUST use a cloudpickle-based serializer for tasks and results
- **AND** MUST allow arbitrary Python objects in arguments and return values
- **AND** MUST clearly document that this mode is unsafe for untrusted or multi-tenant inputs.

### Requirement: Logging behavior
The library MUST emit basic logs for queue and worker behavior and allow users to control log verbosity.

#### Scenario: Configure log level via environment
- **GIVEN** the environment variable `OMNIQ_LOG_LEVEL` is set to a valid log level (e.g., `INFO`, `DEBUG`, `WARNING`, `ERROR`)
- **WHEN** OmniQ initializes its logging configuration
- **THEN** it MUST set the library logger to the configured level
- **AND** MUST use the standard Python logging infrastructure so users can integrate OmniQ logs with application logs.

#### Scenario: Log key lifecycle events
- **GIVEN** a running OmniQ instance with logging enabled
- **WHEN** tasks are enqueued, started, retried, failed, or completed
- **THEN** the library SHOULD emit log messages for these lifecycle events at appropriate levels
- **AND** these logs MUST NOT include sensitive task argument data by default.
