# project-examples Specification (Delta)

## ADDED Requirements

### Requirement: Curated runnable examples
The repository SHALL provide a minimal set of runnable examples that demonstrate OmniQ’s primary features with clear, beginner-friendly scripts.

#### Scenario: Run examples directly
- **GIVEN** a developer has installed OmniQ and its default dependencies
- **WHEN** they run an example via `python examples/<name>.py`
- **THEN** the example MUST execute without requiring external services
- **AND** MUST complete in a short amount of time suitable for local iteration.

### Requirement: Examples cover core feature surface
The examples suite SHALL collectively demonstrate the core OmniQ feature surface with minimal overlap between scripts.

#### Scenario: Feature coverage across a minimal set
- **GIVEN** the examples suite is reviewed as a set
- **WHEN** mapping each example to demonstrated features
- **THEN** the suite MUST include examples covering:
  - async façade usage
  - sync façade usage
  - at least one storage backend (file) and one transactional backend (SQLite)
  - delayed execution (`eta`) and repeating execution (`interval`)
  - retries and task failure recording
  - logging configuration and task correlation context.

### Requirement: Examples are deterministic and self-contained
Examples SHALL avoid non-deterministic behavior and persistent side effects.

#### Scenario: Deterministic failure/retry demonstrations
- **GIVEN** an example demonstrates retry behavior
- **WHEN** it is run multiple times
- **THEN** its failure and success path MUST be deterministic (no reliance on randomness).

#### Scenario: No persistent repo changes
- **GIVEN** a developer runs the examples from a clean checkout
- **WHEN** the examples complete
- **THEN** they MUST NOT require committing generated files to the repository
- **AND** any created storage artifacts SHOULD be written to temporary directories.

