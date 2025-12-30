"""Quickstart example: AsyncOmniQ façade, worker execution, and result retrieval.

Demonstrates:
- AsyncOmniQ initialization with Settings
- File-based storage backend
- Enqueuing both sync and async tasks
- Worker pool configuration and execution
- Waiting for task results with get_result(wait=True)
"""

import asyncio
import tempfile
from pathlib import Path

from omniq import AsyncOmniQ
from omniq.config import BackendType, Settings

from tasks import async_multiply, sync_add


async def main():
    print("=== Quickstart Example ===")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        settings = Settings(
            backend=BackendType.FILE, base_dir=base_dir, serializer="json"
        )
        omniq = AsyncOmniQ(settings)

        print(f"Using file storage at: {base_dir}")
        print()

        # Enqueue tasks
        print("Enqueuing tasks...")
        sync_task_id = await omniq.enqueue(sync_add, 5, 3)
        print(f"  Sync task enqueued: {sync_task_id}")

        async_task_id = await omniq.enqueue(async_multiply, 4, 7)
        print(f"  Async task enqueued: {async_task_id}")
        print()

        # Process tasks with workers
        print("Starting worker pool (concurrency=2)...")
        workers = omniq.worker(concurrency=2)

        # Start worker in background
        worker_task = asyncio.create_task(workers.start())
        print("  Worker pool started")
        print()

        # Wait for both tasks to complete
        print("Waiting for results...")
        sync_result = await omniq.get_result(sync_task_id, wait=True, timeout=5.0)
        async_result = await omniq.get_result(async_task_id, wait=True, timeout=5.0)
        print()

        # Stop worker
        await workers.stop()
        await asyncio.wait_for(worker_task, timeout=2.0)

        print("Results:")
        sync_value = (
            sync_result["result"]
            if isinstance(sync_result, dict) and "result" in sync_result
            else sync_result
        )
        async_value = (
            async_result["result"]
            if isinstance(async_result, dict) and "result" in async_result
            else async_result
        )
        print(f"  Sync task result: {sync_value if sync_value else 'None'}")
        print(f"  Async task result: {async_value if async_value else 'None'}")
        print()

    print("✓ Quickstart example completed")


if __name__ == "__main__":
    asyncio.run(main())
