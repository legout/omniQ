"""
Basic Usage with AsyncOmniQ

This example demonstrates how to use the AsyncOmniQ interface for asynchronous task processing.
"""

import asyncio
import datetime as dt
from omniq import AsyncOmniQ
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage, PostgresEventStorage


async def main():
    # Create AsyncOmniQ instance with default components
    oq = AsyncOmniQ(
        project_name="my_project",
        task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
        result_store=SQLiteResultStorage(base_dir="some/path"),
        event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
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
        ttl=dt.timedelta(hours=1),
        result_ttl=dt.timedelta(minutes=5)
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
    async with AsyncOmniQ(
        project_name="my_project",
        task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
        result_store=SQLiteResultStorage(base_dir="some/path"),
        event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
    ) as oq:
        task_id = await oq.enqueue(async_task, func_args=dict(name="Tom"))
        result = await oq.get_result(task_id)
        print(f"Context manager result: {result}")


if __name__ == "__main__":
    print("Running basic async usage example...")
    asyncio.run(main())
    
    print("\nRunning context manager example...")
    asyncio.run(context_manager_example())