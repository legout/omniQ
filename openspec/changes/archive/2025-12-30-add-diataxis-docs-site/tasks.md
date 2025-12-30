## 1. Docs Site Scaffolding
- [x] Add MkDocs configuration with Diátaxis navigation (Tutorials / How-to / Reference / Explanation)
- [x] Add `mkdocs-material` theme and minimal markdown extensions suitable for code-heavy docs
- [x] Add mkdocstrings configuration and include Reference → API in navigation
- [x] Add baseline docs directory structure (`docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`)

## 2. README-as-Index Guarantee
- [x] Implement docs build step that generates `docs/index.md` from `README.md` (`README.md` remains canonical)
- [x] Add a check that fails CI if generated `docs/index.md` differs from `README.md`
- [x] Ensure `README.md` links remain valid when rendered on GitHub and on GitHub Pages

## 3. API Reference Scaffolding (mkdocstrings)
- [x] Create API reference entry points for façade modules (`omniq.core`, `omniq.config`, etc.)
- [x] Create API reference entry points for power-user modules:
  - [x] `omniq.queue`
  - [x] `omniq.worker`
  - [x] `omniq.storage.base`
  - [x] `omniq.storage.file`
  - [x] `omniq.storage.sqlite`
- [x] Ensure API reference pages build without importing test-only dependencies

## 4. GitHub Pages Deployment
- [x] Add GitHub Actions workflow to build and publish MkDocs site to GitHub Pages on pushes to `main`

## 5. Validation
- [x] Ensure `mkdocs build --strict` runs in CI
- [x] Confirm broken internal links fail the build
- [x] Confirm README/index equality check runs in CI
