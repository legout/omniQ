# Change: Align public API documentation with actual façade behavior

## Why
The README examples use string function paths for `enqueue(...)`, but the current public façade API expects a Python callable and derives `func_path` internally. This mismatch makes the library harder to use and creates confusion about what is supported in v1.

## What Changes
- Decide and document the supported v1 enqueue input(s):
  - callable-only, or
  - callable plus explicit `func_path` string overload.
- Update docs/examples accordingly (README + examples).
- Ensure OpenSpec `omniq-api-config` reflects the chosen API shape and includes scenarios for both async and sync façades.

## Impact
- Affected specs: `omniq-api-config`
- Affected docs: `README.md`, `examples/` (if applicable)
- Potentially breaking if a new overload is added/removed; preference is to keep backward compatibility where possible.

