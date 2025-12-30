# Design: Docstring improvements for mkdocstrings

## Key Decisions

### Google-style convention
- Use Google-style docstrings (already configured for mkdocstrings)
- Format: `Args:`, `Returns:`, `Raises:`, `Example:` sections
- Keep descriptions concise but complete

### Examples in docstrings
- Add Examples section to **public APIs** including:
  - Façade APIs: `AsyncOmniQ` methods, `Settings.from_env`
  - Power-user APIs: `AsyncTaskQueue` methods, `AsyncWorkerPool` class
- Examples should be:
  - Self-contained (no external state assumptions)
  - Use concrete, realistic values
  - Show common patterns (enqueue, result retrieval, worker usage)
  - **Focus on happy path only** (no error handling shown in examples)
- No examples for internal methods (e.g., `_convert_interval`)

### TypedDict documentation
- Use full class docstrings explaining:
  - Purpose of the data structure
  - Where it's used in the system
  - Key field descriptions (field-by-field documentation)
  - Example usage

### Enum documentation
- Document enum values with tradeoffs when relevant (e.g., BackendType)

## Validation
- mkdocstrings should generate pages without warnings
- Generated API docs should have complete parameter descriptions
- All examples should be runnable and demonstrate happy path
