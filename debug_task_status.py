#!/usr/bin/env python3
"""
Debug script to understand task status issue.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.file import FileStorage
from src.omniq.models import create_task
from src.omniq.serialization import JSONSerializer
from src.omniq.logging import get_logger
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def debug_task_status():
    """Debug task status flow."""
    print("Debugging task status flow...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.debug_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            print(f"1. Enqueued task: {task_id}")

            # Check initial task status
            initial_task = await queue.get_task(task_id)
            print(f"2. Initial task status: {initial_task['status']}")

            # Dequeue task
            dequeued_task = await queue.dequeue()
            print(f"3. Dequeued task status: {dequeued_task['status']}")
            print(f"   Dequeued task attempts: {dequeued_task['attempts']}")

            # Check task status from storage after dequeue
            storage_task_after_dequeue = await storage.get_task(task_id)
            print(
                f"4. Storage task status after dequeue: {storage_task_after_dequeue['status']}"
            )
            print(f"   Storage task attempts: {storage_task_after_dequeue['attempts']}")

            # Try to fail task
            try:
                await queue.fail_task(task_id, "Debug failure", task=dequeued_task)
                print("5. Task failed successfully")
            except Exception as e:
                print(f"5. Failed to fail task: {e}")

        except Exception as e:
            print(f"Debug failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(debug_task_status())
