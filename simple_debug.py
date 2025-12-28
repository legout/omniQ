#!/usr/bin/env python3
"""
Simple test to debug task status issue.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.omniq.storage.file import FileStorage
from src.omniq.models import create_task
from src.omniq.serialization import JSONSerializer


async def simple_debug():
    """Simple debug of task status."""
    print("Simple debug...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Enqueue task
            task = create_task("test_function", max_retries=2)
            task_id = await storage.enqueue(task)
            print(f"1. Enqueued: {task_id}")

            # Dequeue task
            dequeued = await storage.dequeue(datetime.now(timezone.utc))
            print(f"2. Dequeued status: {dequeued['status']}")

            # Check what files exist
            files = list(Path(temp_dir).glob("queue/*"))
            print(f"3. Files after dequeue: {[f.name for f in files]}")

            # Get task immediately
            immediate = await storage.get_task(task_id)
            print(f"4. Immediate get_task status: {immediate['status']}")

        except Exception as e:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(simple_debug())
