# Design: Examples Suite Conventions

## Goals
- Each example is a single, runnable script with a clear “story”.
- Examples are fast (<10s), deterministic (no randomness), and side-effect minimal (use temp dirs).
- Minimal overlap: each script demonstrates distinct feature clusters.

## Conventions
- Use `tempfile.TemporaryDirectory()` for storage paths.
- Keep task functions in `examples/tasks.py`:
  - Top-level functions only (stable `func_path` resolution).
  - One sync function and one async function for worker execution coverage.
  - One deterministic “flaky N times then succeed” function for retries.
- Use explicit prints that explain what’s happening (enqueue, worker start, result retrieval).
- Avoid network calls and external dependencies.

## Documentation Alignment
`README.md` worker examples must match the implemented façade:
- Prefer `AsyncOmniQ.worker(...)` + `await pool.start()/stop()` in docs/examples unless/until a convenience API exists.

