# Design: Diátaxis docs site + README-as-index

## Key Decisions

### Documentation stack
- Use MkDocs + `mkdocs-material` for a Markdown-first, user-focused experience.
- Use `mkdocstrings` (Python handler) for API reference generation.

### Publishing target
- Publish the site to GitHub Pages via GitHub Actions on pushes to `main`.

### README is canonical for homepage
Goal: the rendered docs homepage MUST be identical to `README.md`, and `README.md` is the single source of truth.

Implementation approach:
- Generate `docs/index.md` from `README.md` as part of the docs build (do not hand-edit `docs/index.md`).
- Add a CI check that fails if the generated `docs/index.md` differs from `README.md`.

Rationale:
- Prevents drift by construction.
- Keeps GitHub README and docs homepage in lockstep.

### Link strategy (to keep README links valid)
`README.md` links to repo-relative paths (e.g. `examples/README.md`). Because the docs homepage is identical, those links must also resolve on GitHub Pages.

Strategy:
- Mirror required repo artifacts into the docs build output (e.g. ensure `examples/README.md` is available under the published site).
- Avoid rewriting links differently between GitHub and docs.

### API reference scope (includes power-user modules)
The API reference should include both user-facing façade APIs and power-user modules.

Planned mkdocstrings coverage (module-level pages):
- `omniq` (package entry)
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

Notes:
- Private/implementation modules (e.g. `omniq.storage._async_sqlite`) are excluded by default unless users need them.

## Validation
- `mkdocs build --strict` must pass.
- GitHub Pages workflow must successfully build and publish.
- README/index drift check must pass.
