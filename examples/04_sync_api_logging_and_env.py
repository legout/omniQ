"""Sync API, logging, and environment configuration example.

Demonstrates:
- OmniQ sync façade for synchronous code
- Settings.from_env() for environment-based configuration
- Loguru logging configuration
- Task correlation with bind_task()
- WorkerPool for sync task execution
"""

import os
import tempfile
from pathlib import Path

from omniq import OmniQ
from omniq.config import BackendType
from omniq.logging import configure, bind_task

from tasks import process_item


def main():
    print("=== Sync API, Logging, and Environment Example ===")
    print()

    # Set environment variables for configuration
    os.environ["OMNIQ_BACKEND"] = BackendType.FILE.value
    os.environ["OMNIQ_SERIALIZER"] = "json"

    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["OMNIQ_BASE_DIR"] = temp_dir

        # Configure logging with correlation support
        configure(level="INFO")
        print("Configured Loguru logging (level=INFO)")
        print()

        # Initialize OmniQ from environment
        omniq = OmniQ.from_env()
        print(f"Initialized OmniQ from environment (backend=file)")
        print(f"  Base directory: {temp_dir}")
        print()

        # Use logging with task correlation
        logger = bind_task("main-process", operation="enqueue")
        logger.info("Enqueueing tasks...")

        # Enqueue tasks (sync API)
        task1_id = omniq.enqueue(process_item, 1, "data-1")
        print(f"  Task 1 enqueued: {task1_id}")

        task2_id = omniq.enqueue(process_item, 2, "data-2")
        print(f"  Task 2 enqueued: {task2_id}")
        print()

        # Create and run sync worker pool
        logger = bind_task("worker-pool", operation="execute")
        logger.info("Starting worker pool...")

        workers = omniq.worker(concurrency=2)
        print(f"  Worker pool created (concurrency=2)")
        print()

        # Start worker in a separate thread
        import threading

        worker_thread = threading.Thread(target=workers.start, daemon=True)
        worker_thread.start()
        print("  Worker pool started")
        print()

        # Wait for tasks to complete
        print("Processing tasks...")
        import time

        time.sleep(2)
        print()

        # Stop worker
        workers.stop(timeout=2.0)
        worker_thread.join(timeout=3.0)

        print()

        # Get results with correlated logging
        logger = bind_task("results", operation="retrieve")
        logger.info("Retrieving results...")

        result1 = omniq.get_result(task1_id)
        result2 = omniq.get_result(task2_id)

        print("Results:")
        if result1:
            result_value = (
                result1["result"]
                if isinstance(result1, dict) and "result" in result1
                else result1
            )
            print(f"  Task 1: {result_value}")
        if result2:
            result_value = (
                result2["result"]
                if isinstance(result2, dict) and "result" in result2
                else result2
            )
            print(f"  Task 2: {result_value}")
        print()

    print("✓ Sync API example completed")


if __name__ == "__main__":
    main()
