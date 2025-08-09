# Examples

This section provides practical examples demonstrating various features and usage patterns of OmniQ. These examples are designed to help you quickly understand how to integrate OmniQ into your projects.

## 1. Basic Usage

This example covers the fundamental concepts of enqueuing and retrieving tasks with both synchronous and asynchronous OmniQ instances.

*   **Synchronous Example**:
    ```python
    from omniq import OmniQ
    import time

    def simple_sync_task(message):
        print(f"Sync task received: {message}")
        time.sleep(0.5)
        return f"Processed: {message}"

    with OmniQ() as omniq:
        print("Enqueuing synchronous task...")
        task_id = omniq.enqueue(simple_sync_task, "Hello, Sync World!")
        result = omniq.get_result(task_id)
        print(f"Synchronous task result: {result}")
    ```

*   **Asynchronous Example**:
    ```python
    import asyncio
    from omniq import AsyncOmniQ

    async def simple_async_task(message):
        print(f"Async task received: {message}")
        await asyncio.sleep(0.5)
        return f"Processed async: {message}"

    async def main_async_basic():
        async with AsyncOmniQ() as omniq:
            print("Enqueuing asynchronous task...")
            task_id = await omniq.enqueue(simple_async_task, "Hello, Async World!")
            result = await omniq.get_result(task_id)
            print(f"Asynchronous task result: {result}")

    if __name__ == "__main__":
        asyncio.run(main_async_basic())
    ```

## 2. Using Different Backends

Demonstrates how to configure OmniQ to use different storage backends for task queues, results, and events.

```python
import asyncio
from omniq import OmniQ, AsyncOmniQ
from omniq.config import OmniQConfig

# Configure OmniQ with different backends
config = OmniQConfig(
    task_queue_type="sqlite",
    task_queue_path="tasks.db",
    result_storage_type="file",
    result_storage_base_dir="./results_data",
    event_storage_type="memory"
)

def process_data(data):
    print(f"Processing data: {data}")
    return data.upper()

async def async_process_data(data):
    print(f"Processing async data: {data}")
    await asyncio.sleep(0.1)
    return data.lower()

async def main_backend_example():
    # Synchronous usage
    with OmniQ(config=config) as omniq_sync:
        print("\n--- Synchronous Backend Example ---")
        sync_task_id = omniq_sync.enqueue(process_data, "sync item")
        sync_result = omniq_sync.get_result(sync_task_id)
        print(f"Sync result: {sync_result}")

    # Asynchronous usage
    async with AsyncOmniQ(config=config) as omniq_async:
        print("\n--- Asynchronous Backend Example ---")
        async_task_id = await omniq_async.enqueue(async_process_data, "ASYNC ITEM")
        async_result = await omniq_async.get_result(async_task_id)
        print(f"Async result: {async_result}")

if __name__ == "__main__":
    asyncio.run(main_backend_example())
```

## 3. Working with Multiple Queues

Illustrates how to use named queues to categorize and prioritize tasks.

```python
import asyncio
from omniq import AsyncOmniQ

async def high_priority_task(item):
    print(f"High priority processing: {item}")
    await asyncio.sleep(0.1)
    return f"HP: {item}"

async def low_priority_task(item):
    print(f"Low priority processing: {item}")
    await asyncio.sleep(0.5)
    return f"LP: {item}"

async def main_multiple_queues():
    async with AsyncOmniQ() as omniq:
        print("\n--- Multiple Queues Example ---")
        
        # Enqueue tasks to different queues
        task1_id = await omniq.enqueue(low_priority_task, "data A", queue_name="low_prio")
        task2_id = await omniq.enqueue(high_priority_task, "data B", queue_name="high_prio")
        task3_id = await omniq.enqueue(low_priority_task, "data C", queue_name="low_prio")
        task4_id = await omniq.enqueue(high_priority_task, "data D", queue_name="high_prio")

        # In a real scenario, workers would be configured to pull from these queues
        # For demonstration, we'll just retrieve results in order of enqueueing
        results = await asyncio.gather(
            omniq.get_result(task1_id),
            omniq.get_result(task2_id),
            omniq.get_result(task3_id),
            omniq.get_result(task4_id)
        )
        print("All results received:", results)

if __name__ == "__main__":
    asyncio.run(main_multiple_queues())
```

## 4. Task Scheduling and Dependencies

(This example assumes scheduling and dependency features are implemented)

```python
# import asyncio
# from datetime import datetime, timedelta
# from omniq import AsyncOmniQ
# from omniq.models import Schedule, Task

# async def dependent_task(data):
#     print(f"Dependent task received data: {data}")
#     return f"Processed dependent: {data}"

# async def initial_task():
#     print("Initial task completed.")
#     return "initial_data"

# async def main_scheduling():
#     async with AsyncOmniQ() as omniq:
#         print("\n--- Scheduling and Dependencies Example ---")
        
#         # Schedule a task to run 5 seconds from now
#         scheduled_time = datetime.now() + timedelta(seconds=5)
#         schedule = Schedule(run_at=scheduled_time)
#         scheduled_task_id = await omniq.enqueue(initial_task, schedule=schedule)
#         print(f"Initial task scheduled for: {scheduled_time}")

#         # Create a task that depends on the initial task
#         dependent_task_obj = Task(
#             func=dependent_task,
#             args=("data from initial",),
#             depends_on=[scheduled_task_id]
#         )
#         dependent_id = await omniq.enqueue(dependent_task_obj)
#         print(f"Dependent task enqueued, waiting for: {scheduled_task_id}")

#         # Wait for results
#         initial_result = await omniq.get_result(scheduled_task_id)
#         dependent_result = await omniq.get_result(dependent_id)
        
#         print(f"Initial task result: {initial_result}")
#         print(f"Dependent task result: {dependent_result}")

# if __name__ == "__main__":
#     asyncio.run(main_scheduling())
```

## 5. Event Monitoring

Demonstrates how to set up an event processor to monitor task lifecycle events.

```python
import asyncio
from omniq import AsyncOmniQ
from omniq.config import OmniQConfig
from omniq.events import AsyncEventProcessor, TaskEvent

async def event_handler(event: TaskEvent):
    print(f"[{event.timestamp.isoformat()}] Event: {event.event_type} "
          f"| Task ID: {event.task_id} | Details: {event.details}")

async def main_event_monitoring():
    # Configure OmniQ to log events to SQLite for easy retrieval
    config = OmniQConfig(
        event_storage_type="sqlite",
        event_storage_path="event_monitor.db"
    )

    async with AsyncOmniQ(config=config) as omniq:
        print("\n--- Event Monitoring Example ---")
        
        # Enqueue a successful task
        task_success_id = await omniq.enqueue(lambda: "Task completed successfully!")
        print(f"Enqueued success task: {task_success_id}")
        
        # Enqueue a task that will fail
        task_fail_id = await omniq.enqueue(lambda: 1 / 0)
        print(f"Enqueued failing task: {task_fail_id}")

        # Give some time for tasks to process and events to be logged
        await asyncio.sleep(2)

    # Now, set up an event processor to read and print events
    # Note: In a real application, the event processor would likely run in a separate process/service
    event_processor = AsyncEventProcessor(
        event_storage_type="sqlite",
        event_storage_path="event_monitor.db"
    )
    event_processor.register_handler(event_handler)
    
    print("\n--- Fetching and Processing Events ---")
    # Fetch events that occurred in the last 5 minutes (or specific task IDs)
    # For this example, we'll just process all available events until done
    await event_processor.process_events_once() # Process all events currently in storage
    print("Finished processing events.")

if __name__ == "__main__":
    asyncio.run(main_event_monitoring())
```

These examples cover common usage patterns. Explore the [API Documentation](api/backends.md) for a full list of features and advanced configurations.