#!/usr/bin/env python3
"""
Test script to verify that invalid transitions remain rejected by can_transition.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.omniq.models import TaskStatus, create_task, transition_status, can_transition
from src.omniq.storage.file import FileStorage
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.serialization import JSONSerializer


def test_invalid_transitions_rejected():
    """Test that invalid transitions are rejected by can_transition."""
    print("Testing invalid transitions are rejected...")

    # Define invalid transitions based on simplified state machine
    invalid_transitions = [
        # From PENDING
        (TaskStatus.PENDING, TaskStatus.SUCCESS),
        (TaskStatus.PENDING, TaskStatus.FAILED),
        # From RUNNING
        (TaskStatus.RUNNING, TaskStatus.PENDING),
        # From SUCCESS (terminal state)
        (TaskStatus.SUCCESS, TaskStatus.PENDING),
        (TaskStatus.SUCCESS, TaskStatus.RUNNING),
        (TaskStatus.SUCCESS, TaskStatus.FAILED),
        (TaskStatus.SUCCESS, TaskStatus.CANCELLED),
        # From FAILED
        (TaskStatus.FAILED, TaskStatus.RUNNING),
        (TaskStatus.FAILED, TaskStatus.SUCCESS),
        # From CANCELLED (terminal state)
        (TaskStatus.CANCELLED, TaskStatus.PENDING),
        (TaskStatus.CANCELLED, TaskStatus.RUNNING),
        (TaskStatus.CANCELLED, TaskStatus.SUCCESS),
        (TaskStatus.CANCELLED, TaskStatus.FAILED),
    ]

    for from_status, to_status in invalid_transitions:
        result = can_transition(from_status, to_status)
        assert not result, (
            f"Invalid transition {from_status.value} → {to_status.value} should be rejected"
        )
        print(f"   ✗ {from_status.value} → {to_status.value} (correctly rejected)")

    print("✓ All invalid transitions are properly rejected!")


def test_valid_transitions_allowed():
    """Test that valid transitions are allowed by can_transition."""
    print("\nTesting valid transitions are allowed...")

    # Define valid transitions based on simplified state machine
    valid_transitions = [
        # From PENDING
        (TaskStatus.PENDING, TaskStatus.PENDING),  # No-op
        (TaskStatus.PENDING, TaskStatus.RUNNING),
        (TaskStatus.PENDING, TaskStatus.CANCELLED),
        # From RUNNING
        (TaskStatus.RUNNING, TaskStatus.RUNNING),  # No-op
        (TaskStatus.RUNNING, TaskStatus.SUCCESS),
        (TaskStatus.RUNNING, TaskStatus.FAILED),
        (TaskStatus.RUNNING, TaskStatus.CANCELLED),
        # From SUCCESS
        (TaskStatus.SUCCESS, TaskStatus.SUCCESS),  # No-op
        # From FAILED
        (TaskStatus.FAILED, TaskStatus.FAILED),  # No-op
        (TaskStatus.FAILED, TaskStatus.PENDING),  # For retries
        (TaskStatus.FAILED, TaskStatus.CANCELLED),
        # From CANCELLED
        (TaskStatus.CANCELLED, TaskStatus.CANCELLED),  # No-op
    ]

    for from_status, to_status in valid_transitions:
        result = can_transition(from_status, to_status)
        assert result, (
            f"Valid transition {from_status.value} → {to_status.value} should be allowed"
        )
        print(f"   ✓ {from_status.value} → {to_status.value} (correctly allowed)")

    print("✓ All valid transitions are properly allowed!")


def test_transition_status_function():
    """Test that transition_status function respects can_transition."""
    print("\nTesting transition_status function...")

    # Test valid transitions
    task = create_task("test_function", max_retries=3)

    # PENDING → RUNNING (valid)
    running_task = transition_status(task, TaskStatus.RUNNING)
    assert running_task["status"] == TaskStatus.RUNNING
    assert running_task["attempts"] == 1  # Should increment attempts
    print("   ✓ PENDING → RUNNING works correctly")

    # RUNNING → SUCCESS (valid)
    success_task = transition_status(running_task, TaskStatus.SUCCESS)
    assert success_task["status"] == TaskStatus.SUCCESS
    assert success_task["attempts"] == 1  # Should not increment attempts
    print("   ✓ RUNNING → SUCCESS works correctly")

    # RUNNING → FAILED (valid)
    failed_task = transition_status(running_task, TaskStatus.FAILED)
    assert failed_task["status"] == TaskStatus.FAILED
    assert failed_task["attempts"] == 1  # Should not increment attempts
    print("   ✓ RUNNING → FAILED works correctly")

    # FAILED → PENDING (valid for retry)
    retry_task = transition_status(failed_task, TaskStatus.PENDING)
    assert retry_task["status"] == TaskStatus.PENDING
    assert retry_task["attempts"] == 1  # Should not increment attempts
    print("   ✓ FAILED → PENDING works correctly")

    # Test invalid transitions
    try:
        # SUCCESS → RUNNING (invalid)
        transition_status(success_task, TaskStatus.RUNNING)
        assert False, "Should have raised ValueError for invalid transition"
    except ValueError as e:
        print(f"   ✓ SUCCESS → RUNNING correctly rejected: {e}")

    try:
        # RUNNING → PENDING (invalid)
        transition_status(running_task, TaskStatus.PENDING)
        assert False, "Should have raised ValueError for invalid transition"
    except ValueError as e:
        print(f"   ✓ RUNNING → PENDING correctly rejected: {e}")

    print("✓ transition_status function works correctly!")


async def test_storage_transition_validation():
    """Test that storage backends respect transition validation."""
    print("\nTesting storage backend transition validation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Test FileStorage
        file_storage = FileStorage(temp_dir, JSONSerializer())

        try:
            task = create_task("test_function", max_retries=3)
            task_id = await file_storage.enqueue(task)

            # First dequeue the task to put it in running state
            running_task = await file_storage.dequeue(datetime.now(timezone.utc))
            assert running_task is not None, "Should have dequeued task"
            assert running_task["status"] == TaskStatus.RUNNING, (
                "Task should be RUNNING"
            )
            print("   ✓ FileStorage: dequeue creates RUNNING state")

            # Try to mark done (should work)
            from src.omniq.models import create_success_result

            result = create_success_result(task_id, "test", 1)
            await file_storage.mark_done(task_id, result)
            print("   ✓ FileStorage: mark_done works")

        except Exception as e:
            print(f"   ✗ FileStorage transition validation failed: {e}")
            raise

        # Test SQLiteStorage
        db_path = Path(temp_dir) / "test_transitions.db"
        sqlite_storage = SQLiteStorage(db_path)

        try:
            task = create_task("test_function", max_retries=3)
            task_id = await sqlite_storage.enqueue(task)

            # Try to mark running without dequeuing (should work)
            await sqlite_storage.mark_running(task_id)
            print("   ✓ SQLiteStorage: mark_running works")

            # Try to mark done without being in running state (should work)
            result = create_success_result(task_id, "test", 1)
            await sqlite_storage.mark_done(task_id, result)
            print("   ✓ SQLiteStorage: mark_done works")

        except Exception as e:
            print(f"   ✗ SQLiteStorage transition validation failed: {e}")
            raise
        finally:
            await sqlite_storage.close()

    print("✓ Storage backend transition validation works correctly!")


async def test_retry_flow_transitions():
    """Test that retry flow uses correct transitions."""
    print("\nTesting retry flow transitions...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Create task
            task = create_task("test_function", max_retries=2)
            task_id = await storage.enqueue(task)

            # Initial state: PENDING
            pending_task = await storage.get_task(task_id)
            assert pending_task["status"] == TaskStatus.PENDING
            print("   ✓ Initial state: PENDING")

            # After dequeue: RUNNING
            running_task = await storage.dequeue(datetime.now(timezone.utc))
            assert running_task["status"] == TaskStatus.RUNNING
            assert running_task["attempts"] == 1
            print("   ✓ After dequeue: RUNNING (attempts=1)")

            # After failure with retry: FAILED (until rescheduled)
            await storage.mark_failed(task_id, "Test failure", will_retry=True)
            failed_task = await storage.get_task(task_id)
            assert failed_task["status"] == TaskStatus.FAILED
            assert failed_task["attempts"] == 1
            print("   ✓ After failure with retry: FAILED (attempts=1)")

            # After reschedule: PENDING
            await storage.reschedule(task_id, datetime.now(timezone.utc))
            retry_pending_task = await storage.get_task(task_id)
            assert retry_pending_task["status"] == TaskStatus.PENDING
            assert retry_pending_task["attempts"] == 1
            print("   ✓ After reschedule: PENDING (attempts=1)")

            # After retry dequeue: RUNNING
            retry_running_task = await storage.dequeue(datetime.now(timezone.utc))
            assert retry_running_task["status"] == TaskStatus.RUNNING
            assert retry_running_task["attempts"] == 2
            print("   ✓ After retry dequeue: RUNNING (attempts=2)")

            # After final failure: FAILED
            await storage.mark_failed(task_id, "Final failure", will_retry=False)
            final_failed_task = await storage.get_task(task_id)
            assert final_failed_task["status"] == TaskStatus.FAILED
            assert final_failed_task["attempts"] == 2
            print("   ✓ After final failure: FAILED (attempts=2)")

            print("✓ Retry flow transitions work correctly!")

        except Exception as e:
            print(f"✗ Retry flow transitions test failed: {e}")
            raise


async def main():
    """Run all transition validation tests."""
    print("Running transition validation tests...\n")

    test_invalid_transitions_rejected()
    test_valid_transitions_allowed()
    test_transition_status_function()
    await test_storage_transition_validation()
    await test_retry_flow_transitions()

    print("\n🎉 All transition validation tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
