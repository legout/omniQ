#!/usr/bin/env python3
"""
Comprehensive tests for TaskError model and functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.models import (
    TaskError,
    Task,
    TaskStatus,
    create_task,
    has_error,
    is_failed,
    get_error_message,
)
from src.omniq.serialization import (
    serialize_task_error,
    deserialize_task_error,
    JSONSerializer,
)
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.queue import AsyncTaskQueue


def test_task_error_creation():
    """Test TaskError model creation and validation."""
    print("Testing TaskError creation...")

    # Test basic creation
    error = TaskError(
        error_type="runtime",
        message="Test error",
        timestamp=datetime.now(timezone.utc),
    )

    assert error.error_type == "runtime"
    assert error.message == "Test error"
    assert error.retry_count == 0
    assert error.is_retryable is True
    assert error.severity == "error"
    assert error.category == "application"  # Auto-categorized
    print("   ✓ Basic TaskError creation works")

    # Test with all fields
    error_full = TaskError(
        error_type="timeout",
        message="Task timed out",
        timestamp=datetime.now(timezone.utc),
        traceback="Traceback line 1\nTraceback line 2",
        exception_type="TimeoutError",
        context={"timeout": 30, "operation": "test"},
        retry_count=2,
        is_retryable=True,
        max_retries=5,
        severity="critical",
        category="system",
    )

    assert error_full.error_type == "timeout"
    assert error_full.retry_count == 2
    assert error_full.max_retries == 5
    assert error_full.severity == "critical"
    assert error_full.category == "system"
    print("   ✓ Full TaskError creation works")

    # Test auto-categorization
    validation_error = TaskError(
        error_type="validation",
        message="Invalid input",
        timestamp=datetime.now(timezone.utc),
    )
    assert validation_error.category == "user"
    print("   ✓ Auto-categorization works")

    # Test severity validation
    invalid_severity = TaskError(
        error_type="runtime",
        message="Test",
        timestamp=datetime.now(timezone.utc),
        severity="invalid",
    )
    assert invalid_severity.severity == "error"  # Should default to "error"
    print("   ✓ Severity validation works")


def test_task_error_from_exception():
    """Test TaskError.from_exception method."""
    print("\nTesting TaskError.from_exception...")

    # Test from ValueError
    try:
        raise ValueError("Invalid value")
    except Exception as e:
        error = TaskError.from_exception(e, error_type="validation", is_retryable=False)

        assert error.error_type == "validation"
        assert error.message == "Invalid value"
        assert error.exception_type == "ValueError"
        assert error.is_retryable is False
        assert error.traceback is not None
        print("   ✓ TaskError.from_exception works")

    # Test with custom message
    try:
        raise RuntimeError("Runtime error")
    except Exception as e:
        error = TaskError.from_exception(
            e,
            message="Custom error message",
            error_type="runtime",
            context={"custom": "data"},
        )

        assert error.message == "Custom error message"
        assert error.context == {"custom": "data"}
        print("   ✓ Custom message and context work")


def test_task_error_serialization():
    """Test TaskError serialization and deserialization."""
    print("\nTesting TaskError serialization...")

    # Create error with all fields
    original_error = TaskError(
        error_type="timeout",
        message="Task timeout",
        timestamp=datetime.now(timezone.utc),
        traceback="Test traceback",
        exception_type="TimeoutError",
        context={"timeout": 30},
        retry_count=1,
        is_retryable=True,
        max_retries=3,
        severity="error",
        category="system",
    )

    # Test to_dict
    error_dict = original_error.to_dict()
    assert error_dict["error_type"] == "timeout"
    assert error_dict["message"] == "Task timeout"
    assert error_dict["retry_count"] == 1
    assert error_dict["context"] == {"timeout": 30}
    assert "timestamp" in error_dict
    print("   ✓ TaskError.to_dict works")

    # Test from_dict
    deserialized_error = TaskError.from_dict(error_dict)
    assert deserialized_error.error_type == original_error.error_type
    assert deserialized_error.message == original_error.message
    assert deserialized_error.retry_count == original_error.retry_count
    assert deserialized_error.context == original_error.context
    print("   ✓ TaskError.from_dict works")

    # Test roundtrip
    roundtrip_error = TaskError.from_dict(deserialized_error.to_dict())
    assert roundtrip_error.error_type == original_error.error_type
    assert roundtrip_error.message == original_error.message
    print("   ✓ Serialization roundtrip works")


def test_task_error_retry_logic():
    """Test TaskError retry logic."""
    print("\nTesting TaskError retry logic...")

    # Test can_retry without max_retries
    error_unlimited = TaskError(
        error_type="runtime",
        message="Retryable error",
        is_retryable=True,
        retry_count=2,
    )
    assert error_unlimited.can_retry() is True
    print("   ✓ Unlimited retry logic works")

    # Test can_retry with max_retries not reached
    error_limited = TaskError(
        error_type="runtime",
        message="Retryable error",
        is_retryable=True,
        retry_count=2,
        max_retries=5,
    )
    assert error_limited.can_retry() is True
    print("   ✓ Limited retry logic works")

    # Test can_retry with max_retries reached
    error_exhausted = TaskError(
        error_type="runtime",
        message="Retryable error",
        is_retryable=True,
        retry_count=5,
        max_retries=5,
    )
    assert error_exhausted.can_retry() is False
    print("   ✓ Retry exhaustion logic works")

    # Test non-retryable error
    error_non_retryable = TaskError(
        error_type="validation",
        message="Non-retryable error",
        is_retryable=False,
        retry_count=1,
        max_retries=5,
    )
    assert error_non_retryable.can_retry() is False
    print("   ✓ Non-retryable logic works")

    # Test increment_retry
    incremented = error_limited.increment_retry()
    assert incremented.retry_count == 3
    assert incremented.error_type == error_limited.error_type
    assert incremented.message == error_limited.message
    print("   ✓ increment_retry works")


def test_task_model_with_error():
    """Test Task model with error field."""
    print("\nTesting Task model with error...")

    # Test task without error
    task_no_error = create_task(
        func_path="test.function",
        args=[1, 2],
        kwargs={"key": "value"},
    )
    assert not has_error(task_no_error)
    assert not is_failed(task_no_error)
    assert get_error_message(task_no_error) is None
    print("   ✓ Task without error works")

    # Test task with error
    task_error = TaskError(
        error_type="validation",
        message="Task failed validation",
        timestamp=datetime.now(timezone.utc),
    )

    task_with_error = create_task(
        func_path="test.function",
        args=[1, 2],
        kwargs={"key": "value"},
        error=task_error,
    )

    assert has_error(task_with_error)
    assert is_failed(task_with_error)
    assert get_error_message(task_with_error) == "Task failed validation"
    print("   ✓ Task with error works")

    # Test task status FAILED
    task_failed = create_task(
        func_path="test.function",
        args=[1, 2],
        kwargs={"key": "value"},
    )
    task_failed["status"] = TaskStatus.FAILED

    assert is_failed(task_failed)
    print("   ✓ Task status FAILED detection works")


def test_json_serializer_task_error():
    """Test JSON serializer with TaskError."""
    print("\nTesting JSON serializer with TaskError...")

    serializer = JSONSerializer()

    # Create task with error
    task_error = TaskError(
        error_type="timeout",
        message="Task timed out after 30 seconds",
        timestamp=datetime.now(timezone.utc),
        traceback="Test traceback",
        exception_type="TimeoutError",
        context={"timeout": 30},
        retry_count=1,
        is_retryable=True,
    )

    task_with_error = create_task(
        func_path="test.function",
        args=[1, 2],
        kwargs={"key": "value"},
        error=task_error,
    )

    # Test serialization
    encoded = serializer.encode_task(task_with_error)
    assert isinstance(encoded, bytes)
    print("   ✓ JSON serialization with TaskError works")

    # Test deserialization
    decoded = serializer.decode_task(encoded)
    assert decoded["func_path"] == task_with_error["func_path"]
    assert decoded["args"] == task_with_error["args"]
    assert decoded["kwargs"] == task_with_error["kwargs"]

    # Check error field
    decoded_error = decoded.get("error")
    assert decoded_error is not None
    # The JSON serializer returns a TaskError object, not a dict
    assert hasattr(decoded_error, "error_type")
    assert decoded_error.error_type == "timeout"
    assert decoded_error.message == "Task timed out after 30 seconds"
    assert decoded_error.context["timeout"] == 30
    print("   ✓ JSON deserialization with TaskError works")


async def test_storage_task_error():
    """Test storage backend with TaskError."""
    print("\nTesting storage with TaskError...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        storage = SQLiteStorage(db_path)

        try:
            # Create task with error
            task_error = TaskError(
                error_type="runtime",
                message="Storage test error",
                timestamp=datetime.now(timezone.utc),
                context={"test": True},
            )

            task_with_error = create_task(
                func_path="test.function",
                args=[1, 2],
                kwargs={"key": "value"},
                error=task_error,
            )

            # Enqueue task
            task_id = await storage.enqueue(task_with_error)
            assert task_id == task_with_error["id"]
            print("   ✓ Storage enqueue with TaskError works")

            # Retrieve task
            retrieved_task = await storage.get_task(task_id)
            assert retrieved_task is not None
            assert retrieved_task["id"] == task_id
            assert retrieved_task["func_path"] == "test.function"

            # Check error field
            retrieved_error = retrieved_task.get("error")
            assert retrieved_error is not None
            assert retrieved_error.error_type == "runtime"
            assert retrieved_error.message == "Storage test error"
            assert retrieved_error.context["test"] is True
            print("   ✓ Storage retrieval with TaskError works")

            # Test task without error for backward compatibility
            task_no_error = create_task(
                func_path="test.no_error",
                args=[],
                kwargs={},
            )

            task_id_no_error = await storage.enqueue(task_no_error)
            retrieved_no_error = await storage.get_task(task_id_no_error)
            assert retrieved_no_error.get("error") is None
            print("   ✓ Backward compatibility without error works")

        finally:
            await storage.close()


async def test_queue_task_error():
    """Test AsyncTaskQueue with TaskError."""
    print("\nTesting AsyncTaskQueue with TaskError...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_queue.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task with max_retries=0 so it fails immediately
            task_id = await queue.enqueue(
                func_path="test.function",
                args=[1, 2],
                kwargs={"key": "value"},
                max_retries=0,  # No retries allowed
            )

            # Get task
            task = await queue.get_task(task_id)
            assert task is not None
            assert task.get("error") is None
            print("   ✓ Queue enqueue without error works")

            # Simulate task failure with error
            await queue.fail_task(
                task_id=task_id,
                error="Simulated failure",
                exception_type="RuntimeError",
                task=task,
            )

            # Check that task was marked as failed
            failed_task = await queue.get_task(task_id)
            assert failed_task is not None
            assert failed_task["status"] == TaskStatus.FAILED
            print("   ✓ Queue fail_task works")

        finally:
            await storage.close()


def test_performance():
    """Test TaskError performance requirements."""
    print("\nTesting TaskError performance...")

    import time

    # Test TaskError creation performance
    start_time = time.perf_counter()
    for _ in range(1000):
        error = TaskError.from_exception(
            ValueError("Performance test error"),
            error_type="validation",
            is_retryable=False,
        )
    end_time = time.perf_counter()

    avg_creation_time = (end_time - start_time) / 1000
    assert avg_creation_time < 0.001, (
        f"TaskError creation too slow: {avg_creation_time:.6f}s"
    )
    print(
        f"   ✓ TaskError creation performance: {avg_creation_time:.6f}s average (< 1ms)"
    )

    # Test serialization performance
    error = TaskError(
        error_type="runtime",
        message="Performance test",
        timestamp=datetime.now(timezone.utc),
        context={"performance": True},
    )

    start_time = time.perf_counter()
    for _ in range(1000):
        error_dict = error.to_dict()
        TaskError.from_dict(error_dict)
    end_time = time.perf_counter()

    avg_serialization_time = (end_time - start_time) / 1000
    assert avg_serialization_time < 0.001, (
        f"TaskError serialization too slow: {avg_serialization_time:.6f}s"
    )
    print(
        f"   ✓ TaskError serialization performance: {avg_serialization_time:.6f}s average (< 1ms)"
    )


async def main():
    """Run all TaskError tests."""
    print("Running TaskError comprehensive tests...\n")

    # Unit tests
    test_task_error_creation()
    test_task_error_from_exception()
    test_task_error_serialization()
    test_task_error_retry_logic()
    test_task_model_with_error()
    test_json_serializer_task_error()
    test_performance()

    # Integration tests
    await test_storage_task_error()
    await test_queue_task_error()

    print("\n🎉 All TaskError tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
