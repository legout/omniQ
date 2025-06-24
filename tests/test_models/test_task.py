import pytest
from omniq.models.task import Task
from omniq.serialization.manager import SerializationManager
import asyncio

def test_task_creation():
    """Test basic Task object creation with minimal parameters."""
    task = Task(
        func=lambda x: x * 2,
        args=(5,),
        kwargs={},
        id="test-task-1"
    )
    assert task.id == "test-task-1"
    assert callable(task.func)
    assert task.args == (5,)
    assert task.kwargs == {}

def test_task_serialization():
    """Test Task serialization and deserialization."""
    serializer = SerializationManager()
    task = Task(
        func=lambda x: x * 2,
        args=(5,),
        kwargs={},
        id="test-task-2"
    )
    serialized = serializer.serialize(task)
    deserialized = serializer.deserialize(serialized)
    assert deserialized.id == "test-task-2"
    assert deserialized.args == (5,)
    assert deserialized.kwargs == {}
    # Note: Function reference might not be identical after deserialization with dill
    assert callable(deserialized.func)

@pytest.mark.asyncio
async def test_task_execution_sync():
    """Test synchronous task execution."""
    task = Task(
        func=lambda x: x * 2,
        args=(5,),
        kwargs={},
        id="test-task-3"
    )
    result = task.func(*task.args, **task.kwargs)
    assert result == 10

@pytest.mark.asyncio
async def test_task_execution_async():
    """Test asynchronous task execution with an async function."""
    async def async_func(x):
        await asyncio.sleep(0.1)
        return x * 2
    
    task = Task(
        func=async_func,
        args=(5,),
        kwargs={},
        id="test-task-4"
    )
    result = await task.func(*task.args, **task.kwargs)
    assert result == 10
