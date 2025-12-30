## 1. Tutorials (Learning-Oriented)
- [x] Add tutorial: async quickstart (based on `examples/01_quickstart_async.py`)
- [x] Add tutorial: scheduling with ETA + interval (based on `examples/02_scheduling_eta_and_interval.py`)
- [x] Add tutorial: retries + TaskError + retry budget semantics (based on `examples/03_retries_and_task_errors.py`)
- [x] Add tutorial: logging + env config + sync façade (based on `examples/04_sync_api_logging_and_env.py`)

## 2. How-to Guides (Goal-Oriented)
- [x] How-to: choose file vs sqlite backend
- [x] How-to: run workers (concurrency, polling, shutdown)
- [x] How-to: configure retries and timeouts safely (idempotency guidance included)
- [x] How-to: inspect task results and errors (TaskError usage)
- [x] How-to: configure logging in DEV/PROD via env vars

## 3. Explanation (Conceptual)
- [x] Explanation: OmniQ architecture (façade, queue, worker, storage)
- [x] Explanation: scheduling model (eta + interval)
- [x] Explanation: retry model (attempt counting, max_retries predicate, backoff + jitter)
- [x] Explanation: storage backends tradeoffs and constraints

## 4. Reference (Factual)
- [x] Ensure mkdocstrings API reference includes and links to power-user modules:
  - [x] `omniq.queue`
  - [x] `omniq.worker`
  - [x] `omniq.storage.base`
  - [x] `omniq.storage.file`
  - [x] `omniq.storage.sqlite`
- [x] Add curated reference pages for configuration + environment variables if mkdocstrings output is insufficient

## 5. Validation
- [x] `mkdocs build --strict` passes with no broken links
- [x] Tutorials match runnable examples (no drift)
- [x] README homepage remains unchanged except for improvements intended to be reflected on docs homepage
