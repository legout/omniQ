import pytest
from datetime import datetime
from omniq.models.task_event import TaskEvent
from omniq.events.types import EventType

def test_task_event_creation_enqueued():
    """Test TaskEvent object creation for an enqueued event."""
    event = TaskEvent(
        task_id="test-task-1",
        event_type=EventType.ENQUEUED.value,
        timestamp=datetime.now().timestamp(),
        metadata={"queue": "default"}
    )
    assert event.task_id == "test-task-1"
    assert event.event_type == EventType.ENQUEUED.value
    assert event.timestamp is not None
    assert event.metadata == {"queue": "default"}

def test_task_event_creation_started():
    """Test TaskEvent object creation for a started event."""
    event = TaskEvent(
        task_id="test-task-2",
        event_type=EventType.EXECUTING.value,
        timestamp=datetime.now().timestamp(),
        metadata={"worker_id": "worker-123"}
    )
    assert event.task_id == "test-task-2"
    assert event.event_type == EventType.EXECUTING.value
    assert event.timestamp is not None
    assert event.metadata == {"worker_id": "worker-123"}

def test_task_event_creation_completed():
    """Test TaskEvent object creation for a completed event."""
    event = TaskEvent(
        task_id="test-task-3",
        event_type=EventType.COMPLETE.value,
        timestamp=datetime.now().timestamp(),
        metadata={"result": 42}
    )
    assert event.task_id == "test-task-3"
    assert event.event_type == EventType.COMPLETE.value
    assert event.timestamp is not None
    assert event.metadata == {"result": 42}

def test_task_event_creation_failed():
    """Test TaskEvent object creation for a failed event."""
    event = TaskEvent(
        task_id="test-task-4",
        event_type=EventType.ERROR.value,
        timestamp=datetime.now().timestamp(),
        metadata={"error": "Task execution failed"}
    )
    assert event.task_id == "test-task-4"
    assert event.event_type == EventType.ERROR.value
    assert event.timestamp is not None
    assert event.metadata == {"error": "Task execution failed"}
