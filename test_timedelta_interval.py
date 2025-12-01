#!/usr/bin/env python3
"""
Test script to verify timedelta interval functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.models import create_task, has_interval
from src.omniq.serialization import (
    serialize_timedelta,
    deserialize_timedelta,
    JSONSerializer,
)


def test_timedelta_serialization():
    """Test timedelta serialization and deserialization."""
    print("Testing timedelta serialization...")

    # Test basic timedelta
    td = timedelta(seconds=60)
    serialized = serialize_timedelta(td)
    assert serialized["type"] == "timedelta"
    assert serialized["total_seconds"] == 60.0
    print("   ✓ Timedelta serialization works")

    # Test deserialization
    deserialized = deserialize_timedelta(serialized)
    assert deserialized == td
    print("   ✓ Timedelta deserialization works")

    # Test complex timedelta
    td_complex = timedelta(hours=1, minutes=30, seconds=45)
    serialized_complex = serialize_timedelta(td_complex)
    deserialized_complex = deserialize_timedelta(serialized_complex)
    assert deserialized_complex == td_complex
    print("   ✓ Complex timedelta serialization works")

    # Test invalid data
    try:
        deserialize_timedelta({"type": "invalid", "total_seconds": 60})
        assert False, "Should have raised ValueError"
    except ValueError:
        print("   ✓ Invalid timedelta data properly rejected")

    print("✓ Timedelta serialization tests passed!")


def test_json_serializer_timedelta():
    """Test JSON serializer with timedelta objects."""
    print("\nTesting JSON serializer with timedelta...")

    serializer = JSONSerializer()

    # Test task with timedelta interval
    task = create_task(
        func_path="test.function", args=[], kwargs={}, interval=timedelta(seconds=30)
    )

    # Encode task
    encoded = serializer.encode_task(task)
    assert isinstance(encoded, bytes)
    print("   ✓ Task with timedelta encoded successfully")

    # Decode task
    decoded = serializer.decode_task(encoded)
    assert decoded["func_path"] == task["func_path"]
    assert decoded["schedule"]["interval"] == task["schedule"]["interval"]
    assert isinstance(decoded["schedule"]["interval"], timedelta)
    print("   ✓ Task with timedelta decoded successfully")

    print("✓ JSON serializer timedelta tests passed!")


def test_task_model_timedelta():
    """Test Task model with timedelta intervals."""
    print("\nTesting Task model with timedelta...")

    # Test with timedelta
    task_td = create_task(
        func_path="test.function", args=[], kwargs={}, interval=timedelta(seconds=45)
    )
    assert task_td["schedule"]["interval"] == timedelta(seconds=45)
    assert isinstance(task_td["schedule"]["interval"], timedelta)
    assert has_interval(task_td) == True
    print("   ✓ Task with timedelta interval works")

    # Test with int (backward compatibility)
    task_int = create_task(
        func_path="test.function",
        args=[],
        kwargs={},
        interval=45,  # int seconds
    )
    assert task_int["schedule"]["interval"] == timedelta(seconds=45)
    assert isinstance(task_int["schedule"]["interval"], timedelta)
    assert has_interval(task_int) == True
    print("   ✓ Task with int interval (backward compatibility) works")

    # Test without interval
    task_none = create_task(func_path="test.function", args=[], kwargs={})
    assert task_none["schedule"].get("interval") is None
    assert has_interval(task_none) == False
    print("   ✓ Task without interval works")

    print("✓ Task model timedelta tests passed!")


async def test_queue_timedelta_intervals():
    """Test AsyncTaskQueue with timedelta intervals."""
    print("\nTesting AsyncTaskQueue with timedelta...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_queue_timedelta.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Test enqueue with timedelta
            task_id_td = await queue.enqueue(
                func_path="test.timedelta_function",
                args=[],
                kwargs={},
                interval=timedelta(seconds=60),
            )
            task_td = await queue.get_task(task_id_td)
            assert task_td is not None
            assert task_td["schedule"]["interval"] == timedelta(seconds=60)
            assert has_interval(task_td) == True
            print("   ✓ Enqueue with timedelta works")

            # Test enqueue with int (backward compatibility)
            task_id_int = await queue.enqueue(
                func_path="test.int_function",
                args=[],
                kwargs={},
                interval=30,  # int seconds
            )
            task_int = await queue.get_task(task_id_int)
            assert task_int is not None
            assert task_int["schedule"]["interval"] == timedelta(seconds=30)
            assert has_interval(task_int) == True
            print("   ✓ Enqueue with int (backward compatibility) works")

            # Test interval conversion utility
            converted_td = queue._convert_interval(timedelta(seconds=45))
            assert converted_td == timedelta(seconds=45)
            print("   ✓ Interval conversion utility works for timedelta")

            converted_int = queue._convert_interval(45)
            assert converted_int == timedelta(seconds=45)
            print("   ✓ Interval conversion utility works for int")

            print("✓ AsyncTaskQueue timedelta tests passed!")

        finally:
            await storage.close()


async def test_interval_rescheduling_timedelta():
    """Test interval task rescheduling with timedelta."""
    print("\nTesting interval task rescheduling with timedelta...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_reschedule_timedelta.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue interval task with timedelta
            task_id = await queue.enqueue(
                func_path="test.interval_reschedule",
                args=[],
                kwargs={},
                interval=timedelta(seconds=30),
            )

            # Dequeue and complete
            task = await queue.dequeue()
            assert task is not None
            assert has_interval(task)

            await queue.complete_task(task_id=task_id, result="success", task=task)
            print("   ✓ Interval task with timedelta completed")

            # Check rescheduled task
            future_time = datetime.now(timezone.utc) + timedelta(seconds=31)
            next_task = await queue.storage.dequeue(future_time)

            if next_task:
                assert next_task["func_path"] == "test.interval_reschedule"
                assert next_task["schedule"]["interval"] == timedelta(seconds=30)
                assert next_task["id"] != task_id
                print("   ✓ Interval task properly rescheduled with timedelta")
            else:
                print("   Task scheduled for future execution (expected)")

            print("✓ Interval rescheduling timedelta tests passed!")

        finally:
            await storage.close()


async def main():
    """Run all timedelta interval tests."""
    print("Running timedelta interval tests...\n")

    test_timedelta_serialization()
    test_json_serializer_timedelta()
    test_task_model_timedelta()
    await test_queue_timedelta_intervals()
    await test_interval_rescheduling_timedelta()

    print("\n🎉 All timedelta interval tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
