# Events

This section will cover the event system and how to use it for monitoring.

The event system in OmniQ allows for tracking the lifecycle of tasks.

**Event Types:**
- `ENQUEUED`
- `EXECUTING`
- `COMPLETE`
- `ERROR`
- `RETRY`
- `CANCELLED`
- `EXPIRED`
- `SCHEDULE_PAUSED`
- `SCHEDULE_RESUMED`

**Key Design Decisions:**
- Non-blocking event logging with disable option
- Structured logging with metadata
- Configurable event retention policies
- Event logging automatically disabled when no event storage is configured
- Store task events without serialization in SQLite, PostgreSQL, or as JSON files
- Track task TTL events and schedule state changes
- Clear separation between library logging and task event logging