## MODIFIED Requirements

### Requirement: Async and sync façades
The library MUST expose async-first and sync-friendly APIs for enqueuing tasks.

#### Scenario: Enqueue using a callable
- **GIVEN** an `AsyncOmniQ` instance
- **WHEN** `await enqueue(func, *args, **kwargs)` is called with a Python callable
- **THEN** the system MUST derive and persist `func_path` from the callable
- **AND** MUST enqueue the task and return a task ID.

