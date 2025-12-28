## ADDED Requirements

### Requirement: Pytest-Based Test Suite
The project SHALL provide a pytest-based test suite that validates the public behavior of OmniQ and can be run reliably in a clean environment.

#### Scenario: Run tests without path hacks
- **GIVEN** a clean checkout with development dependencies installed
- **WHEN** a developer runs the test suite via pytest
- **THEN** tests MUST import OmniQ using package imports (e.g. `omniq.*`) without modifying `sys.path`
- **AND** the suite MUST execute deterministically without relying on unbounded sleeps for async timing.

