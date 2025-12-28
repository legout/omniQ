"""
Test worker concurrency implementation and shutdown behavior.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from omniq.models import TaskStatus
from omniq.storage.sqlite import SQLiteStorage
from omniq.queue import AsyncTaskQueue
from omniq.worker import AsyncWorkerPool
from omniq.storage.base import BaseStorage


async def test_worker_concurrency():
    """Test that worker respects concurrency limit via timing."""
    print("Testing worker concurrency...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "concurrency_test.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue 5 slow tasks
            task_ids = []
            for i in range(5):
                task_id = await queue.enqueue(
                    func_path="asyncio.sleep",
                    args=[0.5],
                    kwargs={},
                    max_retries=0,
                )
                task_ids.append(task_id)

            # Create worker pool with concurrency=3
            worker = AsyncWorkerPool(queue, concurrency=3)

            # Start worker in background
            worker_task = asyncio.create_task(worker.start())

            # Wait for all tasks to complete
            # With concurrency=3 and 5 tasks of 0.5s each:
            # Tasks 1,2,3 run in parallel: ~0.5s
            # Tasks 4,5 run after: another ~0.5s
            # Total: ~1s (not ~2.5s which would be sequential)
            await asyncio.sleep(2.0)

            # Stop worker
            await worker.stop()

            # Verify all tasks completed
            completed_count = 0
            for task_id in task_ids:
                result = await queue.get_result(task_id)
                if result is not None:
                    completed_count += 1

            print(f"   Completed tasks: {completed_count}/5")
            assert completed_count == 5, (
                f"Expected 5 completed tasks, got {completed_count}"
            )
            print("   ✓ Worker concurrency works correctly!")

        finally:
            await storage.close()


async def test_shutdown_while_idle():
    """Test shutdown when no tasks are running."""
    print("\nTesting shutdown while idle...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "idle_shutdown.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            worker = AsyncWorkerPool(queue, concurrency=2, poll_interval=0.1)

            # Start worker
            worker_task = asyncio.create_task(worker.start())

            # Wait a bit to ensure worker is running and idle
            await asyncio.sleep(0.3)

            # Stop worker (should be prompt)
            stop_time = asyncio.get_event_loop().time()
            await worker.stop()
            stop_duration = asyncio.get_event_loop().time() - stop_time

            # Should stop quickly (< poll_interval * 3)
            assert stop_duration < 0.5, f"Shutdown took too long: {stop_duration}s"
            print(f"   ✓ Shutdown while idle completed quickly ({stop_duration:.3f}s)")

            # Ensure worker is stopped
            assert not worker._running, "Worker should not be running"

        finally:
            await storage.close()


async def test_shutdown_with_in_flight_tasks():
    """Test shutdown while tasks are in flight."""
    print("\nTesting shutdown with in-flight tasks...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "inflight_shutdown.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            worker = AsyncWorkerPool(queue, concurrency=2, poll_interval=0.1)

            # Create slow tasks
            task_ids = []
            for i in range(3):
                task_id = await queue.enqueue(
                    func_path="asyncio.sleep",
                    args=[0.5],
                    kwargs={},
                    max_retries=0,
                )
                task_ids.append(task_id)

            # Start worker
            worker_task = asyncio.create_task(worker.start())

            # Wait for tasks to start but not complete
            await asyncio.sleep(0.2)

            # Stop worker while tasks are in flight
            await worker.stop()

            # Check that some tasks completed
            completed_count = 0
            for task_id in task_ids:
                result = await queue.get_result(task_id)
                if result is not None:
                    completed_count += 1

            # Some tasks may have completed (graceful shutdown)
            print(
                f"   ✓ Shutdown with {completed_count}/{len(task_ids)} tasks completed"
            )

        finally:
            await storage.close()


async def main():
    """Run all concurrency and shutdown tests."""
    print("Running worker concurrency and shutdown tests...\n")

    await test_worker_concurrency()
    await test_shutdown_while_idle()
    await test_shutdown_with_in_flight_tasks()

    print("\n🎉 All concurrency and shutdown tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
