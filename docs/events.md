# Events

OmniQ features a comprehensive event system that logs various lifecycle events for tasks. This system is crucial for monitoring task progress, debugging issues, and building real-time dashboards or audit trails.

## Key Concepts

*   **Event Types**: Distinct types of events represent different stages or outcomes in a task's lifecycle (e.g., `ENQUEUED`, `STARTED`, `COMPLETED`, `FAILED`, `RETRIED`).
*   **Event Logging**: OmniQ automatically logs events to a configured event storage backend.
*   **Event Processing**: Events can be consumed and processed by external systems or custom handlers for various purposes.

## Event Data Structure

Each event typically includes:

*   `task_id`: Unique identifier of the task.
*   `event_type`: The type of event (e.g., "COMPLETED").
*   `timestamp`: When the event occurred.
*   `details`: Additional context-specific information (e.g., error messages for `FAILED` events, result for `COMPLETED` events).

## Supported Event Storage Backends

OmniQ supports the same storage backends for events as it does for results, providing flexibility in how and where your event data is stored. Refer to the [Storage](storage.md) documentation for details on each backend:

*   **Memory Backend**: Non-persistent, for testing or short-lived data.
*   **File Backend**: Persistent, leveraging `fsspec` for local or cloud storage.
*   **SQLite Backend**: Lightweight, file-based relational database.
*   **PostgreSQL Backend**: Robust and scalable relational database.
*   **Redis Backend**: High-performance in-memory store.
*   **NATS Backend**: Messaging system for distributed event streams.

## Configuring Event Storage

You can configure the event storage backend in your OmniQ settings:

```python
from omniq import OmniQ
from omniq.config import OmniQConfig

# Configure OmniQ to use SQLite for event storage
config = OmniQConfig(
    event_storage_type="sqlite",
    event_storage_path="omniq_events.db"
)

omniq = OmniQ(config=config)
# Events will now be logged to omniq_events.db
```

## Consuming Events

While OmniQ handles event logging internally, you can build custom event consumers to listen for and react to task events. This typically involves interacting directly with the chosen event storage backend or setting up an event processor.

```python
import asyncio
from omniq.events import AsyncEventProcessor, TaskEvent

async def my_event_handler(event: TaskEvent):
    print(f"Received event: {event.event_type} for task {event.task_id}")
    if event.event_type == "COMPLETED":
        print(f"Task {event.task_id} completed with result: {event.details.get('result')}")
    elif event.event_type == "FAILED":
        print(f"Task {event.task_id} failed with error: {event.details.get('error')}")

async def run_event_processor():
    # Assuming you've configured your event storage (e.g., SQLiteEventStorage)
    # The processor would connect to this storage.
    processor = AsyncEventProcessor(event_storage_type="sqlite", event_storage_path="omniq_events.db")
    
    # Register your handler
    processor.register_handler(my_event_handler)
    
    print("Starting event processor...")
    await processor.start() # This would typically run indefinitely

if __name__ == "__main__":
    # Example of how you might run a task and then process its events
    from omniq import AsyncOmniQ

    async def main_with_events():
        async with AsyncOmniQ(
            config=OmniQConfig(event_storage_type="sqlite", event_storage_path="omniq_events.db")
        ) as omniq:
            task_id_success = await omniq.enqueue(lambda: "success!")
            print(f"Enqueued success task: {task_id_success}")
            await asyncio.sleep(1) # Give time for task to process and events to log

            task_id_fail = await omniq.enqueue(lambda: 1/0)
            print(f"Enqueued fail task: {task_id_fail}")
            await asyncio.sleep(1) # Give time for task to process and events to log

        # Now, start the event processor to read these events
        await run_event_processor()

    asyncio.run(main_with_events())
```

This event system provides a powerful mechanism for building resilient and observable task processing workflows.