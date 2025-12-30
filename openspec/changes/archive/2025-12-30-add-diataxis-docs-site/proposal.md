# Change: Add Diátaxis documentation site (MkDocs + GitHub Pages)

## Why
OmniQ's current documentation is primarily in `README.md` with a small amount of additional material under `docs/`. Users lack a cohesive documentation experience that supports the four distinct documentation needs:
- learning (tutorials)
- solving concrete tasks (how-to guides)
- looking up precise details (reference)
- understanding concepts and trade-offs (explanation)

This change establishes a Diátaxis-aligned documentation site published to GitHub Pages. It guarantees the docs homepage is identical to `README.md` (with `README.md` as the canonical source) and scaffolds an auto-generated API reference using mkdocstrings, including "power-user" modules such as queue/worker/storage.

## What Changes
- Add a MkDocs documentation site using `mkdocs-material`.
- Define Diátaxis navigation sections:
  - Tutorials
  - How-to guides
  - Reference
  - Explanation
- Publish docs to GitHub Pages via GitHub Actions on pushes to `main`.
- Enforce README-as-index:
  - `README.md` is canonical
  - `docs/index.md` is generated from `README.md` during docs build
  - CI fails if `docs/index.md` would diverge from `README.md`
- Scaffold mkdocstrings-based API reference generation and include it in nav.
- Ensure repo-relative links in `README.md` remain valid when rendered as the docs homepage.

## Impact
- Affected specs: `project-documentation` (new; documentation-only)
- Affected code/config:
  - MkDocs config + documentation scaffolding
  - GitHub Actions workflow for Pages deployment
  - Docs tooling dependencies (no runtime behavior changes)

## Non-Goals
- No changes to OmniQ runtime behavior or public API semantics.
- No contributor/maintainer documentation (users only).
- No versioned documentation strategy.
