# api-standards Specification

## Purpose
TBD - created by archiving change improve-docstrings-for-api-reference. Update Purpose after archive.
## Requirements
### Requirement: Public APIs have docstrings with examples (façade and power-user)
All public APIs MUST have docstrings that include a usage example. This includes both façade APIs (`AsyncOmniQ`) and power-user APIs (`AsyncTaskQueue`, `AsyncWorkerPool`).

#### Scenario: Public API with example
- **GIVEN** a user looks at `AsyncOmniQ.enqueue()` documentation
- **WHEN** they read the docstring
- **THEN** they MUST find an Example section showing basic usage.

#### Scenario: Power-user API with example
- **GIVEN** a user looks at `AsyncTaskQueue.complete_task()` documentation
- **WHEN** they read the docstring
- **THEN** they MUST find an Example section showing typical usage.

#### Scenario: Examples focus on happy path
- **GIVEN** a user reads docstring examples
- **WHEN** they follow the example code
- **THEN** the example MUST demonstrate successful operation (happy path)
- **AND** MUST NOT include error handling or exception catching.

### Requirement: Data models have comprehensive field documentation
All data models exported via `__all__` MUST have complete docstrings with field-by-field documentation describing all fields.

#### Scenario: Task TypedDict field documentation
- **GIVEN** a user consults `Task` type documentation
- **WHEN** they read the docstring
- **THEN** they MUST find descriptions for all fields (`id`, `func_path`, `args`, etc.)
- **AND** MUST understand the purpose of `Task` as a data structure
- **AND** MUST see an example showing how to create and use a `Task`.

#### Scenario: TaskResult TypedDict field documentation
- **GIVEN** a user consults `TaskResult` type documentation
- **WHEN** they read the docstring
- **THEN** they MUST find descriptions for all fields (`task_id`, `status`, `result`, etc.)
- **AND** MUST understand the purpose of `TaskResult` as a data structure
- **AND** MUST see an example showing how to interpret a `TaskResult`.

### Requirement: Configuration class has complete parameter documentation
`Settings.__init__` and related configuration methods MUST document all parameters with type and purpose.

#### Scenario: Settings configuration documentation
- **GIVEN** a user creates a `Settings` instance
- **WHEN** they read the docstring
- **THEN** they MUST see a complete Args section describing all parameters
- **AND** MUST see a Raises section for validation errors
- **AND** MUST see an Example showing common configuration patterns.

### Requirement: Storage backends document error conditions
Storage backend public methods MUST document exceptions they can raise.

#### Scenario: Storage operation error handling
- **GIVEN** a user calls `FileStorage.enqueue()`
- **WHEN** they read the docstring
- **THEN** they MUST see a Raises section listing `StorageError` and `ValueError`.

### Requirement: Type hints match docstring descriptions
Type hints in function signatures MUST be consistent with parameter descriptions in docstrings.

#### Scenario: Type hint consistency
- **GIVEN** a function signature has type hints
- **WHEN** docstring documents parameters
- **THEN** parameter types in docstring MUST match the signature's type hints.

### Requirement: Enum values documented with tradeoffs
Enum types that represent configuration options MUST document each value and provide tradeoff guidance where relevant.

#### Scenario: BackendType enum documentation
- **GIVEN** a user consults `BackendType` documentation
- **WHEN** they read the docstring
- **THEN** they MUST see documentation for both `FILE` and `SQLITE` values
- **AND** MUST see tradeoffs explaining when to use each backend.

