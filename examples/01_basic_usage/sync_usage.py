"""
Basic Usage with OmniQ (Sync)

This example demonstrates how to use the synchronous OmniQ interface for task processing.
"""

import datetime as dt
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage, PostgresEventStorage


def main():
    # Create OmniQ instance with default components
    oq = OmniQ(
        project_name="my_project",
        task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
        result_store=SQLiteResultStorage(base_dir="some/path"),
        event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
    )

    # Define a task
    def simple_task(name):
        print(f"Hello {name}")
        return name

    # Start the worker
    oq.start_worker()

    # Enqueue a task
    task_id = oq.enqueue(
        func=simple_task,
        func_args=dict(name="Tom"),
        queue_name="low",
        run_in=dt.timedelta(seconds=100),
        ttl=dt.timedelta(hours=1),
        result_ttl=dt.timedelta(minutes=5)
    )

    print(f"Enqueued task with ID: {task_id}")

    # Get the result
    result = oq.get_result(task_id)
    print(f"Task result: {result}")

    # Schedule a recurring task
    schedule_id = oq.schedule(
        func=simple_task,
        func_args=dict(name="Tom"),
        interval=dt.timedelta(seconds=10),
        queue_name="low"
    )

    print(f"Scheduled recurring task with ID: {schedule_id}")

    # Get latest result from scheduled task
    latest_result = oq.get_result(schedule_id=schedule_id, kind="latest")
    print(f"Latest scheduled task result: {latest_result}")

    # Stop the worker
    oq.stop_worker()


def context_manager_example():
    """Example using sync context manager for proper resource management"""
    
    # Define a task
    def simple_task(name):
        print(f"Hello {name}")
        return name

    # Using sync context manager
    with OmniQ(
        project_name="my_project",
        task_queue=FileTaskQueue(base_dir="some/path", queues=["low", "medium", "high"]),
        result_store=SQLiteResultStorage(base_dir="some/path"),
        event_store=PostgresEventStorage(host="localhost", port=5432, username="postgres")
    ) as oq:
        task_id = oq.enqueue(simple_task, func_args=dict(name="Tom"))
        result = oq.get_result(task_id)
        print(f"Context manager result: {result}")


if __name__ == "__main__":
    print("Running basic sync usage example...")
    main()
    
    print("\nRunning context manager example...")
    context_manager_example()