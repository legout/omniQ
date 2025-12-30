# Change: Replace ASCII art with Mermaid charts

## Why
The explanation chapter contains multiple ASCII art diagrams that are hard to read, not interactive, and don't scale well on different screen sizes. Replacing them with Mermaid charts will:
- Improve readability with proper diagram rendering
- Enable interactive diagrams (zoom, pan)
- Ensure consistent styling across documentation
- Leverage the existing mkdocs Material theme support for Mermaid

## What Changes
- Replace all ASCII art in explanation chapter with Mermaid flowcharts:
  - **architecture.md**: Component diagram, enqueue flow, worker execution flow
  - **scheduling.md**: ETA timeline, interval task timeline, failure rescheduling, combined ETA+interval, queue state
  - **storage-tradeoffs.md**: Directory layout structure
- Update mkdocs.yml to ensure Mermaid is properly enabled (if needed)

## Impact
- Affected specs: `project-documentation` (documentation-only)
- Affected code: `docs/explanation/*.md` files, possibly `mkdocs.yml`

## Non-Goals
- No changes to documentation content or text
- No new features or behavioral changes
- No changes to other documentation sections (tutorials, how-to, reference)
