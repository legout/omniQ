# project-structure Specification (Delta)

## REMOVED Requirements

### Requirement: Examples directory exists in repository root
The project SHALL maintain a single canonical examples directory at the repository root level (`examples/`), not within `docs/`.

#### Scenario: Find example files in repository
- **GIVEN** a developer downloads or clones the OmniQ repository
- **WHEN** they look for example code
- **THEN** they MUST find all examples in a single `examples/` directory at the repository root
- **THEN** they MUST NOT encounter confusion from duplicate example directories in `docs/examples/` and `examples/`

#### Scenario: Documentation references canonical examples location
- **GIVEN** a user reads the OmniQ documentation
- **WHEN** they follow links to examples
- **THEN** all links MUST point to the `examples/` directory at repository root
- **THEN** no links MUST point to `docs/examples/`

#### Scenario: Project follows Python conventions
- **GIVEN** a new contributor examines the OmniQ project structure
- **WHEN** they review the directory layout
- **THEN** examples SHALL be located at repository root (`examples/`)
- **THEN** examples SHALL NOT be nested within documentation directory
