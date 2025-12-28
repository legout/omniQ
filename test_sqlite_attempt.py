#!/usr/bin/env python3
"""
Test attempt counting with SQLite only.
"""

import asyncio
import tempfile
from pathlib import Path

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.models import create_task


async def test_sqlite_attempt_counting():
    """Test attempt counting with SQLite."""
    print("Testing attempt counting with SQLite...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.attempt_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            print(f"   Enqueued task: {task_id}")

            # First attempt
            task = await queue.dequeue()
            print(f"   Dequeued task status: {task['status']}")
            print(f"   Dequeued task attempts: {task['attempts']}")

            # First failure - let queue fetch task
            await queue.fail_task(task_id, "First failure", task=None)

            print("   ✓ First failure completed")

        except Exception as e:
            print(f"✗ SQLite test failed: {e}")
            raise
        finally:
            await storage.close()


if __name__ == "__main__":
    asyncio.run(test_sqlite_attempt_counting())
