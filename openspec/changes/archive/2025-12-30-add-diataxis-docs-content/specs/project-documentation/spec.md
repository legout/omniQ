# project-documentation Specification (Delta)

## ADDED Requirements

### Requirement: Tutorials cover primary user journeys
The documentation SHALL include tutorials that teach the primary OmniQ user journeys end-to-end.

#### Scenario: Learn OmniQ from tutorials
- **GIVEN** a new user
- **WHEN** they follow the tutorials in order
- **THEN** they MUST successfully learn how to enqueue tasks, run workers, schedule tasks, and observe results without needing external services.

### Requirement: How-to guides cover common user goals
The documentation SHALL include how-to guides that help users accomplish common tasks with OmniQ.

#### Scenario: Solve a specific goal
- **GIVEN** a user has a concrete goal (e.g., choose backend, configure retries, configure logging)
- **WHEN** they consult the how-to section
- **THEN** they MUST find a focused, step-oriented guide to achieve that goal.

### Requirement: Explanation describes the mental model and semantics
The documentation SHALL include explanation pages that describe OmniQ’s core concepts, semantics, and tradeoffs.

#### Scenario: Understand retry and scheduling semantics
- **GIVEN** a user is deciding how to use retries or scheduling safely
- **WHEN** they read the explanation pages
- **THEN** they MUST understand the retry budget model and scheduling behavior at a conceptual level.

### Requirement: Reference provides complete API lookup (including power-user modules)
The documentation SHALL include an API reference suitable for lookup, generated from the codebase via mkdocstrings, including power-user modules (queue/worker/storage).

#### Scenario: Look up façade and power-user API details
- **GIVEN** a user wants exact signatures and docstrings
- **WHEN** they visit the reference section
- **THEN** they MUST find documentation for façade modules and at least:
  - `omniq.queue`
  - `omniq.worker`
  - `omniq.storage.base`
  - `omniq.storage.file`
  - `omniq.storage.sqlite`
