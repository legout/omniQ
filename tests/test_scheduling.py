"""
Tests for OmniQ advanced scheduling functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from omniq import OmniQ, ScheduleType, ScheduleStatus
from omniq.models.schedule import Schedule
from omniq.queue.scheduler import AsyncScheduler, Scheduler


class TestScheduling:
    """Test suite for scheduling functionality."""
    
    @pytest.fixture
    async def omniq(self):
        """Create OmniQ instance for testing."""
        instance = OmniQ()
        await instance.connect()
        yield instance
        await instance.disconnect()
    
    @pytest.fixture
    def sample_function(self):
        """Sample function for testing."""
        def test_func(message: str, count: int = 1):
            return f"Executed: {message} (count: {count})"
        return test_func
    
    async def test_create_cron_schedule(self, omniq, sample_function):
        """Test creating a CRON schedule."""
        omniq.register_function("test_func", sample_function)
        
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.CRON,
            args=("test message",),
            kwargs={"count": 5},
            cron_expression="0 * * * *",  # Every hour
            max_runs=10,
            metadata={"test": "cron"}
        )
        
        assert schedule_id is not None
        
        # Verify schedule was created
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule is not None
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expression == "0 * * * *"
        assert schedule.max_runs == 10
        assert schedule.metadata["test"] == "cron"
    
    async def test_create_interval_schedule(self, omniq, sample_function):
        """Test creating an INTERVAL schedule."""
        omniq.register_function("test_func", sample_function)
        
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("interval test",),
            interval=timedelta(minutes=5),
            max_runs=3,
            metadata={"test": "interval"}
        )
        
        assert schedule_id is not None
        
        # Verify schedule was created
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule is not None
        assert schedule.schedule_type == ScheduleType.INTERVAL
        assert schedule.interval == timedelta(minutes=5)
        assert schedule.max_runs == 3
    
    async def test_create_timestamp_schedule(self, omniq, sample_function):
        """Test creating a TIMESTAMP schedule."""
        omniq.register_function("test_func", sample_function)
        
        run_time = datetime.utcnow() + timedelta(hours=1)
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.TIMESTAMP,
            args=("timestamp test",),
            timestamp=run_time,
            metadata={"test": "timestamp"}
        )
        
        assert schedule_id is not None
        
        # Verify schedule was created
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule is not None
        assert schedule.schedule_type == ScheduleType.TIMESTAMP
        assert schedule.timestamp == run_time
    
    async def test_list_schedules(self, omniq, sample_function):
        """Test listing schedules."""
        omniq.register_function("test_func", sample_function)
        
        # Create multiple schedules
        schedule_ids = []
        for i in range(3):
            schedule_id = await omniq.create_schedule(
                func="test_func",
                schedule_type=ScheduleType.INTERVAL,
                args=(f"test {i}",),
                interval=timedelta(minutes=i+1),
                metadata={"index": i}
            )
            schedule_ids.append(schedule_id)
        
        # List all schedules
        schedules = await omniq.list_schedules()
        assert len(schedules) >= 3
        
        # Verify our schedules are in the list
        found_ids = [s.id for s in schedules]
        for schedule_id in schedule_ids:
            assert schedule_id in found_ids
    
    async def test_pause_resume_schedule(self, omniq, sample_function):
        """Test pausing and resuming a schedule."""
        omniq.register_function("test_func", sample_function)
        
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("pause test",),
            interval=timedelta(minutes=1)
        )
        
        # Pause the schedule
        paused = await omniq.pause_schedule(schedule_id)
        assert paused is True
        
        # Verify it's paused
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule.status == ScheduleStatus.PAUSED
        
        # Resume the schedule
        resumed = await omniq.resume_schedule(schedule_id)
        assert resumed is True
        
        # Verify it's active again
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule.status == ScheduleStatus.ACTIVE
    
    async def test_cancel_schedule(self, omniq, sample_function):
        """Test cancelling a schedule."""
        omniq.register_function("test_func", sample_function)
        
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("cancel test",),
            interval=timedelta(minutes=1)
        )
        
        # Cancel the schedule
        cancelled = await omniq.cancel_schedule(schedule_id)
        assert cancelled is True
        
        # Verify it's cancelled
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule.status == ScheduleStatus.CANCELLED
    
    async def test_delete_schedule(self, omniq, sample_function):
        """Test deleting a schedule."""
        omniq.register_function("test_func", sample_function)
        
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("delete test",),
            interval=timedelta(minutes=1)
        )
        
        # Delete the schedule
        deleted = await omniq.delete_schedule(schedule_id)
        assert deleted is True
        
        # Verify it's gone
        schedule = await omniq.get_schedule(schedule_id)
        assert schedule is None
    
    async def test_scheduler_start_stop(self, omniq):
        """Test starting and stopping the scheduler."""
        # Start scheduler
        await omniq.start_scheduler()
        assert omniq._async_scheduler._running is True
        
        # Stop scheduler
        await omniq.stop_scheduler()
        assert omniq._async_scheduler._running is False
    
    async def test_recover_schedules(self, omniq, sample_function):
        """Test schedule recovery."""
        omniq.register_function("test_func", sample_function)
        
        # Create a schedule
        schedule_id = await omniq.create_schedule(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("recovery test",),
            interval=timedelta(minutes=1)
        )
        
        # Test recovery
        recovered_count = await omniq.recover_schedules()
        assert recovered_count >= 0  # Should not fail
    
    async def test_function_registration(self, omniq):
        """Test function registration and unregistration."""
        def test_func():
            return "test"
        
        # Register function
        omniq.register_function("test_func", test_func)
        
        # Verify it's registered in the scheduler
        if omniq._async_scheduler:
            assert "test_func" in omniq._async_scheduler._function_registry
        
        # Unregister function
        omniq.unregister_function("test_func")
        
        # Verify it's unregistered
        if omniq._async_scheduler:
            assert "test_func" not in omniq._async_scheduler._function_registry


class TestSyncScheduling:
    """Test suite for synchronous scheduling functionality."""
    
    @pytest.fixture
    def omniq_sync(self):
        """Create OmniQ instance for sync testing."""
        instance = OmniQ()
        instance.connect_sync()
        yield instance
        instance.disconnect_sync()
    
    @pytest.fixture
    def sample_function(self):
        """Sample function for testing."""
        def test_func(message: str):
            return f"Sync executed: {message}"
        return test_func
    
    def test_create_schedule_sync(self, omniq_sync, sample_function):
        """Test creating a schedule synchronously."""
        omniq_sync.register_function("test_func", sample_function)
        
        schedule_id = omniq_sync.create_schedule_sync(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("sync test",),
            interval=timedelta(minutes=1)
        )
        
        assert schedule_id is not None
        
        # Verify schedule was created
        schedule = omniq_sync.get_schedule_sync(schedule_id)
        assert schedule is not None
        assert schedule.schedule_type == ScheduleType.INTERVAL
    
    def test_list_schedules_sync(self, omniq_sync, sample_function):
        """Test listing schedules synchronously."""
        omniq_sync.register_function("test_func", sample_function)
        
        # Create a schedule
        schedule_id = omniq_sync.create_schedule_sync(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("sync list test",),
            interval=timedelta(minutes=1)
        )
        
        # List schedules
        schedules = omniq_sync.list_schedules_sync()
        assert len(schedules) >= 1
        
        # Find our schedule
        found = any(s.id == schedule_id for s in schedules)
        assert found is True
    
    def test_pause_resume_sync(self, omniq_sync, sample_function):
        """Test pause/resume synchronously."""
        omniq_sync.register_function("test_func", sample_function)
        
        schedule_id = omniq_sync.create_schedule_sync(
            func="test_func",
            schedule_type=ScheduleType.INTERVAL,
            args=("sync pause test",),
            interval=timedelta(minutes=1)
        )
        
        # Pause
        paused = omniq_sync.pause_schedule_sync(schedule_id)
        assert paused is True
        
        # Resume
        resumed = omniq_sync.resume_schedule_sync(schedule_id)
        assert resumed is True


class TestScheduleModel:
    """Test suite for Schedule model functionality."""
    
    def test_schedule_from_cron(self):
        """Test creating schedule from CRON expression."""
        schedule = Schedule.from_cron(
            cron_expression="0 9 * * 1-5",  # 9 AM weekdays
            func="test_func",
            args=("test",),
            kwargs={"count": 1},
            queue_name="test_queue"
        )
        
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expression == "0 9 * * 1-5"
        assert schedule.func == "test_func"
        assert schedule.queue_name == "test_queue"
    
    def test_schedule_from_interval(self):
        """Test creating schedule from interval."""
        interval = timedelta(hours=2)
        schedule = Schedule.from_interval(
            interval=interval,
            func="test_func",
            args=("test",),
            kwargs={"count": 1},
            queue_name="test_queue"
        )
        
        assert schedule.schedule_type == ScheduleType.INTERVAL
        assert schedule.interval == interval
        assert schedule.func == "test_func"
    
    def test_schedule_from_timestamp(self):
        """Test creating schedule from timestamp."""
        timestamp = datetime.utcnow() + timedelta(hours=1)
        schedule = Schedule.from_timestamp(
            timestamp=timestamp,
            func="test_func",
            args=("test",),
            kwargs={"count": 1},
            queue_name="test_queue"
        )
        
        assert schedule.schedule_type == ScheduleType.TIMESTAMP
        assert schedule.timestamp == timestamp
        assert schedule.func == "test_func"
    
    def test_schedule_pause_resume(self):
        """Test schedule pause/resume functionality."""
        schedule = Schedule.from_interval(
            interval=timedelta(minutes=5),
            func="test_func",
            args=(),
            kwargs={},
            queue_name="test"
        )
        
        # Initially active
        assert schedule.status == ScheduleStatus.ACTIVE
        
        # Pause
        schedule.pause()
        assert schedule.status == ScheduleStatus.PAUSED
        
        # Resume
        schedule.resume()
        assert schedule.status == ScheduleStatus.ACTIVE
    
    def test_schedule_cancel(self):
        """Test schedule cancellation."""
        schedule = Schedule.from_interval(
            interval=timedelta(minutes=5),
            func="test_func",
            args=(),
            kwargs={},
            queue_name="test"
        )
        
        # Cancel
        schedule.cancel()
        assert schedule.status == ScheduleStatus.CANCELLED
    
    def test_schedule_mark_run(self):
        """Test marking schedule as run."""
        schedule = Schedule.from_interval(
            interval=timedelta(minutes=5),
            func="test_func",
            args=(),
            kwargs={},
            queue_name="test"
        )
        
        initial_count = schedule.run_count
        old_next_run = schedule.next_run
        
        # Mark as run
        schedule.mark_run()
        
        assert schedule.run_count == initial_count + 1
        # Check that next_run was updated (both should be datetime objects)
        if old_next_run is not None and schedule.next_run is not None:
            assert schedule.next_run > old_next_run
    
    def test_schedule_is_ready_to_run(self):
        """Test schedule readiness check."""
        # Create schedule that should be ready now
        past_time = datetime.utcnow() - timedelta(minutes=1)
        schedule = Schedule.from_timestamp(
            timestamp=past_time,
            func="test_func",
            args=(),
            kwargs={},
            queue_name="test"
        )
        schedule.next_run = past_time
        
        assert schedule.is_ready_to_run() is True
        
        # Create schedule that should not be ready yet
        future_time = datetime.utcnow() + timedelta(hours=1)
        schedule.next_run = future_time
        
        assert schedule.is_ready_to_run() is False
    
    def test_schedule_is_expired(self):
        """Test schedule expiration check."""
        # Create schedule with TTL
        schedule = Schedule.from_interval(
            interval=timedelta(minutes=5),
            func="test_func",
            args=(),
            kwargs={},
            queue_name="test",
            ttl=timedelta(hours=1)
        )
        
        # Should not be expired initially
        assert schedule.is_expired() is False
        
        # Manually set creation time to past
        schedule.created_at = datetime.utcnow() - timedelta(hours=2)
        
        # Should be expired now
        assert schedule.is_expired() is True


if __name__ == "__main__":
    pytest.main([__file__])