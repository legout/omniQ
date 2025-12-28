## MODIFIED Requirements

### Requirement: Serializer Configuration
The system MUST support multiple serialization backends for task data.

#### Scenario: Default serializer is msgspec
- **GIVEN** a user creates an `AsyncOmniQ` or `OmniQ` instance without specifying serializer
- **WHEN** the instance is initialized
- **THEN** it MUST use `msgspec` as the default serializer
- **AND** MUST NOT use `json` as the default.

#### Scenario: JSON serializer option
- **GIVEN** a user explicitly requests JSON serialization
- **WHEN** `Settings` is created with `serializer="json"`
- **THEN** the system MUST use a simplified JSON serializer
- **AND** MUST NOT use model-aware coercion (tight coupling to Task/TaskError structure)
- **AND** MUST define a stable wire format for TaskError (6 core fields only)
- **AND** MAY deprecate JSON serializer in future v2 in favor of msgspec

#### Scenario: Wire format for TaskError
- **GIVEN** a TaskError with error information
- **WHEN** serialized to JSON or msgspec
- **THEN** the wire format MUST include exactly these 6 fields:
  ```json
  {
    "error_type": "ValueError",
    "message": "Invalid input",
    "timestamp": "2025-12-28T12:00:00Z",
    "traceback": null,
    "retry_count": 0,
    "is_retryable": true
  }
  ```
- **AND** MUST NOT include severity, category, exception_type, context, or max_retries for v1
