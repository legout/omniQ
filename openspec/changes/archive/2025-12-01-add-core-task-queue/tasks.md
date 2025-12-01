## 1. Core Task Models
- [x] 1.1 Define `Task`, `TaskStatus`, `TaskResult`, and `Schedule` types in `src/omniq/models.py`.
- [x] 1.2 Ensure task fields cover IDs, callable path, arguments, scheduling, retries, timeouts, and timestamps as per the PRD.
- [x] 1.3 Implement basic status transition helpers for common lifecycle changes (pending → running → success / failed / retrying / cancelled).

## 2. Task Creation and Validation
- [x] 2.1 Add helpers to construct tasks from Python callables and arguments, including `eta`, optional `interval`, `max_retries`, and `timeout` defaults.
- [x] 2.2 Validate that required fields are always set (e.g., `id`, `func_path`, `created_at`) when tasks are created.

## 3. Result Handling
- [x] 3.1 Implement `TaskResult` construction helpers for success and error cases.
- [x] 3.2 Ensure results record status, serialized result or error, timestamps, and attempt metadata.

