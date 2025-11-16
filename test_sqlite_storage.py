#!/usr/bin/env python3
"""Comprehensive test script for SQLiteStorage implementation."""

import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, "src")

from omniq.models import Task, TaskResult, TaskStatus, Schedule
from omniq.storage.base import BaseStorage, TaskError, Serializer
from omniq.storage.sqlite import SQLiteStorage


class MockSerializer:
    """Production-ready mock serializer for testing."""

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

    async def run_sqlite_tests(self):
        print("🧪 Testing SQLiteStorage Implementation")
        print("=" * 50)

        # Create temporary database
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            serializer = MockSerializer()
            storage = SQLiteStorage(db_path, serializer)

            try:
                await self.test_basic_functionality(storage, serializer)
                await self.test_database_schema(storage)
                await self.test_task_lifecycle(storage)
                await self.test_scheduling(storage)
                await self.test_error_handling(storage)
                await self.test_concurrent_operations(storage)

            finally:
                await storage.close()

        print(f"\nTest Results: {self.passed} passed, {self.failed} failed")

    async def test_basic_functionality(self, storage, serializer):
        print("\n📋 Test 1: Basic Functionality")
        print("-" * 40)

        # Test inheritance
        assert isinstance(storage, BaseStorage)
        self.assert_true(True, "SQLiteStorage implements BaseStorage")

        # Test basic enqueue/dequeue
        task = Task.create(func=lambda: "test", eta=datetime.now(timezone.utc))
        task_id = await storage.enqueue(task)
        self.assert_equal(task_id, task.id, "Task ID should match")

        dequeued = await storage.dequeue(datetime.now(timezone.utc))
        self.assert_is_not_none(dequeued, "Should get task from queue")
        self.assert_equal(dequeued.id, task.id, "Task ID should match")

    async def test_database_schema(self, storage):
        print("\n📋 Test 2: Database Schema")
        print("-" * 40)

        # Test that schema is created
        import sqlite3

        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('tasks', 'results')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        self.assert_equal(len(tables), 2, "Both tasks and results tables should exist")
        self.assert_true("tasks" in tables, "tasks table should exist")
        self.assert_true("results" in tables, "results table should exist")

        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        self.assert_true(
            len(indexes) >= 3, f"Should have at least 3 indexes, found {len(indexes)}"
        )
        conn.close()

    async def test_task_lifecycle(self, storage):
        print("\n📋 Test 3: Task Lifecycle")
        print("-" * 40)

        # Create task
        task = Task.create(func=lambda: "result", eta=datetime.now(timezone.utc))
        await storage.enqueue(task)

        # Dequeue and mark as running
        dequeued = await storage.dequeue(datetime.now(timezone.utc))
        self.assert_is_not_none(dequeued, "Should get task")
        await storage.mark_running(task.id)

        # Mark as done
        result = TaskResult.success(task.id, "test_result")
        await storage.mark_done(task.id, result)

        # Retrieve result
        retrieved = await storage.get_result(task.id)
        self.assert_is_not_none(retrieved, "Should get result")
        self.assert_equal(retrieved.status, TaskStatus.SUCCESS, "Should be SUCCESS")
        self.assert_equal(retrieved.result, "test_result", "Result should match")

    async def test_scheduling(self, storage):
        print("\n📋 Test 4: Scheduling (ETA)")
        print("-" * 40)

        now = datetime.now(timezone.utc)
        past = now - timedelta(seconds=30)
        future = now + timedelta(seconds=30)

        # Create tasks with different ETAs
        past_task = Task.create(func=lambda: "past", eta=past)
        future_task = Task.create(func=lambda: "future", eta=future)

        await storage.enqueue(past_task)
        await storage.enqueue(future_task)

        # Should only get past task
        dequeued = await storage.dequeue(now)
        self.assert_is_not_none(dequeued, "Should get due task")
        self.assert_equal(dequeued.id, past_task.id, "Should get past task first")

        # Future task should not be available
        dequeued = await storage.dequeue(now)
        self.assert_equal(dequeued, None, "Future task should not be available")

    async def test_error_handling(self, storage):
        print("\n📋 Test 5: Error Handling")
        print("-" * 40)

        # Test final failure
        fail_task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(fail_task)
        await storage.dequeue(datetime.now(timezone.utc))

        error = TaskError(ValueError("Test error"))
        await storage.mark_failed(fail_task.id, error, will_retry=False)

        result = await storage.get_result(fail_task.id)
        self.assert_is_not_none(result, "Should get error result")
        self.assert_equal(result.status, TaskStatus.FAILED, "Should be FAILED")

        # Test retry
        retry_task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(retry_task)
        await storage.dequeue(datetime.now(timezone.utc))

        await storage.mark_failed(retry_task.id, error, will_retry=True)
        retry_result = await storage.get_result(retry_task.id)
        self.assert_is_not_none(retry_result, "Should get retry result")
        self.assert_equal(
            retry_result.status, TaskStatus.RETRYING, "Should be RETRYING"
        )

    async def test_concurrent_operations(self, storage):
        print("\n📋 Test 6: Concurrent Operations")
        print("-" * 40)

        # Test concurrent dequeues don't claim same task twice
        task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(task)

        async def concurrent_dequeue():
            return await storage.dequeue(datetime.now(timezone.utc))

        results = await asyncio.gather(*[concurrent_dequeue() for _ in range(3)])
        claimed_tasks = [r for r in results if r is not None]

        self.assert_equal(len(claimed_tasks), 1, "Only one process should claim task")
        self.assert_equal(claimed_tasks[0].id, task.id, "Should get correct task")

    async def test_reschedule(self, storage):
        print("\n📋 Test 7: Reschedule")
        print("-" * 40)

        task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
        await storage.enqueue(task)
        await storage.dequeue(datetime.now(timezone.utc))

        # Reschedule for future
        new_eta = datetime.now(timezone.utc) + timedelta(minutes=5)
        await storage.reschedule(task.id, new_eta)

        # Should be able to dequeue again
        rescheduled = await storage.dequeue(new_eta)
        self.assert_is_not_none(rescheduled, "Rescheduled task should be available")
        self.assert_equal(rescheduled.id, task.id, "Should be same task")

    async def test_purge_results(self, storage):
        print("\n📋 Test 8: Purge Results")
        print("-" * 40)

        # Create some test results
        old_result = TaskResult.success("old_task", "old")
        new_result = TaskResult.success("new_task", "new")

        # Manually create results to test purging
        import sqlite3

        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO results (task_id, status, result, completed_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                "old_task",
                "success",
                "old",
                (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            ),
        )

        cursor.execute(
            """
            INSERT INTO results (task_id, status, result, completed_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                "new_task",
                "success",
                "new",
                (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        # Purge old results
        purged = await storage.purge_results(datetime.now(timezone.utc))
        self.assert_true(purged >= 0, "Should not throw error")

        # Check old result is gone
        old_res = await storage.get_result("old_task")
        self.assert_equal(old_res, None, "Old result should be purged")


if __name__ == "__main__":
    runner = TestRunner()
    asyncio.run(runner.run_sqlite_tests())
