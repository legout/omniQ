## MODIFIED Requirements

### Requirement: TaskError Model
The system MUST provide structured error information for failed tasks.

#### Scenario: TaskError with minimal fields for v1
- **GIVEN** a task failure occurs during execution
- **WHEN** TaskError is created
- **THEN** it MUST contain exactly these 6 core fields:
  - `error_type`: str (e.g., "ValueError", "RuntimeError")
  - `message`: str (human-readable error description)
  - `timestamp`: datetime (when the error occurred)
  - `traceback`: Optional[str] (optional stack trace)
  - `retry_count`: int (number of retries attempted)
  - `is_retryable`: bool (whether this error allows retry)
- **AND** MUST NOT include additional fields for v1 (severity, category, exception_type, context, max_retries)
