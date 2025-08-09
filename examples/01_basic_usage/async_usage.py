"""
Basic Usage with AsyncOmniQ

This example demonstrates how to use the AsyncOmniQ interface for asynchronous task processing.
"""

import asyncio
import asyncio
import datetime as dt
import os
import uuid

from omniq import AsyncOmniQ
from omniq.queue import SQLiteQueue
from omniq.results import SQLiteResultStorage
from omniq.events import SQLiteEventStorage
from omniq.workers import AsyncWorker


async def main():
    # Create unique database paths for this run
    run_id = uuid.uuid4().hex[:8]
    db_dir = f"./omniq_async_data_{run_id}"
    os.makedirs(db_dir, exist_ok=True)
    
    queue_db_path = os.path.join(db_dir, "async_queue.db")
    results_db_path = os.path.join(db_dir, "async_results.db")
    events_db_path = os.path.join(db_dir, "async_events.db")

    # Create AsyncOmniQ instance with default components
    oq = AsyncOmniQ(
        task_queue=SQLiteQueue(db_path=queue_db_path),
        result_storage=SQLiteResultStorage(db_path=results_db_path),
        event_storage=SQLiteEventStorage(db_path=events_db_path),
        worker=AsyncWorker(
            queue=SQLiteQueue(db_path=queue_db_path),
            result_storage=SQLiteResultStorage(db_path=results_db_path),
            event_storage=SQLiteEventStorage(db_path=events_db_path)
        )
    )

    # Define an async task
    async def async_task(name):
        print(f"Hello {name}")
        return name

    # Start the worker
    await oq.start_worker()

    # Enqueue a task
    task_id = await oq.enqueue(
        func=async_task,
        func_args=dict(name="Tom"),
        queue_name="low",
        run_in=dt.timedelta(seconds=100),
        ttl=dt.timedelta(hours=1)
    )

    print(f"Enqueued task with ID: {task_id}")

    # Get the result
    result = await oq.get_result(task_id)
    print(f"Task result: {result}")

    # Schedule a recurring task
    schedule_id = await oq.schedule(
        func=async_task,
        func_args=dict(name="Tom"),
        interval=dt.timedelta(seconds=10),
        queue_name="low"
    )

    print(f"Scheduled recurring task with ID: {schedule_id}")

    # Get latest result from scheduled task
    latest_result = await oq.get_result(schedule_id=schedule_id, kind="latest")
    print(f"Latest scheduled task result: {latest_result}")

    # Stop the worker
    await oq.stop_worker()


async def context_manager_example():
    """Example using async context manager for proper resource management"""
    
    # Define an async task
    async def async_task(name):
        print(f"Hello {name}")
        return name

    # Using async context manager
    run_id = uuid.uuid4().hex[:8]
    db_dir = f"./omniq_async_data_cm_{run_id}"
    os.makedirs(db_dir, exist_ok=True)

    queue_db_path = os.path.join(db_dir, "async_queue_cm.db")
    results_db_path = os.path.join(db_dir, "async_results_cm.db")
    events_db_path = os.path.join(db_dir, "async_events_cm.db")

    async with AsyncOmniQ(
        task_queue=SQLiteQueue(db_path=queue_db_path),
        result_storage=SQLiteResultStorage(db_path=results_db_path),
        event_storage=SQLiteEventStorage(db_path=events_db_path),
        worker=AsyncWorker(
            queue=SQLiteQueue(db_path=queue_db_path),
            result_storage=SQLiteResultStorage(db_path=results_db_path),
            event_storage=SQLiteEventStorage(db_path=events_db_path)
        )
    ) as oq:
        task_id = await oq.enqueue(async_task, func_args=dict(name="Tom"))
        result = await oq.get_result(task_id)
        print(f"Context manager result: {result}")


if __name__ == "__main__":
    try:
        print("Running basic async usage example...")
        asyncio.run(main())
        
        print("\nRunning context manager example...")
        asyncio.run(context_manager_example())
    finally:
        # Clean up generated directories
        for entry in os.listdir("."):
            if entry.startswith("omniq_async_data_"):
                import shutil
                shutil.rmtree(entry)