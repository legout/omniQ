"""
Basic Usage with OmniQ (Sync)

This example demonstrates how to use the synchronous OmniQ interface for task processing.
"""

import datetime as dt
import os
import uuid

from omniq import OmniQ
from omniq.queue import SQLiteQueue
from omniq.results import SQLiteResultStorage
from omniq.events import SQLiteEventStorage
from omniq.workers import ThreadPoolWorker


def main():
    # Create unique database paths for this run
    run_id = uuid.uuid4().hex[:8]
    db_dir = f"./omniq_data_{run_id}"
    os.makedirs(db_dir, exist_ok=True)
    
    queue_db_path = os.path.join(db_dir, "queue.db")
    results_db_path = os.path.join(db_dir, "results.db")
    events_db_path = os.path.join(db_dir, "events.db")

    # Create OmniQ instance with default components
    oq = OmniQ(
        task_queue=SQLiteQueue(db_path=queue_db_path),
        result_storage=SQLiteResultStorage(db_path=results_db_path),
        event_storage=SQLiteEventStorage(db_path=events_db_path),
        worker=ThreadPoolWorker(
            queue=SQLiteQueue(db_path=queue_db_path),
            result_storage=SQLiteResultStorage(db_path=results_db_path),
            event_storage=SQLiteEventStorage(db_path=events_db_path)
        )
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
        ttl=dt.timedelta(hours=1)
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
    run_id = uuid.uuid4().hex[:8]
    db_dir = f"./omniq_data_cm_{run_id}"
    os.makedirs(db_dir, exist_ok=True)

    queue_db_path = os.path.join(db_dir, "queue.db")
    results_db_path = os.path.join(db_dir, "results.db")
    events_db_path = os.path.join(db_dir, "events.db")

    with OmniQ(
        task_queue=SQLiteQueue(db_path=queue_db_path),
        result_storage=SQLiteResultStorage(db_path=results_db_path),
        event_storage=SQLiteEventStorage(db_path=events_db_path),
        worker=ThreadPoolWorker(
            queue=SQLiteQueue(db_path=queue_db_path),
            result_storage=SQLiteResultStorage(db_path=results_db_path),
            event_storage=SQLiteEventStorage(db_path=events_db_path)
        )
    ) as oq:
        task_id = oq.enqueue(simple_task, func_args=dict(name="Tom"))
        result = oq.get_result(task_id)
        print(f"Context manager result: {result}")


if __name__ == "__main__":
    try:
        print("Running basic sync usage example...")
        main()
        
        print("\nRunning context manager example...")
        context_manager_example()
    finally:
        # Clean up generated directories
        for entry in os.listdir("."):
            if entry.startswith("omniq_data_"):
                import shutil
                shutil.rmtree(entry)