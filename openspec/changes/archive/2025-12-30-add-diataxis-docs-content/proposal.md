# Change: Write comprehensive Diátaxis documentation content

## Why
With the docs site scaffolded, OmniQ needs comprehensive user-facing content that supports:
- learning the library (tutorials)
- accomplishing common goals (how-to guides)
- looking up exact details (reference)
- understanding design decisions and semantics (explanation)

This change fills the Diátaxis sections with clear documentation for library users. Tutorials are grounded in the existing runnable examples to reduce drift. Reference is backed by mkdocstrings-generated API documentation, including power-user modules (queue/worker/storage).

## What Changes
- Tutorials based on runnable examples:
  - Async quickstart
  - Scheduling with `eta` and `interval`
  - Retries + TaskError semantics
  - Logging + env configuration + sync façade
- How-to guides for common user goals:
  - Choose backend (file vs sqlite)
  - Run a worker pool reliably (concurrency, shutdown)
  - Configure retries/timeouts safely (idempotency guidance)
  - Inspect task state/results/errors
  - Configure logging for DEV/PROD via env vars
- Explanation pages:
  - Architecture boundaries (façade vs queue vs worker vs storage)
  - Retry budget semantics (attempts vs max_retries)
  - Scheduling semantics (eta/interval)
  - Storage tradeoffs
- Reference:
  - mkdocstrings-generated API reference for both façade and power-user modules
  - curated reference pages for configuration/env vars if needed beyond docstrings

## Impact
- Affected specs: `project-documentation` (documentation-only)
- Affected code: docs content (Markdown) only

## Non-Goals
- No contributor documentation (users only).
- No runtime feature work or API changes.
