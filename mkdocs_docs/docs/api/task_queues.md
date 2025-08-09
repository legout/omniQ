# Task Queues

This section will cover the different task queue implementations available in OmniQ.

OmniQ supports multiple backends for task queues. Each backend has a sync and an async version.

- **File Queue**: Uses the local filesystem for storing tasks.
  - `omniq.queue.file.FileQueue` (sync)
  - `omniq.queue.file.AsyncFileQueue` (async)
- **Memory Queue**: Uses in-memory storage. This is not persistent.
  - `omniq.queue.memory.MemoryQueue` (sync)
  - `omniq.queue.memory.AsyncMemoryQueue` (async)
- **SQLite Queue**: Uses a SQLite database.
  - `omniq.queue.sqlite.SQLiteQueue` (sync)
  - `omniq.queue.sqlite.AsyncSQLiteQueue` (async)
- **PostgreSQL Queue**: Uses a PostgreSQL database.
  - `omniq.queue.postgres.PostgresQueue` (sync)
  - `omniq.queue.postgres.AsyncPostgresQueue` (async)
- **Redis Queue**: Uses a Redis server.
  - `omniq.queue.redis.RedisQueue` (sync)
  - `omniq.queue.redis.AsyncRedisQueue` (async)
- **NATS Queue**: Uses a NATS messaging server.
  - `omniq.queue.nats.NATSQueue` (sync)
  - `omniq.queue.nats.AsyncNATSQueue` (async)

All task queue implementations support multiple named queues:

- File Queue: Directory structure for each queue
- SQLite/PostgreSQL Queue: Queue column approach with priority ordering
- Redis Queue: Queue prefixes
- NATS Queue: Subject prefixes