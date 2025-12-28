"""
Test worker concurrency implementation.
"""

import asyncio
import tempfile
from pathlib import Path
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.queue import AsyncTaskQueue
from src.omniq.worker import AsyncWorkerPool


async def test_worker_concurrency():
    """Test that worker actually runs tasks concurrently."""
    print("Testing worker concurrency...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "concurrency_test.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        # Track execution overlap
        active_tasks = set()
        max_concurrent = 0

        # Create 5 tasks that each take 1 second
        async def slow_task(x):
            task_id = f"task_{x}"
            active_tasks.add(task_id)
            max_concurrent = max(max_concurrent, len(active_tasks))
            await asyncio.sleep(1.0)
            active_tasks.discard(task_id)
            return x * 2

        # Enqueue 5 tasks
        for i in range(5):
            await queue.enqueue(
                func_path="test_worker_concurrency.slow_task",
                args=[i],
                kwargs={},
            )

        # Create worker pool with concurrency=3
        worker = AsyncWorkerPool(queue, concurrency=3)

        # Start worker in background
        worker_task = asyncio.create_task(worker.start())

        # Let tasks run
        await asyncio.sleep(3.5)

        # Stop worker
        await worker.stop()

        # Check results
        print(f"   Max concurrent tasks: {max_concurrent}")
        print(f"   Expected: 3 (concurrency limit)")

        assert max_concurrent == 3, f"Expected 3 concurrent tasks, got {max_concurrent}"
        print("   Worker concurrency works correctly!")

        await storage.close()


if __name__ == "__main__":
    asyncio.run(test_worker_concurrency())
    print("Worker concurrency test passed!")
