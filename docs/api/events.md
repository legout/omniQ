# API - Events

This section provides a detailed API reference for OmniQ's event system, including event models, loggers, and processors. The event system allows for comprehensive tracking of task lifecycles and provides mechanisms for reacting to task-related occurrences.

## Event Models

Events in OmniQ are represented by data models that encapsulate relevant information about a task's state change.

### `omniq.models.event.TaskEvent`

The base model for all task-related events.

*   **Attributes**:
    *   `task_id` (`str`): The unique identifier of the task associated with the event.
    *   `event_type` (`str`): A string representing the type of event (e.g., "ENQUEUED", "STARTED", "COMPLETED", "FAILED").
    *   `timestamp` (`datetime`): The UTC timestamp when the event occurred.
    *   `details` (`Dict[str, Any]`, optional): A dictionary containing additional context-specific information for the event.

### Common Event Types and Their Details

*   **`ENQUEUED`**: Task has been added to a queue.
    *   `details`: `{"queue_name": "default", "task_data": {...}}`
*   **`STARTED`**: Task execution has begun.
    *   `details`: `{"worker_id": "worker-123"}`
*   **`COMPLETED`**: Task finished successfully.
    *   `details`: `{"result": "task_return_value"}`
*   **`FAILED`**: Task execution failed.
    *   `details`: `{"error": "exception_message", "traceback": "full_traceback_string"}`
*   **`RETRIED`**: Task is being retried after a failure.
    *   `details`: `{"attempt": 2, "max_attempts": 3}`
*   **`CANCELLED`**: Task was explicitly cancelled.
    *   `details`: `{"reason": "User cancellation"}`
*   **`TIMEOUT`**: Task timed out during execution.
    *   `details`: `{"timeout_seconds": 300}`

## Event Loggers

Event loggers are responsible for recording `TaskEvent` instances to a configured storage backend.

### `omniq.events.logger.AsyncEventLogger`

The asynchronous event logger.

*   **Methods**:
    *   `async log_event(event: TaskEvent)`: Asynchronously logs a task event.

### `omniq.events.logger.EventLogger`

A synchronous wrapper around `AsyncEventLogger`.

*   **Methods**:
    *   `log_event(event: TaskEvent)`: Synchronously logs a task event.

## Event Processors

Event processors are components that consume events from event storage backends and allow custom handlers to react to them.

### `omniq.events.processor.AsyncEventProcessor`

The asynchronous event processor.

*   **Parameters**:
    *   `event_storage` (`BaseEventStorage`): An instance of an event storage backend.
*   **Methods**:
    *   `register_handler(handler: Callable[[TaskEvent], Awaitable[None]])`: Registers an asynchronous function to be called for each processed event.
    *   `async start()`: Starts the event processing loop.
    *   `async process_events_once()`: Processes all available events in the storage once.

### `omniq.events.processor.EventProcessor`

A synchronous wrapper around `AsyncEventProcessor`.

*   **Methods**:
    *   `register_handler(handler: Callable[[TaskEvent], None])`: Registers a synchronous function to be called for each processed event.
    *   `start()`: Starts the event processing loop.
    *   `process_events_once()`: Processes all available events in the storage once.

## Example Usage

```python
import asyncio
from datetime import datetime
from omniq.models.event import TaskEvent
from omniq.events import AsyncEventLogger, AsyncEventProcessor
from omniq.backend import MemoryBackend # or other backend

async def demonstrate_events():
    event_backend = MemoryBackend() # Using MemoryBackend for simplicity
    event_logger = AsyncEventLogger(event_storage=event_backend)
    event_processor = AsyncEventProcessor(event_storage=event_backend)

    # Define an event handler
    async def my_custom_handler(event: TaskEvent):
        print(f"Custom Handler: {event.event_type} for task {event.task_id} at {event.timestamp}")
        if event.event_type == "COMPLETED":
            print(f"  Result: {event.details.get('result')}")
        elif event.event_type == "FAILED":
            print(f"  Error: {event.details.get('error')}")

    event_processor.register_handler(my_custom_handler)

    # Log some events
    task_id_1 = "task_abc"
    await event_logger.log_event(TaskEvent(task_id=task_id_1, event_type="ENQUEUED", timestamp=datetime.utcnow(), details={"queue": "default"}))
    await event_logger.log_event(TaskEvent(task_id=task_id_1, event_type="STARTED", timestamp=datetime.utcnow()))
    await event_logger.log_event(TaskEvent(task_id=task_id_1, event_type="COMPLETED", timestamp=datetime.utcnow(), details={"result": "success"}))

    task_id_2 = "task_xyz"
    await event_logger.log_event(TaskEvent(task_id=task_id_2, event_type="ENQUEUED", timestamp=datetime.utcnow()))
    await event_logger.log_event(TaskEvent(task_id=task_id_2, event_type="STARTED", timestamp=datetime.utcnow()))
    await event_logger.log_event(TaskEvent(task_id=task_id_2, event_type="FAILED", timestamp=datetime.utcnow(), details={"error": "DivisionByZero", "traceback": "..."}))

    print("\nProcessing events...")
    await event_processor.process_events_once() # Process all events currently in the backend

if __name__ == "__main__":
    asyncio.run(demonstrate_events())
```

The event system provides a powerful foundation for building observable and reactive task processing applications.