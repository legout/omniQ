# Task 10: PostgreSQL, Redis, and NATS Backends

## Objective
To implement the PostgreSQL, Redis, and NATS storage backends for the OmniQ library.

## Requirements

### 1. PostgreSQL Backend Implementation (`src/omniq/queue/postgres.py`, `src/omniq/results/postgres.py`, `src/omniq/events/postgres.py`)
- Implement `AsyncPostgresQueue` and `PostgresQueue` for task queues using `asyncpg`. Support multiple named queues using a `queue_name` column.
- Implement `AsyncPostgresResultStorage` and `PostgresResultStorage` for result storage.
- Implement `AsyncPostgresEventStorage` and `PostgresEventStorage` for event storage.
- Ensure all implementations follow the "Async First, Sync Wrapped" design principle.
- Implement task locking mechanism using database transactions and row locking.

### 2. Redis Backend Implementation (`src/omniq/queue/redis.py`, `src/omniq/results/redis.py`)
- Implement `AsyncRedisQueue` and `RedisQueue` for task queues using `redis.asyncio`. Support multiple named queues using prefixes.
- Implement `AsyncRedisResultStorage` and `RedisResultStorage` for result storage.
- Ensure all implementations follow the "Async First, Sync Wrapped" design principle.
- Implement task locking mechanism using Redis atomic operations.

### 3. NATS Backend Implementation (`src/omniq/queue/nats.py`, `src/omniq/results/nats.py`)
- Implement `AsyncNATSQueue` and `NATSQueue` for task queues using `nats.aio`. Support multiple named queues using subject prefixes and NATS queue groups for exclusive consumption.
- Implement `AsyncNATSResultStorage` and `NATSResultStorage` for result storage.
- Ensure all implementations follow the "Async First, Sync Wrapped" design principle.

### 4. Backend Integration (`src/omniq/backend/postgres.py`, `src/omniq/backend/redis.py`, `src/omniq/backend/nats.py`)
- In `src/omniq/backend/postgres.py`, implement `PostgresBackend`.
- In `src/omniq/backend/redis.py`, implement `RedisBackend`.
- In `src/omniq/backend/nats.py`, implement `NATSBackend`.

## Completion Criteria
- `src/omniq/queue/postgres.py`, `src/omniq/results/postgres.py`, `src/omniq/events/postgres.py` are created with PostgreSQL implementations.
- `src/omniq/queue/redis.py`, `src/omniq/results/redis.py` are created with Redis implementations.
- `src/omniq/queue/nats.py`, `src/omniq/results/nats.py` are created with NATS implementations.
- Respective backend integration files are created.
- All implementations adhere to the "Async First, Sync Wrapped" principle and include appropriate locking mechanisms where specified.