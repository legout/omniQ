"""
Tests for file storage backend.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from omniq.backend.file import FileBackend
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def file_backend(temp_dir):
    """Create a file backend for testing."""
    return FileBackend(base_dir=str(temp_dir))


@pytest.mark.asyncio
async def test_file_backend_initialization(file_backend):
    """Test file backend initialization."""
    assert file_backend.base_dir.exists() or file_backend.fs_protocol != "file"
    assert file_backend.fs_protocol == "file"


@pytest.mark.asyncio
async def test_task_queue_operations(file_backend):
    """Test basic task queue operations."""
    async with file_backend:
        task_queue = file_backend.get_task_queue()
        
        # Create a task
        task = Task(
            func="test_function",
            args=(1, 2),
            kwargs={"key": "value"},
            queue_name="test_queue"
        )
        
        # Enqueue the task
        task_id = await task_queue.enqueue(task)
        assert task_id == task.id
        
        # Get task by ID
        retrieved_task = await task_queue.get_task(task.id)
        assert retrieved_task is not None
        assert retrieved_task.id == task.id
        assert retrieved_task.func == "test_function"
        
        # List tasks
        tasks = await task_queue.list_tasks(queue_name="test_queue")
        assert len(tasks) == 1
        assert tasks[0].id == task.id
        
        # Dequeue the task
        dequeued_task = await task_queue.dequeue(["test_queue"])
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        
        # Queue should be empty now
        empty_task = await task_queue.dequeue(["test_queue"], timeout=0.1)
        assert empty_task is None


@pytest.mark.asyncio
async def test_result_storage_operations(file_backend):
    """Test result storage operations."""
    async with file_backend:
        result_storage = file_backend.get_result_storage()
        
        # Create a result
        result = TaskResult(
            task_id="test_task_123",
            status=ResultStatus.SUCCESS,
            result={"output": "test_output"},
            execution_time=0.5
        )
        
        # Store the result
        await result_storage.set(result)
        
        # Retrieve the result
        retrieved_result = await result_storage.get("test_task_123")
        assert retrieved_result is not None
        assert retrieved_result.task_id == "test_task_123"
        assert retrieved_result.status == ResultStatus.SUCCESS
        assert retrieved_result.result == {"output": "test_output"}
        
        # List results
        results = await result_storage.list_results()
        assert len(results) == 1
        assert results[0].task_id == "test_task_123"
        
        # Delete result
        deleted = await result_storage.delete("test_task_123")
        assert deleted is True
        
        # Result should be gone
        missing_result = await result_storage.get("test_task_123")
        assert missing_result is None


@pytest.mark.asyncio
async def test_event_storage_operations(file_backend):
    """Test event storage operations."""
    async with file_backend:
        event_storage = file_backend.get_event_storage()
        
        # Create an event
        event = TaskEvent(
            task_id="test_task_456",
            event_type=EventType.COMPLETED,
            message="Task completed successfully",
            details={"duration": 1.5}
        )
        
        # Store the event
        await event_storage.log_event(event)
        
        # Retrieve events
        events = await event_storage.get_events(task_id="test_task_456")
        assert len(events) == 1
        assert events[0].task_id == "test_task_456"
        assert events[0].event_type == EventType.COMPLETED
        
        # Get all events
        all_events = await event_storage.get_events()
        assert len(all_events) == 1


@pytest.mark.asyncio
async def test_schedule_storage_operations(file_backend):
    """Test schedule storage operations."""
    async with file_backend:
        schedule_storage = file_backend.get_schedule_storage()
        
        # Create a schedule
        schedule = Schedule(
            schedule_type=ScheduleType.CRON,
            func="scheduled_task",
            cron_expression="0 */6 * * *",  # Every 6 hours
            queue_name="scheduled"
        )
        
        # Store the schedule
        await schedule_storage.save_schedule(schedule)
        
        # Retrieve the schedule
        retrieved_schedule = await schedule_storage.get_schedule(schedule.id)
        assert retrieved_schedule is not None
        assert retrieved_schedule.id == schedule.id
        assert retrieved_schedule.func == "scheduled_task"
        
        # List schedules
        schedules = await schedule_storage.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].id == schedule.id
        
        # Update schedule
        schedule.queue_name = "updated_queue"
        await schedule_storage.update_schedule(schedule)
        
        updated_schedule = await schedule_storage.get_schedule(schedule.id)
        assert updated_schedule.queue_name == "updated_queue"
        
        # Delete schedule
        deleted = await schedule_storage.delete_schedule(schedule.id)
        assert deleted is True
        
        # Schedule should be gone
        missing_schedule = await schedule_storage.get_schedule(schedule.id)
        assert missing_schedule is None


@pytest.mark.asyncio
async def test_backend_context_manager(file_backend):
    """Test backend context manager functionality."""
    async with file_backend as backend:
        assert backend is file_backend
        
        # Should be able to use storage components
        task_queue = backend.get_task_queue()
        task = Task(func="context_test", args=())
        await task_queue.enqueue(task)
        
        retrieved_task = await task_queue.get_task(task.id)
        assert retrieved_task is not None


@pytest.mark.asyncio
async def test_sync_storage_access(file_backend):
    """Test synchronous storage component access."""
    with file_backend:
        # Get sync versions
        sync_task_queue = file_backend.get_task_queue(async_mode=False)
        sync_result_storage = file_backend.get_result_storage(async_mode=False)
        sync_event_storage = file_backend.get_event_storage(async_mode=False)
        sync_schedule_storage = file_backend.get_schedule_storage(async_mode=False)
        
        # Verify they are different instances
        async_task_queue = file_backend.get_task_queue(async_mode=True)
        assert sync_task_queue is not async_task_queue


def test_backend_from_url():
    """Test creating backend from URL."""
    backend = FileBackend.from_url("file:///tmp/test_omniq")
    assert backend.base_dir == Path("/tmp/test_omniq")
    assert backend.fs_protocol == "file"


def test_backend_from_config():
    """Test creating backend from config."""
    from omniq.models.config import FileConfig
    
    config = FileConfig(
        base_dir="/tmp/config_test",
        fsspec_uri="file:///tmp/config_test"
    )
    
    backend = FileBackend.from_config(config)
    assert str(backend.base_dir) == "/tmp/config_test"


@pytest.mark.asyncio
async def test_cleanup_operations(file_backend):
    """Test cleanup operations."""
    async with file_backend:
        task_queue = file_backend.get_task_queue()
        result_storage = file_backend.get_result_storage()
        
        # Create expired task
        expired_task = Task(
            func="expired_task",
            args=(),
            ttl=timedelta(seconds=-1)  # Already expired
        )
        await task_queue.enqueue(expired_task)
        
        # Create expired result
        expired_result = TaskResult(
            task_id="expired_result_task",
            status=ResultStatus.SUCCESS,
            result="expired",
            ttl=timedelta(seconds=-1)  # Already expired
        )
        await result_storage.set(expired_result)
        
        # Run cleanup
        stats = await file_backend.cleanup_expired()
        
        # Should have cleaned up expired items
        assert "expired_tasks" in stats
        assert "expired_results" in stats


if __name__ == "__main__":
    pytest.main([__file__])