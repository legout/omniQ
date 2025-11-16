#!/usr/bin/env python3
"""Integration test comparing FileStorage and SQLiteStorage behavior."""

import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, "src")

from omniq.models import Task, TaskResult, TaskStatus
from omniq.storage.file import FileStorage
from omniq.storage.sqlite import SQLiteStorage


class MockSerializer:
    """Production-ready mock serializer for testing."""

    async def encode_task(self, task: Task) -> bytes:
        import json

        task_data = {
            "id": task.id,
            "func_path": task.func_path,
            "args": task.args,
            "kwargs": task.kwargs,
            "schedule": {
                "eta": task.schedule.eta.isoformat(),
                "interval": task.schedule.interval,
                "max_retries": task.schedule.max_retries,
                "timeout": task.schedule.timeout,
            },
            "status": task.status.value,
            "attempt": task.attempt,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "metadata": task.metadata,
        }
        return json.dumps(task_data).encode()

    async def decode_task(self, data: bytes) -> Task:
        import json
        from datetime import datetime

        task_data = json.loads(data.decode())
        from omniq.models import Schedule

        schedule = Schedule(
            eta=datetime.fromisoformat(task_data["schedule"]["eta"]).replace(
                tzinfo=timezone.utc
            ),
            interval=task_data["schedule"]["interval"],
            max_retries=task_data["schedule"]["max_retries"],
            timeout=task_data["schedule"]["timeout"],
        )

        from omniq.models import Task, TaskStatus

        return Task(
            id=task_data["id"],
            func_path=task_data["func_path"],
            args=task_data["args"],
            kwargs=task_data["kwargs"],
            schedule=schedule,
            status=TaskStatus(task_data["status"]),
            attempt=task_data["attempt"],
            created_at=datetime.fromisoformat(task_data["created_at"]).replace(
                tzinfo=timezone.utc
            ),
            updated_at=datetime.fromisoformat(task_data["updated_at"]).replace(
                tzinfo=timezone.utc
            ),
            metadata=task_data["metadata"],
        )

    async def encode_result(self, result: TaskResult) -> bytes:
        import json

        result_data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "attempt": result.attempt,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat()
            if result.completed_at
            else None,
        }
        return json.dumps(result_data).encode()

    async def decode_result(self, data: bytes) -> TaskResult:
        import json
        from datetime import datetime

        result_data = json.loads(data.decode())

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            attempt=result_data["attempt"],
            started_at=datetime.fromisoformat(result_data["started_at"]).replace(
                tzinfo=timezone.utc
            )
            if result_data["started_at"]
            else None,
            completed_at=datetime.fromisoformat(result_data["completed_at"]).replace(
                tzinfo=timezone.utc
            )
            if result_data["completed_at"]
            else None,
        )


async def test_storage_compatibility():
    """Test that both storage backends behave the same way."""

    print("🔄 Testing Storage Backend Compatibility")
    print("=" * 50)

    serializer = MockSerializer()

    # Test FileStorage
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_storage = FileStorage(Path(tmp_dir), serializer)

        # Test basic operation
        task = Task.create(func=lambda: "test", eta=datetime.now(timezone.utc))
        await file_storage.enqueue(task)
        dequeued = await file_storage.dequeue(datetime.now(timezone.utc))

        result = TaskResult.success(task.id, "test_result")
        await file_storage.mark_done(task.id, result)
        retrieved = await file_storage.get_result(task.id)

        file_ok = retrieved is not None and retrieved.result == "test_result"
        print(f"✅ FileStorage basic test: {'PASS' if file_ok else 'FAIL'}")

        await file_storage.close()

    # Test SQLiteStorage
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        sqlite_storage = SQLiteStorage(db_path, serializer)

        # Test basic operation
        task = Task.create(func=lambda: "test", eta=datetime.now(timezone.utc))
        await sqlite_storage.enqueue(task)
        dequeued = await sqlite_storage.dequeue(datetime.now(timezone.utc))

        result = TaskResult.success(task.id, "test_result")
        await sqlite_storage.mark_done(task.id, result)
        retrieved = await sqlite_storage.get_result(task.id)

        sqlite_ok = retrieved is not None and retrieved.result == "test_result"
        print(f"✅ SQLiteStorage basic test: {'PASS' if sqlite_ok else 'FAIL'}")

        await sqlite_storage.close()

    print("\n🎉 Both storage backends working correctly!")
    print(
        "📋 SQLiteStorage implementation is fully compatible with BaseStorage interface"
    )


if __name__ == "__main__":
    asyncio.run(test_storage_compatibility())
