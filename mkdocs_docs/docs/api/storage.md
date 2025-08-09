# Storage

This section will explain the storage options for task results and events.

## Result Storage

OmniQ can store the results of tasks in various backends:

- **File Storage**:
  - `omniq.results.file.FileResultStorage` (sync)
  - `omniq.results.file.AsyncFileResultStorage` (async)
- **Memory Storage**:
  - `omniq.results.memory.MemoryResultStorage` (sync)
  - `omniq.results.memory.AsyncMemoryResultStorage` (async)
- **SQLite Storage**:
  - `omniq.results.sqlite.SQLiteResultStorage` (sync)
  - `omniq.results.sqlite.AsyncSQLiteResultStorage` (async)
- **PostgreSQL Storage**:
  - `omniq.results.postgres.PostgresResultStorage` (sync)
  - `omniq.results.postgres.AsyncPostgresResultStorage` (async)
- **Redis Storage**:
  - `omniq.results.redis.RedisResultStorage` (sync)
  - `omniq.results.redis.AsyncRedisResultStorage` (async)
- **NATS Storage**:
  - `omniq.results.nats.NATSResultStorage` (sync)
  - `omniq.results.nats.AsyncNATSResultStorage` (async)

## Event Storage

Task lifecycle events can be stored for monitoring and debugging:

- **SQLite Storage**:
  - `omniq.events.sqlite.SQLiteEventStorage` (sync)
  - `omniq.events.sqlite.AsyncSQLiteEventStorage` (async)
- **PostgreSQL Storage**:
  - `omniq.events.postgres.PostgresEventStorage` (sync)
  - `omniq.events.postgres.AsyncPostgresEventStorage` (async)
- **File Storage**:
  - `omniq.events.file.FileEventStorage` (sync)
  - `omniq.events.file.AsyncFileEventStorage` (async)