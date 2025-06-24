import pytest
from datetime import datetime
from omniq.models.task_result import TaskResult

def test_task_result_creation_success():
    """Test TaskResult object creation for a successful task execution."""
    result = TaskResult(
        task_id="test-task-1",
        status="success",
        result=10,
        error=None,
        completed_at=datetime.now()
    )
    assert result.task_id == "test-task-1"
    assert result.status == "success"
    assert result.result == 10
    assert result.error is None
    assert result.completed_at is not None

def test_task_result_creation_failure():
    """Test TaskResult object creation for a failed task execution."""
    error_msg = "Task failed due to an error"
    result = TaskResult(
        task_id="test-task-2",
        status="failure",
        result=None,
        error=error_msg,
        completed_at=datetime.now()
    )
    assert result.task_id == "test-task-2"
    assert result.status == "failure"
    assert result.result is None
    assert result.error == error_msg
    assert result.completed_at is not None

def test_task_result_creation_timeout():
    """Test TaskResult object creation for a timed-out task."""
    result = TaskResult(
        task_id="test-task-3",
        status="timeout",
        result=None,
        error="Task timed out",
        completed_at=datetime.now()
    )
    assert result.task_id == "test-task-3"
    assert result.status == "timeout"
    assert result.result is None
    assert result.error == "Task timed out"
    assert result.completed_at is not None
