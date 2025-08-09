# Task 13: Fault Tolerance and Cleanup

## Objective
To implement fault tolerance mechanisms and automatic task cleanup for the OmniQ library.

## Requirements

### 1. Task TTL Enforcement and Cleanup
- Implement logic in all storage backends (File, Memory, SQLite, PostgreSQL, Redis, NATS) to automatically clean up expired tasks and results based on their TTL. This might involve periodic cleanup routines or on-access checks.

### 2. Retry Logic (`src/omniq/queue/retry.py`)
- Create `src/omniq/queue/retry.py`.
- Implement a `RetryManager` that handles task retries with exponential backoff and jitter.
- Integrate this manager into the worker execution flow so that failed tasks can be retried.

### 3. Circuit Breaker (`src/omniq/backend/circuit_breaker.py`)
- Create `src/omniq/backend/circuit_breaker.py`.
- Implement a `CircuitBreaker` pattern to prevent cascading failures in distributed storage backends.
- Integrate the circuit breaker into the backend interactions to protect against unresponsive or failing storage systems.

### 4. Dead Letter Queue (DLQ)
- Implement a mechanism to move tasks that have exhausted their retries or failed permanently to a Dead Letter Queue for inspection and manual intervention. This might involve a special queue in existing backends or a dedicated storage.

## Completion Criteria
- All storage backends (including newly implemented ones) incorporate task and result TTL enforcement.
- `src/omniq/queue/retry.py` is created with a `RetryManager` and integrated into worker logic.
- `src/omniq/backend/circuit_breaker.py` is created with a `CircuitBreaker` and integrated into backend interactions.
- A Dead Letter Queue mechanism is in place for failed tasks.