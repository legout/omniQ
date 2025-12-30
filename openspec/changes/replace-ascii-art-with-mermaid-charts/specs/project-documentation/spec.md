# project-documentation Specification (Delta)

## ADDED Requirements

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
