#!/usr/bin/env python3
"""
Test script to verify FileStorage functionality including new get_task() method.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

from src.omniq.storage.file import FileStorage
from src.omniq.models import Task, TaskStatus, create_task
from src.omniq.serialization import JSONSerializer


async def test_file_storage():
    """Test basic FileStorage functionality."""
    print("Testing FileStorage...")

    # Create temporary directory for storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Test 1: Create and enqueue a task
            print("1. Testing enqueue...")
            task = create_task(
                func_path="test_module.test_function",
                args=[1, 2],
                kwargs={"key": "value"},
                max_retries=3,
                timeout=30,
            )

            task_id = await storage.enqueue(task)
            print(f"   Enqueued task: {task_id}")

            # Test 2: Get task by ID
            print("2. Testing get_task...")
            retrieved_task = await storage.get_task(task_id)
            assert retrieved_task is not None, "Should retrieve task by ID"
            assert retrieved_task["id"] == task_id, "Task ID should match"
            assert retrieved_task["func_path"] == "test_module.test_function", (
                "Function path should match"
            )
            assert retrieved_task["args"] == [1, 2], "Args should match"
            assert retrieved_task["kwargs"] == {"key": "value"}, "Kwargs should match"
            print(f"   Retrieved task: {retrieved_task['id']}")

            # Test 3: Dequeue task
            print("3. Testing dequeue...")
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            dequeued_task = await storage.dequeue(now)
            assert dequeued_task is not None, "Should have dequeued a task"
            assert dequeued_task["id"] == task_id, "Task ID should match"
            assert dequeued_task["status"] == TaskStatus.RUNNING, (
                "Task should be RUNNING"
            )
            print(f"   Dequeued task: {dequeued_task['id']}")

            # Test 4: Get task in RUNNING state
            print("4. Testing get_task for RUNNING task...")
            running_task = await storage.get_task(task_id)
            assert running_task is not None, "Should retrieve running task"
            assert running_task["status"] == TaskStatus.RUNNING, (
                "Task should be RUNNING"
            )
            print("   Successfully retrieved running task")

            # Test 5: Mark task as done
            print("5. Testing mark_done...")
            from src.omniq.models import create_success_result

            result = create_success_result(
                task_id=task_id, result=42, attempts=1, last_attempt_at=now
            )

            await storage.mark_done(task_id, result)
            print("   Task marked as done")

            # Test 6: Get task in DONE state
            print("6. Testing get_task for DONE task...")
            done_task = await storage.get_task(task_id)
            assert done_task is not None, "Should retrieve done task"
            print("   Successfully retrieved done task")

            # Test 7: Test get_task for non-existent task
            print("7. Testing get_task for non-existent task...")
            non_existent_task = await storage.get_task("non-existent-id")
            assert non_existent_task is None, "Should return None for non-existent task"
            print("   Correctly returned None for non-existent task")

            # Test 8: Test reschedule
            print("8. Testing reschedule...")
            task2 = create_task(
                func_path="test_module.scheduled_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            task2_id = await storage.enqueue(task2)
            future_time = datetime.now(timezone.utc)

            await storage.reschedule(task2_id, future_time)
            print("   Task rescheduled successfully")

            # Test 9: Get rescheduled task
            print("9. Testing get_task for rescheduled task...")
            rescheduled_task = await storage.get_task(task2_id)
            assert rescheduled_task is not None, "Should retrieve rescheduled task"
            assert rescheduled_task["id"] == task2_id, "Task ID should match"
            print("   Successfully retrieved rescheduled task")

            print("✓ All FileStorage tests passed!")

        except Exception as e:
            print(f"✗ FileStorage test failed: {e}")
            raise


async def test_file_storage_task_states():
    """Test FileStorage with different task states."""
    print("\nTesting FileStorage task states...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Create tasks in different states
            task1 = create_task(
                func_path="test_module.pending_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            task1_id = await storage.enqueue(task1)

            task2 = create_task(
                func_path="test_module.running_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            task2_id = await storage.enqueue(task2)
            await storage.dequeue(datetime.now(timezone.utc))  # Mark as running

            task3 = create_task(
                func_path="test_module.done_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            task3_id = await storage.enqueue(task3)
            from datetime import datetime, timezone
            from src.omniq.models import create_success_result

            await storage.dequeue(datetime.now(timezone.utc))
            result = create_success_result(
                task3_id, "done", 1, datetime.now(timezone.utc)
            )
            await storage.mark_done(task3_id, result)

            # Test getting tasks in different states
            pending_task = await storage.get_task(task1_id)
            assert pending_task is not None, "Should get pending task"
            assert pending_task["status"] == TaskStatus.PENDING, "Should be PENDING"

            running_task = await storage.get_task(task2_id)
            assert running_task is not None, "Should get running task"
            assert running_task["status"] == TaskStatus.RUNNING, "Should be RUNNING"

            done_task = await storage.get_task(task3_id)
            assert done_task is not None, "Should get done task"
            print("   Successfully retrieved tasks in all states")

            print("✓ FileStorage task states tests passed!")

        except Exception as e:
            print(f"✗ FileStorage task states test failed: {e}")
            raise


async def main():
    """Run all FileStorage tests."""
    print("Running FileStorage tests...\n")

    await test_file_storage()
    await test_file_storage_task_states()

    print("\n🎉 All FileStorage tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
