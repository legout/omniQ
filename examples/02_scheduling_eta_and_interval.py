"""Scheduling example: Delayed execution with ETA and interval tasks.

Demonstrates:
- Task scheduling with eta (delayed execution)
- Repeating tasks with interval
- Worker polling behavior
- Interval task rescheduling (new task IDs each execution)
"""

import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from omniq import AsyncOmniQ
from omniq.config import BackendType, Settings

from tasks import echo_task


async def main():
    print("=== Scheduling Example ===")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        settings = Settings(
            backend=BackendType.FILE, base_dir=base_dir, serializer="json"
        )
        omniq = AsyncOmniQ(settings)

        # Enqueue a task with ETA (delayed execution)
        print("Enqueuing task with ETA (delayed by 1 second)...")
        eta_task_id = await omniq.enqueue(
            echo_task,
            "delayed-task",
            eta=datetime.now(timezone.utc) + timedelta(seconds=1),
        )
        print(f"  ETA task ID: {eta_task_id}")
        print()

        # Enqueue an interval task (repeating every 0.5 seconds)
        print("Enqueuing interval task (repeats every 0.5 seconds)...")
        interval_task_id = await omniq.enqueue(
            echo_task,
            "interval-task",
            interval=500,  # milliseconds
        )
        print(f"  Interval task ID: {interval_task_id}")
        print()

        # Process tasks with workers
        print("Starting worker pool (concurrency=1)...")
        workers = omniq.worker(concurrency=1)

        # Start worker in background
        worker_task = asyncio.create_task(workers.start())
        print("  Worker pool started")
        print()

        # Let workers process for 2.5 seconds
        # This allows:
        # - The ETA task to execute after 1 second delay
        # - Multiple interval task executions (approx 4-5 runs)
        print("Processing tasks for 2.5 seconds...")
        await asyncio.sleep(2.5)
        print()

        # Stop worker
        await workers.stop()
        await asyncio.wait_for(worker_task, timeout=2.0)

        print("✓ Scheduling example completed")


if __name__ == "__main__":
    asyncio.run(main())
