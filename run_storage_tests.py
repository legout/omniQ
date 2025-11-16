#!/usr/bin/env python3
"""Simple test runner for storage tests without pytest."""

import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, "src")

from omniq.models import Task, TaskResult, TaskStatus, Schedule
from omniq.storage.base import TaskError
from omniq.storage.file import FileStorage


class MockSerializer:
    """Mock serializer for testing."""

    def __init__(self):
        self.tasks = {}
        self.results = {}

    async def encode_task(self, task: Task) -> bytes:
        self.tasks[task.id] = task
        import json

        # Serialize task to JSON-compatible format
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

        # Reconstruct Schedule
        schedule = Schedule(
            eta=datetime.fromisoformat(task_data["schedule"]["eta"]).replace(
                tzinfo=timezone.utc
            ),
            interval=task_data["schedule"]["interval"],
            max_retries=task_data["schedule"]["max_retries"],
            timeout=task_data["schedule"]["timeout"],
        )

        # Reconstruct Task
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
        self.results[result.task_id] = result
        import json

        # Serialize result to JSON-compatible format
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


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def assert_equal(self, actual, expected, message=""):
        if actual == expected:
            self.passed += 1
            print(f"  ✅ {message or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  ❌ {message or 'Assertion failed'}: {actual} != {expected}")

    def assert_true(self, condition, message=""):
        if condition:
            self.passed += 1
            print(f"  ✅ {message or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  ❌ {message or 'Assertion failed'}: condition was False")

    def assert_is_not_none(self, value, message=""):
        if value is not None:
            self.passed += 1
            print(f"  ✅ {message or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  ❌ {message or 'Assertion failed'}: value was None")

    async def run_tests(self):
        print("Running storage tests...")

        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir = Path(tmp_dir)
            serializer = MockSerializer()
            storage = FileStorage(temp_dir, serializer)

            try:
                await self.test_enqueue_and_dequeue_basic(storage, serializer)
                await self.test_mark_done_creates_result_file(storage, serializer)
                await self.test_mark_failed_final(storage, serializer)
                await self.test_get_result_nonexistent(storage)
                await self.test_reschedule_task(storage, serializer)

            finally:
                await storage.close()

        print(f"\nTest Results: {self.passed} passed, {self.failed} failed")

    async def test_enqueue_and_dequeue_basic(self, storage, serializer):
        print("\n📋 test_enqueue_and_dequeue_basic")

        # Create a task
        task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))

        # Enqueue the task
        task_id = await storage.enqueue(task)
        self.assert_equal(task_id, task.id, "Task ID should match")

        # Dequeue the task
        dequeued_task = await storage.dequeue(datetime.now(timezone.utc))
        self.assert_is_not_none(dequeued_task, "Dequeued task should not be None")
        if dequeued_task:
            self.assert_equal(
                dequeued_task.id, task.id, "Dequeued task ID should match"
            )
            self.assert_equal(
                dequeued_task.status,
                TaskStatus.PENDING,
                "Task status should be PENDING",
            )

    async def test_mark_done_creates_result_file(self, storage, serializer):
        print("\n📋 test_mark_done_creates_result_file")

        task = Task.create(func=lambda: "result", eta=datetime.now(timezone.utc))
        await storage.enqueue(task)

        # Simulate running the task
        await storage.dequeue(datetime.now(timezone.utc))

        # Mark as done
        result = TaskResult.success(task.id, "test_result")
        await storage.mark_done(task.id, result)

        # Verify result file exists
        result_file = storage.results_dir / f"{task.id}.result"
        self.assert_true(result_file.exists(), "Result file should exist")

        # Verify we can retrieve the result
        retrieved = await storage.get_result(task.id)
        self.assert_is_not_none(retrieved, "Retrieved result should not be None")
        if retrieved:
            self.assert_equal(retrieved.task_id, task.id, "Result task ID should match")

    async def test_mark_failed_final(self, storage, serializer):
        print("\n📋 test_mark_failed_final")

        task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(task)

        # Simulate running and failing
        await storage.dequeue(datetime.now(timezone.utc))

        error = TaskError(ValueError("Test error"))
        await storage.mark_failed(task.id, error, will_retry=False)

        # Verify result file exists
        result = await storage.get_result(task.id)
        self.assert_is_not_none(result, "Result should exist for failed task")
        if result:
            self.assert_equal(
                result.status, TaskStatus.FAILED, "Status should be FAILED"
            )

    async def test_get_result_nonexistent(self, storage):
        print("\n📋 test_get_result_nonexistent")

        result = await storage.get_result("nonexistent")
        self.assert_equal(result, None, "Non-existent task should return None")

    async def test_reschedule_task(self, storage, serializer):
        print("\n📋 test_reschedule_task")

        task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(task)

        # Simulate taking the task
        await storage.dequeue(datetime.now(timezone.utc))

        # Reschedule for future
        from datetime import timedelta

        new_eta = datetime.now(timezone.utc) + timedelta(seconds=60)
        await storage.reschedule(task.id, new_eta)

        # Should be able to dequeue again (task is back in queue)
        dequeued = await storage.dequeue(new_eta)
        self.assert_is_not_none(dequeued, "Rescheduled task should be dequeueable")
        if dequeued:
            self.assert_equal(dequeued.id, task.id, "Rescheduled task ID should match")


if __name__ == "__main__":
    runner = TestRunner()
    asyncio.run(runner.run_tests())
