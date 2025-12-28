#!/usr/bin/env python3
"""
Test atomic claim semantics under concurrency.
"""

import asyncio
import tempfile
from pathlib import Path
from omniq.storage.sqlite import SQLiteStorage
from omniq.queue import AsyncTaskQueue
from omniq.models import TaskStatus


async def test_atomic_claim_under_concurrency():
    """Test that atomic claim works correctly with multiple concurrent operations."""
    print("Testing atomic claim semantics under concurrency...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "atomic_claim.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue a single task
            task_id = await queue.enqueue(
                func_path="asyncio.sleep",
                args=[0.1],
                kwargs={},
                max_retries=0,
            )

            # Create multiple workers that all try to dequeue the same task concurrently
            worker_tasks = []

            async def worker_task(worker_id: int):
                """Worker that tries to dequeue and execute a task."""
                try:
                    task = await queue.dequeue()
                    if task is not None:
                        await asyncio.sleep(0.1)
                        await queue.complete_task(
                            task["id"], f"worker-{worker_id}", task
                        )
                        return worker_id, task["id"]
                    return worker_id, None
                except Exception as e:
                    return worker_id, str(e)

            # Start 5 workers concurrently
            for i in range(5):
                task = asyncio.create_task(worker_task(i))
                worker_tasks.append(task)

            # Wait for all workers to complete
            results = await asyncio.gather(*worker_tasks, return_exceptions=True)

            # Check that only one worker claimed the task
            successful_claims = [
                r for r in results if isinstance(r, tuple) and r[1] == task_id
            ]
            failed_claims = [
                r for r in results if isinstance(r, tuple) and r[0] is not None
            ]

            print(f"   Successful claims: {len(successful_claims)}")
            print(f"   Expected: exactly 1 (atomic claim)")

            assert len(successful_claims) == 1, (
                f"Expected 1 successful claim, got {len(successful_claims)}"
            )
            print("   ✓ Atomic claim semantics work correctly!")

        finally:
            await storage.close()


async def main():
    """Run atomic claim test."""
    print("Running atomic claim semantics test...\n")

    await test_atomic_claim_under_concurrency()

    print("\n🎉 Atomic claim semantics test passed!")


if __name__ == "__main__":
    asyncio.run(main())
