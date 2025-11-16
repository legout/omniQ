## Why
OmniQ v1 needs a minimal, well-defined core for representing tasks and their lifecycle so that storage, workers, and public APIs all share the same model. The PRD specifies async-first task execution, simple scheduling, retries, and result retrieval, but there is currently no canonical spec for task fields or status transitions.

## What Changes
- Define the core task model (`Task`, `TaskStatus`, `TaskResult`, `Schedule`) aligned with the v1 PRD.
- Specify how tasks are created from Python callables, including support for `eta`, optional `interval`, `max_retries`, and `timeout`.
- Describe the allowed task status transitions and how results and errors are recorded.
- Capture simple scheduling semantics (`eta` and fixed `interval`) without introducing cron or DAG features.

## Impact
- Provides a shared contract for storage backends, worker pools, and the public API.
- Keeps v1 scope small by focusing only on the core lifecycle needed for enqueue, execute, retry, and retrieve.
- Enables future extensions (advanced scheduling, events, additional backends) without changing the basic task model.

