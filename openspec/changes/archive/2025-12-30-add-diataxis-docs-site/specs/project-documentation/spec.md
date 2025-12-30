# project-documentation Specification (Delta)

## ADDED Requirements

### Requirement: Documentation follows Diátaxis structure
The project SHALL publish user-facing documentation organized by the Diátaxis framework: Tutorials, How-to guides, Reference, and Explanation.

#### Scenario: Navigate by documentation intent
- **GIVEN** a user visits the documentation site
- **WHEN** they choose between learning, solving a task, looking up details, or understanding concepts
- **THEN** they MUST find a dedicated section matching that intent (Tutorials / How-to / Reference / Explanation).

### Requirement: Documentation is published to GitHub Pages
The project SHALL publish the documentation site to GitHub Pages on updates to the `main` branch.

#### Scenario: Deploy on merge to main
- **GIVEN** a change is merged into `main`
- **WHEN** the documentation workflow runs
- **THEN** the documentation site MUST be built and published successfully to GitHub Pages.

### Requirement: README is canonical and identical to docs homepage
`README.md` SHALL be the canonical source of the documentation index page, and the published docs homepage MUST be identical to `README.md`.

#### Scenario: Prevent README/homepage drift
- **GIVEN** `README.md` is updated
- **WHEN** the documentation site is built
- **THEN** the homepage content MUST match `README.md` exactly
- **AND** CI MUST fail if the homepage would diverge from `README.md`.

### Requirement: API reference is auto-generated (including power-user modules)
The documentation site SHALL include an auto-generated API reference based on the installed OmniQ package using mkdocstrings, covering both façade APIs and power-user modules.

#### Scenario: Generate API reference for documented modules
- **GIVEN** OmniQ is importable during docs build
- **WHEN** the documentation reference section is built
- **THEN** API pages MUST be generated and included in navigation for at least:
  - `omniq.core`
  - `omniq.config`
  - `omniq.queue`
  - `omniq.worker`
  - `omniq.models`
  - `omniq.logging`
  - `omniq.serialization`
  - `omniq.storage.base`
  - `omniq.storage.file`
  - `omniq.storage.sqlite`
