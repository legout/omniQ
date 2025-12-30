# project-documentation Specification

## Purpose
TBD - created by archiving change add-diataxis-docs-content. Update Purpose after archive.
## Requirements
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

### Requirement: Explanation chapter uses Mermaid charts for visual diagrams
The documentation SHALL use Mermaid charts for all diagrams in the explanation chapter to provide interactive, properly rendered visualizations of OmniQ's architecture, scheduling semantics, and storage structures.

#### Scenario: View architecture diagram
- **GIVEN** a user is reading the architecture explanation
- **WHEN** they view the component diagram and flow diagrams
- **THEN** they MUST see properly rendered Mermaid flowcharts that show component relationships and data flow clearly.

#### Scenario: Understand scheduling timelines
- **GIVEN** a user is learning about ETA and interval scheduling
- **WHEN** they view the scheduling timeline diagrams
- **THEN** they MUST see Mermaid flowcharts that clearly show the temporal progression of task execution and rescheduling.

#### Scenario: Compare storage backend structures
- **GIVEN** a user is deciding between File and SQLite backends
- **WHEN** they view the storage directory structure diagram
- **THEN** they MUST see a Mermaid tree-style flowchart showing the organization of files and directories.

#### Scenario: Access interactive diagrams
- **GIVEN** a user is viewing any Mermaid chart in the documentation
- **WHEN** they interact with the diagram
- **THEN** they MUST be able to zoom and pan (if supported by the theme) and the diagram MUST render consistently across screen sizes.

