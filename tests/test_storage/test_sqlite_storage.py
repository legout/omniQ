import pytest
import os
from omniq.storage.sqlite_storage import SQLiteStorage
from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from datetime import datetime
import tempfile

@pytest.fixture
def temp_db_file():
    """Create a temporary SQLite database file for storage tests."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
        yield temp_file.name
    os.unlink(temp_file.name)

def test_sqlite_storage_task_store_and_retrieve(temp_db_file):
    """Test storing and retrieving a task using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    task = Task(func=lambda x: x * 2, id="test-task-1", args=(5,), kwargs={})
    
    # Store the task
    storage.store_task(task)
    
    # Retrieve the task
    retrieved_task = storage.get_task("test-task-1")
    assert retrieved_task is not None
    assert retrieved_task.id == "test-task-1"
    assert retrieved_task.args == (5,)

def test_sqlite_storage_task_delete(temp_db_file):
    """Test deleting a task using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    task = Task(func=lambda x: x * 2, id="test-task-2", args=(5,), kwargs={})
    
    # Store and delete the task
    storage.store_task(task)
    assert storage.delete_task("test-task-2") is True
    assert storage.get_task("test-task-2") is None

def test_sqlite_storage_result_store_and_retrieve(temp_db_file):
    """Test storing and retrieving a task result using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    result = TaskResult(task_id="test-task-3", status="success", result=10, error=None, completed_at=datetime.now())
    
    # Store the result
    storage.store_result(result)
    
    # Retrieve the result
    retrieved_result = storage.get_result("test-task-3")
    assert retrieved_result is not None
    assert retrieved_result.task_id == "test-task-3"
    assert retrieved_result.status == "success"
    assert retrieved_result.result == 10

def test_sqlite_storage_result_delete(temp_db_file):
    """Test deleting a task result using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    result = TaskResult(task_id="test-task-4", status="success", result=10, error=None, completed_at=datetime.now())
    
    # Store and delete the result
    storage.store_result(result)
    assert storage.delete_result("test-task-4") is True
    assert storage.get_result("test-task-4") is None

@pytest.mark.asyncio
async def test_sqlite_storage_task_store_and_retrieve_async(temp_db_file):
    """Test asynchronously storing and retrieving a task using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    task = Task(func=lambda x: x * 2, id="test-task-5", args=(5,), kwargs={})
    
    # Store the task asynchronously
    await storage.store_task_async(task)
    
    # Retrieve the task asynchronously
    retrieved_task = await storage.get_task_async("test-task-5")
    assert retrieved_task is not None
    assert retrieved_task.id == "test-task-5"
    assert retrieved_task.args == (5,)

@pytest.mark.asyncio
async def test_sqlite_storage_result_store_and_retrieve_async(temp_db_file):
    """Test asynchronously storing and retrieving a task result using SQLiteStorage."""
    storage = SQLiteStorage(db_path=temp_db_file)
    result = TaskResult(task_id="test-task-6", status="success", result=10, error=None, completed_at=datetime.now())
    
    # Store the result asynchronously
    await storage.store_result_async(result)
    
    # Retrieve the result asynchronously
    retrieved_result = await storage.get_result_async("test-task-6")
    assert retrieved_result is not None
    assert retrieved_result.task_id == "test-task-6"
    assert retrieved_result.status == "success"
    assert retrieved_result.result == 10
