import pytest
from datetime import datetime, timedelta
from omniq.models.schedule import Schedule

def test_schedule_creation_interval():
    """Test basic Schedule object creation with interval timing."""
    schedule = Schedule(
        timing_type="interval",
        timing_value=60.0,  # Every 60 seconds
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-1"
    )
    assert schedule.id == "test-schedule-1"
    assert schedule.timing_type == "interval"
    assert schedule.timing_value == 60.0
    assert schedule.is_active is True
    assert "func" in schedule.task_data
    assert callable(schedule.task_data["func"])
    assert schedule.task_data["args"] == (5,)

def test_schedule_creation_cron():
    """Test Schedule object creation with cron expression."""
    schedule = Schedule(
        timing_type="cron",
        timing_value="*/5 * * * *",  # Every 5 minutes
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-2"
    )
    assert schedule.id == "test-schedule-2"
    assert schedule.timing_type == "cron"
    assert schedule.timing_value == "*/5 * * * *"
    assert schedule.is_active is True

def test_schedule_creation_timestamp():
    """Test Schedule object creation with specific timestamp."""
    future_time = datetime.now().timestamp() + 600  # 10 minutes from now
    schedule = Schedule(
        timing_type="timestamp",
        timing_value=future_time,
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-3"
    )
    assert schedule.id == "test-schedule-3"
    assert schedule.timing_type == "timestamp"
    assert schedule.timing_value == future_time
    assert schedule.is_active is True

def test_schedule_pause_resume():
    """Test pausing and resuming a schedule."""
    schedule = Schedule(
        timing_type="interval",
        timing_value=60.0,
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-4"
    )
    assert schedule.is_active is True
    schedule.pause()
    assert schedule.is_active is False
    schedule.resume()
    assert schedule.is_active is True

def test_schedule_is_due_interval_first_time():
    """Test if a schedule with interval timing is due for the first time."""
    schedule = Schedule(
        timing_type="interval",
        timing_value=60.0,
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-5",
        last_execution=None
    )
    assert schedule.is_due() is True  # Should be due since it has never run

def test_schedule_is_due_timestamp_future():
    """Test if a schedule with timestamp timing in the future is not due yet."""
    future_time = datetime.now().timestamp() + 600  # 10 minutes from now
    schedule = Schedule(
        timing_type="timestamp",
        timing_value=future_time,
        task_data={"func": lambda x: x * 2, "args": (5,), "kwargs": {}},
        id="test-schedule-6"
    )
    assert schedule.is_due() is False  # Should not be due yet
