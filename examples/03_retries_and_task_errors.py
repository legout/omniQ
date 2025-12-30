"""Retries and task errors example: File backend, deterministic retries, error/result metadata.

Demonstrates:
- File storage backend
- Deterministic retry behavior (fail N times then succeed)
- Task error and result metadata
- Retry budget and exponential backoff
"""

import asyncio
import tempfile
from pathlib import Path

from omniq import AsyncOmniQ
from omniq.config import BackendType, Settings

from tasks import flaky_task, reset_call_counts


async def main():
    print("=== Retries and Task Errors Example ===")
    print()

    reset_call_counts()  # Reset for clean example run

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        settings = Settings(
            backend=BackendType.FILE, base_dir=base_dir, serializer="json"
        )
        omniq = AsyncOmniQ(settings)

        print(f"Using file storage at: {base_dir}")
        print()

        # Enqueue a task that will fail 2 times before succeeding
        print("Enqueuing flaky task (will fail 2 times, then succeed)...")
        task_id = await omniq.enqueue(
            flaky_task, "test-value", fail_before=2, max_retries=3
        )
        print(f"  Task ID: {task_id}")
        print(f"  Config: max_retries=3 (allows up to 4 total executions)")
        print()

        # Process with worker
        print("Starting worker pool (concurrency=1)...")
        workers = omniq.worker(concurrency=1)

        # Start worker in background
        worker_task = asyncio.create_task(workers.start())
        print("  Worker pool started")
        print()

        # Give worker time to process task
        print("Processing task (will retry on failure)...")
        await asyncio.sleep(3.0)
        print()

        # Stop worker
        await workers.stop()
        await asyncio.wait_for(worker_task, timeout=2.0)

        # Get task status
        result = await omniq.get_result(task_id)

        # Examine result and error metadata
        print("Task processing complete!")
        print()

        if result:
            if isinstance(result, dict):
                result_value = result.get("result")
                status = result.get("status")
                attempts = result.get("attempts")
                error = result.get("error")
            else:
                result_value = result.result
                status = result.status
                attempts = result.attempts
                error = result.error

            print(f"  Result: {result_value}")
            print(f"  Status: {status}")
            print(f"  Attempts: {attempts}")
            print()

            if error:
                print("  Final Error Info:")
                if isinstance(error, dict):
                    print(f"    Error type: {error.get('error_type')}")
                    print(f"    Message: {error.get('message')}")
                    print(f"    Retry count: {error.get('retry_count')}")
                elif isinstance(error, str):
                    print(f"    Message: {error}")
                else:
                    print(f"    Error type: {error.error_type}")
                    print(f"    Message: {error.message}")
                    print(f"    Retry count: {error.retry_count}")
                print()

    print("✓ Retries example completed")
    print()
    print("Note: The task is configured to fail 2 times before succeeding.")
    print(
        "  With max_retries=3, it will retry up to 3 times (4 total executions allowed)."
    )


if __name__ == "__main__":
    asyncio.run(main())
