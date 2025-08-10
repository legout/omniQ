# Task 3: Unit and Integration Tests for Core and SQLite Backend

## Overview

This task involves implementing a comprehensive test suite for the OmniQ core components and SQLite backend. The tests will cover unit tests for individual components and integration tests for end-to-end workflows.

## Objectives

1. Implement unit tests for all core models and base classes
2. Implement unit tests for SQLite backend components
3. Implement integration tests for complete workflows
4. Ensure proper test coverage and quality
5. Set up test fixtures and utilities

## Detailed Implementation Plan

### 3.1 Test Structure and Organization

**Purpose**: Organize tests in a logical structure that mirrors the codebase.

**Implementation Requirements**:
- Create a test directory structure that mirrors the source code
- Separate unit tests from integration tests
- Include fixtures and utilities for common test scenarios

**Directory Structure**:
```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration and fixtures
├── fixtures/                      # Test fixtures and utilities
│   ├── __init__.py
│   ├── factories.py               # Factory functions for test objects
│   ├── helpers.py                 # Test helper functions
│   └── data/                      # Test data files
│       ├── sample_tasks.json
│       ├── sample_results.json
│       └── sample_events.json
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── models/                    # Tests for models
│   │   ├── __init__.py
│   │   ├── test_task.py
│   │   ├── test_schedule.py
│   │   ├── test_result.py
│   │   ├── test_event.py
│   │   └── test_config.py
│   ├── base/                      # Tests for base classes
│   │   ├── __init__.py
│   │   ├── test_queue.py
│   │   ├── test_result_storage.py
│   │   ├── test_event_storage.py
│   │   └── test_worker.py
│   ├── serialization/             # Tests for serialization
│   │   ├── __init__.py
│   │   └── test_manager.py
│   ├── config/                    # Tests for configuration
│   │   ├── __init__.py
│   │   └── test_loader.py
│   └── core/                      # Tests for core components
│       ├── __init__.py
│       └── test_omniq.py
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_sqlite_backend.py     # Tests for SQLite backend
│   ├── test_workflows.py          # Tests for complete workflows
│   └── test_configuration.py      # Tests for configuration-based workflows
└── performance/                   # Performance tests (optional)
    ├── __init__.py
    └── test_benchmarks.py
```

### 3.2 Test Configuration (`tests/conftest.py`)

**Purpose**: Configure pytest and define common fixtures.

**Implementation Requirements**:
- Set up pytest configuration
- Define fixtures for common test objects
- Configure test database and temporary directories

**Code Structure**:
```python
# tests/conftest.py
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import json

# Configure pytest
pytest_plugins = []

# Test configuration
@pytest.fixture(scope="session")
def test_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="session")
def test_db_path(test_dir):
    """Get the path to a test database."""
    return test_dir / "test.db"

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": "test-task-123",
        "func": "tests.fixtures.sample_functions.simple_task",
        "func_args": {"x": 5, "y": 10},
        "func_kwargs": {},
        "queue_name": "test",
        "name": "Test Task",
        "description": "A test task for unit testing",
        "tags": ["test", "unit"],
        "priority": 1,
        "run_at": None,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "ttl": timedelta(hours=1),
        "expires_at": None,
        "depends_on": [],
        "callback": None,
        "callback_args": {},
        "retry_count": 0,
        "max_retries": 3,
        "retry_delay": timedelta(seconds=5),
        "result_ttl": timedelta(minutes=30),
        "store_result": True
    }

@pytest.fixture
def sample_schedule_data():
    """Sample schedule data for testing."""
    return {
        "id": "test-schedule-123",
        "task_id": "test-task-123",
        "schedule_type": "interval",
        "cron_expression": None,
        "interval": timedelta(minutes=5),
        "run_at": None,
        "max_runs": 10,
        "status": "active",
        "created_at": datetime.utcnow(),
        "last_run_at": None,
        "next_run_at": datetime.utcnow() + timedelta(minutes=5),
        "run_count": 0,
        "paused_at": None,
        "resumed_at": None,
        "name": "Test Schedule",
        "description": "A test schedule for unit testing",
        "tags": ["test", "schedule"]
    }

@pytest.fixture
def sample_result_data():
    """Sample result data for testing."""
    return {
        "task_id": "test-task-123",
        "status": "completed",
        "result": 15,
        "error": None,
        "error_traceback": None,
        "created_at": datetime.utcnow(),
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "ttl": timedelta(minutes=30),
        "expires_at": None,
        "execution_time": 0.1,
        "worker_id": "test-worker",
        "retry_count": 0
    }

@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "id": "test-event-123",
        "task_id": "test-task-123",
        "event_type": "enqueued",
        "timestamp": datetime.utcnow(),
        "queue_name": "test",
        "worker_id": None,
        "schedule_id": None,
        "message": "Task enqueued",
        "data": {"func_name": "simple_task"},
        "execution_time": None,
        "retry_count": None,
        "error": None,
        "source": "test",
        "level": "info"
    }

@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "project_name": "test_project",
        "task_queue": {
            "type": "sqlite",
            "config": {
                "base_dir": "./test_data",
                "queues": ["high", "medium", "low"]
            }
        },
        "result_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./test_data"
            }
        },
        "event_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./test_data"
            }
        },
        "worker": {
            "type": "async",
            "config": {
                "max_workers": 2
            }
        }
    }

# Async test fixtures
@pytest.fixture
async def sqlite_backend(test_dir):
    """Create a SQLite backend for testing."""
    from src.omniq.backends.sqlite import SQLiteBackend
    
    backend = SQLiteBackend(
        project_name="test_project",
        base_dir=str(test_dir)
    )
    
    await backend.initialize_async()
    yield backend
    await backend.close_async()

@pytest.fixture
async def sqlite_task_queue(sqlite_backend):
    """Create a SQLite task queue for testing."""
    from src.omniq.backends.sqlite import SQLiteBackend
    
    return sqlite_backend.get_task_queue(["test"])

@pytest.fixture
async def sqlite_result_storage(sqlite_backend):
    """Create a SQLite result storage for testing."""
    from src.omniq.backends.sqlite import SQLiteBackend
    
    return sqlite_backend.get_result_storage()

@pytest.fixture
async def sqlite_event_storage(sqlite_backend):
    """Create a SQLite event storage for testing."""
    from src.omniq.backends.sqlite import SQLiteBackend
    
    return sqlite_backend.get_event_storage()

@pytest.fixture
async def sqlite_worker(sqlite_task_queue, sqlite_result_storage, sqlite_event_storage):
    """Create a SQLite worker for testing."""
    from src.omniq.workers.sqlite_worker import SQLiteWorker
    
    worker = SQLiteWorker(
        task_queue=sqlite_task_queue,
        result_storage=sqlite_result_storage,
        event_storage=sqlite_event_storage,
        max_workers=1
    )
    
    await worker.start_async()
    yield worker
    await worker.stop_async()

# Sync test fixtures
@pytest.fixture
def sqlite_backend_sync(test_dir):
    """Create a SQLite backend for sync testing."""
    from src.omniq.backends.sqlite import SQLiteBackend
    
    backend = SQLiteBackend(
        project_name="test_project",
        base_dir=str(test_dir)
    )
    
    backend.initialize()
    yield backend
    backend.close()

@pytest.fixture
def sqlite_task_queue_sync(sqlite_backend_sync):
    """Create a SQLite task queue for sync testing."""
    return sqlite_backend_sync.get_task_queue(["test"])

@pytest.fixture
def sqlite_result_storage_sync(sqlite_backend_sync):
    """Create a SQLite result storage for sync testing."""
    return sqlite_backend_sync.get_result_storage()

@pytest.fixture
def sqlite_event_storage_sync(sqlite_backend_sync):
    """Create a SQLite event storage for sync testing."""
    return sqlite_backend_sync.get_event_storage()

@pytest.fixture
def sqlite_worker_sync(sqlite_task_queue_sync, sqlite_result_storage_sync, sqlite_event_storage_sync):
    """Create a SQLite worker for sync testing."""
    from src.omniq.workers.sqlite_worker import SQLiteWorker
    
    worker = SQLiteWorker(
        task_queue=sqlite_task_queue_sync,
        result_storage=sqlite_result_storage_sync,
        event_storage=sqlite_event_storage_sync,
        max_workers=1
    )
    
    worker.start()
    yield worker
    worker.stop()
```

### 3.3 Test Fixtures and Utilities (`tests/fixtures/factories.py`)

**Purpose**: Provide factory functions for creating test objects.

**Implementation Requirements**:
- Create factory functions for all model types
- Support both default and custom values
- Include helper functions for common test scenarios

**Code Structure**:
```python
# tests/fixtures/factories.py
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from src.omniq.models.task import Task, TaskStatus
from src.omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus
from src.omniq.models.result import TaskResult, ResultStatus
from src.omniq.models.event import TaskEvent, EventType
from src.omniq.models.config import (
    OmniQConfig, TaskQueueConfig, ResultStorageConfig, 
    EventStorageConfig, WorkerConfig
)

def create_task(
    task_id: Optional[str] = None,
    func: str = "tests.fixtures.sample_functions.simple_task",
    func_args: Optional[Dict[str, Any]] = None,
    func_kwargs: Optional[Dict[str, Any]] = None,
    queue_name: str = "test",
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: int = 0,
    run_at: Optional[datetime] = None,
    ttl: Optional[timedelta] = None,
    result_ttl: Optional[timedelta] = None,
    **kwargs
) -> Task:
    """Create a Task object for testing."""
    return Task(
        id=task_id or str(uuid.uuid4()),
        func=func,
        func_args=func_args or {"x": 5, "y": 10},
        func_kwargs=func_kwargs or {},
        queue_name=queue_name,
        name=name or "Test Task",
        description=description or "A test task",
        tags=tags or ["test"],
        priority=priority,
        run_at=run_at,
        created_at=datetime.utcnow(),
        started_at=None,
        completed_at=None,
        ttl=ttl or timedelta(hours=1),
        expires_at=None,
        depends_on=[],
        callback=None,
        callback_args={},
        retry_count=0,
        max_retries=3,
        retry_delay=timedelta(seconds=5),
        result_ttl=result_ttl or timedelta(minutes=30),
        store_result=True,
        **kwargs
    )

def create_schedule(
    schedule_id: Optional[str] = None,
    task_id: Optional[str] = None,
    schedule_type: ScheduleType = ScheduleType.INTERVAL,
    cron_expression: Optional[str] = None,
    interval: Optional[timedelta] = None,
    run_at: Optional[datetime] = None,
    max_runs: Optional[int] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> Schedule:
    """Create a Schedule object for testing."""
    return Schedule(
        id=schedule_id or str(uuid.uuid4()),
        task_id=task_id or str(uuid.uuid4()),
        schedule_type=schedule_type,
        cron_expression=cron_expression,
        interval=interval or timedelta(minutes=5),
        run_at=run_at,
        max_runs=max_runs,
        status=ScheduleStatus.ACTIVE,
        created_at=datetime.utcnow(),
        last_run_at=None,
        next_run_at=datetime.utcnow() + (interval or timedelta(minutes=5)),
        run_count=0,
        paused_at=None,
        resumed_at=None,
        name=name or "Test Schedule",
        description=description or "A test schedule",
        tags=tags or ["test", "schedule"],
        **kwargs
    )

def create_result(
    task_id: Optional[str] = None,
    status: ResultStatus = ResultStatus.COMPLETED,
    result: Any = 15,
    error: Optional[str] = None,
    error_traceback: Optional[str] = None,
    execution_time: float = 0.1,
    worker_id: str = "test-worker",
    retry_count: int = 0,
    **kwargs
) -> TaskResult:
    """Create a TaskResult object for testing."""
    now = datetime.utcnow()
    return TaskResult(
        task_id=task_id or str(uuid.uuid4()),
        status=status,
        result=result,
        error=error,
        error_traceback=error_traceback,
        created_at=now,
        started_at=now,
        completed_at=now,
        ttl=timedelta(minutes=30),
        expires_at=None,
        execution_time=execution_time,
        worker_id=worker_id,
        retry_count=retry_count,
        **kwargs
    )

def create_event(
    task_id: Optional[str] = None,
    event_type: EventType = EventType.ENQUEUED,
    timestamp: Optional[datetime] = None,
    queue_name: str = "test",
    worker_id: Optional[str] = None,
    schedule_id: Optional[str] = None,
    message: str = "Test event",
    data: Optional[Dict[str, Any]] = None,
    execution_time: Optional[float] = None,
    retry_count: Optional[int] = None,
    error: Optional[str] = None,
    source: str = "test",
    level: str = "info",
    **kwargs
) -> TaskEvent:
    """Create a TaskEvent object for testing."""
    return TaskEvent(
        id=str(uuid.uuid4()),
        task_id=task_id or str(uuid.uuid4()),
        event_type=event_type,
        timestamp=timestamp or datetime.utcnow(),
        queue_name=queue_name,
        worker_id=worker_id,
        schedule_id=schedule_id,
        message=message,
        data=data or {},
        execution_time=execution_time,
        retry_count=retry_count,
        error=error,
        source=source,
        level=level,
        **kwargs
    )

def create_config(
    project_name: str = "test_project",
    task_queue_type: str = "sqlite",
    result_store_type: str = "sqlite",
    event_store_type: str = "sqlite",
    worker_type: str = "async",
    **kwargs
) -> OmniQConfig:
    """Create an OmniQConfig object for testing."""
    return OmniQConfig(
        project_name=project_name,
        task_queue=TaskQueueConfig(
            type=task_queue_type,
            config={
                "base_dir": "./test_data",
                "queues": ["high", "medium", "low"],
                **kwargs.get("task_queue_config", {})
            }
        ),
        result_store=ResultStorageConfig(
            type=result_store_type,
            config={
                "base_dir": "./test_data",
                **kwargs.get("result_store_config", {})
            }
        ),
        event_store=EventStorageConfig(
            type=event_store_type,
            config={
                "base_dir": "./test_data",
                **kwargs.get("event_store_config", {})
            }
        ),
        worker=WorkerConfig(
            type=worker_type,
            config={
                "max_workers": 2,
                **kwargs.get("worker_config", {})
            }
        )
    )

# Helper functions
def create_task_sequence(count: int, queue_name: str = "test") -> List[Task]:
    """Create a sequence of tasks for testing."""
    return [create_task(queue_name=queue_name, name=f"Task {i}") for i in range(count)]

def create_schedule_sequence(count: int, interval: timedelta = timedelta(minutes=5)) -> List[Schedule]:
    """Create a sequence of schedules for testing."""
    return [create_schedule(interval=interval * (i + 1), name=f"Schedule {i}") for i in range(count)]

def create_event_sequence(task_id: str, event_types: List[EventType]) -> List[TaskEvent]:
    """Create a sequence of events for testing."""
    return [create_event(task_id=task_id, event_type=event_type) for event_type in event_types]
```

### 3.4 Sample Functions for Testing (`tests/fixtures/sample_functions.py`)

**Purpose**: Provide sample functions to use in task tests.

**Implementation Requirements**:
- Create simple functions with different signatures
- Include both sync and async functions
- Add functions that raise exceptions for error testing

**Code Structure**:
```python
# tests/fixtures/sample_functions.py
import asyncio
import time
from typing import Dict, Any

def simple_task(x: int, y: int) -> int:
    """Simple task that adds two numbers."""
    return x + y

def multiply_task(x: int, y: int) -> int:
    """Task that multiplies two numbers."""
    return x * y

def complex_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Task that processes complex data."""
    result = {}
    for key, value in data.items():
        if isinstance(value, (int, float)):
            result[f"{key}_doubled"] = value * 2
        elif isinstance(value, str):
            result[f"{key}_upper"] = value.upper()
        else:
            result[f"{key}_processed"] = str(value)
    return result

def failing_task():
    """Task that always fails."""
    raise ValueError("This task always fails")

def slow_task(duration: float = 0.1) -> str:
    """Task that takes some time to complete."""
    time.sleep(duration)
    return f"Completed after {duration} seconds"

def task_with_kwargs(a: int, b: int, operation: str = "add") -> int:
    """Task with keyword arguments."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a // b
    else:
        raise ValueError(f"Unknown operation: {operation}")

async def async_simple_task(x: int, y: int) -> int:
    """Simple async task that adds two numbers."""
    await asyncio.sleep(0.01)  # Simulate async work
    return x + y

async def async_multiply_task(x: int, y: int) -> int:
    """Async task that multiplies two numbers."""
    await asyncio.sleep(0.01)  # Simulate async work
    return x * y

async def async_failing_task():
    """Async task that always fails."""
    await asyncio.sleep(0.01)  # Simulate async work
    raise ValueError("This async task always fails")

async def async_slow_task(duration: float = 0.1) -> str:
    """Async task that takes some time to complete."""
    await asyncio.sleep(duration)
    return f"Completed after {duration} seconds"

async def async_task_with_kwargs(a: int, b: int, operation: str = "add") -> int:
    """Async task with keyword arguments."""
    await asyncio.sleep(0.01)  # Simulate async work
    
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a // b
    else:
        raise ValueError(f"Unknown operation: {operation}")

def task_with_callback(x: int, y: int, callback=None, callback_args=None) -> int:
    """Task that calls a callback."""
    result = x + y
    
    if callback:
        if callback_args is None:
            callback_args = {}
        callback(result=result, **callback_args)
    
    return result

def callback_function(result: int, **kwargs):
    """Sample callback function."""
    print(f"Callback called with result: {result}, kwargs: {kwargs}")
```

### 3.5 Unit Tests for Models (`tests/unit/models/test_task.py`)

**Purpose**: Test the Task model and its functionality.

**Implementation Requirements**:
- Test Task creation and validation
- Test serialization and deserialization
- Test business logic methods
- Test edge cases and error conditions

**Code Structure**:
```python
# tests/unit/models/test_task.py
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.omniq.models.task import Task, TaskStatus
from tests.fixtures.factories import create_task

class TestTask:
    """Test cases for the Task model."""
    
    def test_task_creation(self):
        """Test creating a task with default values."""
        task = create_task()
        
        assert task.id is not None
        assert task.func == "tests.fixtures.sample_functions.simple_task"
        assert task.func_args == {"x": 5, "y": 10}
        assert task.func_kwargs == {}
        assert task.queue_name == "test"
        assert task.name == "Test Task"
        assert task.description == "A test task"
        assert task.tags == ["test"]
        assert task.priority == 0
        assert task.run_at is None
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.ttl == timedelta(hours=1)
        assert task.expires_at is None
        assert task.depends_on == []
        assert task.callback is None
        assert task.callback_args == {}
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.retry_delay == timedelta(seconds=5)
        assert task.result_ttl == timedelta(minutes=30)
        assert task.store_result is True
    
    def test_task_creation_with_custom_values(self):
        """Test creating a task with custom values."""
        custom_id = str(uuid4())
        run_at = datetime.utcnow() + timedelta(hours=1)
        custom_ttl = timedelta(hours=2)
        custom_result_ttl = timedelta(hours=1)
        
        task = create_task(
            task_id=custom_id,
            func="custom.func",
            func_args={"a": 1},
            func_kwargs={"b": 2},
            queue_name="custom",
            name="Custom Task",
            description="Custom description",
            tags=["custom", "test"],
            priority=5,
            run_at=run_at,
            ttl=custom_ttl,
            result_ttl=custom_result_ttl,
            max_retries=5,
            retry_delay=timedelta(seconds=10),
            store_result=False
        )
        
        assert task.id == custom_id
        assert task.func == "custom.func"
        assert task.func_args == {"a": 1}
        assert task.func_kwargs == {"b": 2}
        assert task.queue_name == "custom"
        assert task.name == "Custom Task"
        assert task.description == "Custom description"
        assert task.tags == ["custom", "test"]
        assert task.priority == 5
        assert task.run_at == run_at
        assert task.ttl == custom_ttl
        assert task.result_ttl == custom_result_ttl
        assert task.max_retries == 5
        assert task.retry_delay == timedelta(seconds=10)
        assert task.store_result is False
    
    def test_task_expires_at_calculation(self):
        """Test that expires_at is calculated correctly."""
        task = create_task(ttl=timedelta(hours=1))
        
        # expires_at should be created_at + ttl
        expected_expires_at = task.created_at + task.ttl
        assert task.expires_at == expected_expires_at
    
    def test_task_is_ready(self):
        """Test the is_ready property."""
        # Task with no run_at should be ready
        task = create_task()
        assert task.is_ready is True
        
        # Task with future run_at should not be ready
        future_time = datetime.utcnow() + timedelta(hours=1)
        task = create_task(run_at=future_time)
        assert task.is_ready is False
        
        # Task with past run_at should be ready
        past_time = datetime.utcnow() - timedelta(hours=1)
        task = create_task(run_at=past_time)
        assert task.is_ready is True
    
    def test_task_is_expired(self):
        """Test the is_expired property."""
        # Task with no expires_at should not be expired
        task = create_task()
        assert task.is_expired is False
        
        # Task with future expires_at should not be expired
        future_time = datetime.utcnow() + timedelta(hours=1)
        task = create_task()
        task.expires_at = future_time
        assert task.is_expired is False
        
        # Task with past expires_at should be expired
        past_time = datetime.utcnow() - timedelta(hours=1)
        task = create_task()
        task.expires_at = past_time
        assert task.is_expired is True
    
    def test_task_can_retry(self):
        """Test the can_retry property."""
        # Task with no retries should be able to retry
        task = create_task()
        assert task.can_retry is True
        
        # Task with max_retries=0 should not be able to retry
        task = create_task(max_retries=0)
        assert task.can_retry is False
        
        # Task with retry_count < max_retries should be able to retry
        task = create_task(max_retries=3, retry_count=2)
        assert task.can_retry is True
        
        # Task with retry_count >= max_retries should not be able to retry
        task = create_task(max_retries=3, retry_count=3)
        assert task.can_retry is False
    
    def test_task_mark_started(self):
        """Test marking a task as started."""
        task = create_task()
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        
        task.mark_started()
        
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        assert isinstance(task.started_at, datetime)
    
    def test_task_mark_completed(self):
        """Test marking a task as completed."""
        task = create_task()
        task.mark_started()  # First mark as started
        
        assert task.status == TaskStatus.RUNNING
        assert task.completed_at is None
        
        task.mark_completed()
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert isinstance(task.completed_at, datetime)
    
    def test_task_mark_failed(self):
        """Test marking a task as failed."""
        task = create_task()
        task.mark_started()  # First mark as started
        
        assert task.status == TaskStatus.RUNNING
        assert task.completed_at is None
        
        task.mark_failed()
        
        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None
        assert isinstance(task.completed_at, datetime)
    
    def test_task_increment_retry(self):
        """Test incrementing the retry count."""
        task = create_task(max_retries=3)
        assert task.retry_count == 0
        
        task.increment_retry()
        
        assert task.retry_count == 1
        
        task.increment_retry()
        
        assert task.retry_count == 2
    
    def test_task_to_dict(self):
        """Test converting a task to a dictionary."""
        task = create_task()
        task_dict = task.to_dict()
        
        assert isinstance(task_dict, dict)
        assert task_dict["id"] == task.id
        assert task_dict["func"] == task.func
        assert task_dict["func_args"] == task.func_args
        assert task_dict["status"] == task.status.value
        assert task_dict["created_at"] == task.created_at.isoformat()
    
    def test_task_from_dict(self):
        """Test creating a task from a dictionary."""
        task = create_task()
        task_dict = task.to_dict()
        
        new_task = Task.from_dict(task_dict)
        
        assert new_task.id == task.id
        assert new_task.func == task.func
        assert new_task.func_args == task.func_args
        assert new_task.status == task.status
        assert new_task.created_at == task.created_at
    
    def test_task_serialization(self):
        """Test task serialization and deserialization."""
        task = create_task()
        
        # Serialize to bytes
        task_bytes = task.serialize()
        assert isinstance(task_bytes, bytes)
        
        # Deserialize from bytes
        deserialized_task = Task.deserialize(task_bytes)
        
        assert deserialized_task.id == task.id
        assert deserialized_task.func == task.func
        assert deserialized_task.func_args == task.func_args
        assert deserialized_task.status == task.status
        assert deserialized_task.created_at == task.created_at
    
    def test_task_equality(self):
        """Test task equality comparison."""
        task1 = create_task(task_id="same-id")
        task2 = create_task(task_id="same-id")
        task3 = create_task(task_id="different-id")
        
        assert task1 == task2
        assert task1 != task3
        assert hash(task1) == hash(task2)
        assert hash(task1) != hash(task3)
    
    def test_task_repr(self):
        """Test task string representation."""
        task = create_task(name="Test Task")
        task_repr = repr(task)
        
        assert "Task" in task_repr
        assert task.id in task_repr
        assert "Test Task" in task_repr
```

### 3.6 Unit Tests for SQLite Backend (`tests/unit/backends/test_sqlite.py`)

**Purpose**: Test the SQLite backend implementation.

**Implementation Requirements**:
- Test backend initialization and connection
- Test database schema creation
- Test connection management
- Test error handling

**Code Structure**:
```python
# tests/unit/backends/test_sqlite.py
import pytest
import asyncio
from pathlib import Path

from src.omniq.backends.sqlite import SQLiteBackend

class TestSQLiteBackend:
    """Test cases for the SQLite backend."""
    
    @pytest.mark.asyncio
    async def test_backend_initialization(self, test_dir):
        """Test backend initialization."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        # Check that the backend is not initialized yet
        assert backend._connection is None
        
        # Initialize the backend
        await backend.initialize_async()
        
        # Check that the backend is now initialized
        assert backend._connection is not None
        
        # Check that the database file was created
        db_path = test_dir / "test_project.db"
        assert db_path.exists()
        
        # Close the backend
        await backend.close_async()
        
        # Check that the connection is closed
        assert backend._connection is None
    
    @pytest.mark.asyncio
    async def test_backend_creates_tables(self, test_dir):
        """Test that the backend creates all necessary tables."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Check that all tables were created
        async with backend.get_connection_async() as conn:
            # Get list of tables
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            # Check that all expected tables are present
            expected_tables = ["tasks", "schedules", "results", "events"]
            for table in expected_tables:
                assert table in tables
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_creates_indexes(self, test_dir):
        """Test that the backend creates all necessary indexes."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Check that all indexes were created
        async with backend.get_connection_async() as conn:
            # Get list of indexes
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = [row[0] for row in await cursor.fetchall()]
            
            # Check that all expected indexes are present
            expected_indexes = [
                "idx_tasks_queue_status",
                "idx_tasks_run_at",
                "idx_tasks_expires_at",
                "idx_schedules_next_run",
                "idx_schedules_status",
                "idx_results_expires_at",
                "idx_events_task_id",
                "idx_events_timestamp"
            ]
            for index in expected_indexes:
                assert index in indexes
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_connection_locking(self, test_dir):
        """Test that the backend properly locks connections."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Get multiple connections concurrently
        async def get_connection():
            async with backend.get_connection_async() as conn:
                # Simulate some work
                await asyncio.sleep(0.01)
                return conn
        
        # Run multiple connection requests concurrently
        connections = await asyncio.gather(
            get_connection(),
            get_connection(),
            get_connection()
        )
        
        # All connections should be the same object
        assert all(conn is connections[0] for conn in connections)
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_wal_mode(self, test_dir):
        """Test that the backend enables WAL mode."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Check that WAL mode is enabled
        async with backend.get_connection_async() as conn:
            cursor = await conn.execute("PRAGMA journal_mode")
            journal_mode = (await cursor.fetchone())[0]
            assert journal_mode == "wal"
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_get_task_queue(self, test_dir):
        """Test getting a task queue from the backend."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Get a task queue
        task_queue = backend.get_task_queue(["test"])
        
        # Check that the task queue was created correctly
        assert task_queue is not None
        assert task_queue.project_name == "test_project"
        assert task_queue.queues == ["test"]
        assert task_queue.backend is backend
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_get_result_storage(self, test_dir):
        """Test getting a result storage from the backend."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Get a result storage
        result_storage = backend.get_result_storage()
        
        # Check that the result storage was created correctly
        assert result_storage is not None
        assert result_storage.project_name == "test_project"
        assert result_storage.backend is backend
        
        await backend.close_async()
    
    @pytest.mark.asyncio
    async def test_backend_get_event_storage(self, test_dir):
        """Test getting an event storage from the backend."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        await backend.initialize_async()
        
        # Get an event storage
        event_storage = backend.get_event_storage()
        
        # Check that the event storage was created correctly
        assert event_storage is not None
        assert event_storage.project_name == "test_project"
        assert event_storage.backend is backend
        
        await backend.close_async()
    
    def test_backend_sync_initialization(self, test_dir):
        """Test backend initialization using sync methods."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        # Check that the backend is not initialized yet
        assert backend._connection is None
        
        # Initialize the backend
        backend.initialize()
        
        # Check that the backend is now initialized
        assert backend._connection is not None
        
        # Check that the database file was created
        db_path = test_dir / "test_project.db"
        assert db_path.exists()
        
        # Close the backend
        backend.close()
        
        # Check that the connection is closed
        assert backend._connection is None
    
    def test_backend_sync_get_connection(self, test_dir):
        """Test getting a connection using sync methods."""
        backend = SQLiteBackend(
            project_name="test_project",
            base_dir=str(test_dir)
        )
        
        backend.initialize()
        
        # Get a connection
        with backend.get_connection() as conn:
            # Check that the connection is valid
            assert conn is not None
            assert conn is backend._connection
        
        backend.close()
```

### 3.7 Integration Tests for SQLite Backend (`tests/integration/test_sqlite_backend.py`)

**Purpose**: Test end-to-end workflows with the SQLite backend.

**Implementation Requirements**:
- Test complete task lifecycle
- Test scheduling functionality
- Test result storage and retrieval
- Test event logging and querying
- Test worker processing

**Code Structure**:
```python
# tests/integration/test_sqlite_backend.py
import pytest
import asyncio
from datetime import datetime, timedelta

from src.omniq.backends.sqlite import SQLiteBackend
from tests.fixtures.factories import create_task, create_schedule, create_result, create_event
from tests.fixtures.sample_functions import simple_task, async_simple_task

class TestSQLiteBackendIntegration:
    """Integration tests for the SQLite backend."""
    
    @pytest.mark.asyncio
    async def test_task_lifecycle(self, sqlite_backend, sqlite_task_queue, sqlite_result_storage, sqlite_event_storage):
        """Test complete task lifecycle."""
        # Create a task
        task = create_task(func="tests.fixtures.sample_functions.simple_task")
        
        # Enqueue the task
        task_id = await sqlite_task_queue.enqueue_async(task)
        assert task_id == task.id
        
        # Get the task from the queue
        retrieved_task = await sqlite_task_queue.get_task_async(task_id)
        assert retrieved_task is not None
        assert retrieved_task.id == task.id
        assert retrieved_task.status.value == "pending"
        
        # Dequeue the task
        dequeued_task = await sqlite_task_queue.dequeue_async()
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        
        # Mark the task as started
        dequeued_task.mark_started()
        await sqlite_task_queue.update_task_async(dequeued_task)
        
        # Log an event
        from src.omniq.models.event import TaskEvent, EventType
        event = TaskEvent(
            task_id=task_id,
            event_type=EventType.EXECUTING,
            message="Task started",
            data={"worker_id": "test-worker"}
        )
        await sqlite_event_storage.log_async(event)
        
        # Execute the task
        result = simple_task(**dequeued_task.func_args)
        
        # Mark the task as completed
        dequeued_task.mark_completed()
        await sqlite_task_queue.update_task_async(dequeued_task)
        
        # Store the result
        from src.omniq.models.result import TaskResult, ResultStatus
        task_result = TaskResult(
            task_id=task_id,
            status=ResultStatus.COMPLETED,
            result=result,
            execution_time=0.1,
            worker_id="test-worker"
        )
        await sqlite_result_storage.store_async(task_result)
        
        # Log completion event
        completion_event = TaskEvent(
            task_id=task_id,
            event_type=EventType.COMPLETED,
            message="Task completed",
            data={"result": result}
        )
        await sqlite_event_storage.log_async(completion_event)
        
        # Get the result
        retrieved_result = await sqlite_result_storage.get_async(task_id)
        assert retrieved_result is not None
        assert retrieved_result.task_id == task_id
        assert retrieved_result.status == ResultStatus.COMPLETED
        assert retrieved_result.result == result
        
        # Get the events
        events = await sqlite_event_storage.get_events_async(task_id=task_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.COMPLETED
        assert events[1].event_type == EventType.EXECUTING
    
    @pytest.mark.asyncio
    async def test_scheduling(self, sqlite_backend, sqlite_task_queue):
        """Test task scheduling."""
        # Create a task
        task = create_task(func="tests.fixtures.sample_functions.simple_task")
        
        # Enqueue the task
        task_id = await sqlite_task_queue.enqueue_async(task)
        
        # Create a schedule
        from src.omniq.models.schedule import Schedule, ScheduleType
        schedule = Schedule(
            task_id=task_id,
            schedule_type=ScheduleType.INTERVAL,
            interval=timedelta(minutes=5),
            name="Test Schedule"
        )
        
        # Schedule the task
        schedule_id = await sqlite_task_queue.schedule_async(schedule)
        assert schedule_id == schedule.id
        
        # Get the schedule
        retrieved_schedule = await sqlite_task_queue.get_schedule_async(schedule_id)
        assert retrieved_schedule is not None
        assert retrieved_schedule.id == schedule.id
        assert retrieved_schedule.task_id == task_id
        assert retrieved_schedule.schedule_type == ScheduleType.INTERVAL
        assert retrieved_schedule.interval == timedelta(minutes=5)
        
        # Get ready schedules (should be empty since next_run_at is in the future)
        ready_schedules = await sqlite_task_queue.get_ready_schedules_async()
        assert len(ready_schedules) == 0
        
        # Update the schedule to run now
        retrieved_schedule.next_run_at = datetime.utcnow() - timedelta(minutes=1)
        await sqlite_task_queue.update_schedule_async(retrieved_schedule)
        
        # Get ready schedules (should now include our schedule)
        ready_schedules = await sqlite_task_queue.get_ready_schedules_async()
        assert len(ready_schedules) == 1
        assert ready_schedules[0].id == schedule_id
    
    @pytest.mark.asyncio
    async def test_worker_processing(self, sqlite_backend, sqlite_task_queue, sqlite_result_storage, sqlite_event_storage, sqlite_worker):
        """Test worker processing of tasks."""
        # Create a task
        task = create_task(func="tests.fixtures.sample_functions.simple_task")
        
        # Enqueue the task
        task_id = await sqlite_task_queue.enqueue_async(task)
        
        # Wait for the worker to process the task
        await asyncio.sleep(0.5)  # Give the worker time to process
        
        # Check that the task was processed
        result = await sqlite_result_storage.get_async(task_id)
        assert result is not None
        assert result.status.value == "completed"
        assert result.result == 15  # 5 + 10 from the default task args
        
        # Check that events were logged
        events = await sqlite_event_storage.get_events_async(task_id=task_id)
        assert len(events) >= 2  # At least enqueued and completed events
        
        # Check that the task was updated
        updated_task = await sqlite_task_queue.get_task_async(task_id)
        assert updated_task is not None
        assert updated_task.status.value == "completed"
        assert updated_task.started_at is not None
        assert updated_task.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_multiple_queues(self, sqlite_backend):
        """Test processing tasks from multiple queues."""
        # Create task queues for different priorities
        high_queue = sqlite_backend.get_task_queue(["high"])
        medium_queue = sqlite_backend.get_task_queue(["medium"])
        low_queue = sqlite_backend.get_task_queue(["low"])
        
        # Create result and event storage
        result_storage = sqlite_backend.get_result_storage()
        event_storage = sqlite_backend.get_event_storage()
        
        # Create a worker that processes all queues
        from src.omniq.workers.sqlite_worker import SQLiteWorker
        worker = SQLiteWorker(
            task_queue=sqlite_backend.get_task_queue(["high", "medium", "low"]),
            result_storage=result_storage,
            event_storage=event_storage,
            max_workers=1
        )
        
        await worker.start_async()
        
        try:
            # Enqueue tasks to different queues
            high_task = create_task(queue_name="high", name="High Priority Task")
            medium_task = create_task(queue_name="medium", name="Medium Priority Task")
            low_task = create_task(queue_name="low", name="Low Priority Task")
            
            high_task_id = await high_queue.enqueue_async(high_task)
            medium_task_id = await medium_queue.enqueue_async(medium_task)
            low_task_id = await low_queue.enqueue_async(low_task)
            
            # Wait for the worker to process the tasks
            await asyncio.sleep(0.5)  # Give the worker time to process
            
            # Check that all tasks were processed
            high_result = await result_storage.get_async(high_task_id)
            medium_result = await result_storage.get_async(medium_task_id)
            low_result = await result_storage.get_async(low_task_id)
            
            assert high_result is not None
            assert high_result.status.value == "completed"
            
            assert medium_result is not None
            assert medium_result.status.value == "completed"
            
            assert low_result is not None
            assert low_result.status.value == "completed"
            
        finally:
            await worker.stop_async()
    
    @pytest.mark.asyncio
    async def test_task_retry(self, sqlite_backend, sqlite_task_queue, sqlite_result_storage, sqlite_event_storage, sqlite_worker):
        """Test task retry functionality."""
        # Create a task that will fail
        task = create_task(func="tests.fixtures.sample_functions.failing_task")
        
        # Enqueue the task
        task_id = await sqlite_task_queue.enqueue_async(task)
        
        # Wait for the worker to process the task
        await asyncio.sleep(0.5)  # Give the worker time to process
        
        # Check that the task failed
        result = await sqlite_result_storage.get_async(task_id)
        assert result is not None
        assert result.status.value == "failed"
        assert result.error is not None
        
        # Check that the task was updated
        updated_task = await sqlite_task_queue.get_task_async(task_id)
        assert updated_task is not None
        assert updated_task.status.value == "failed"
        assert updated_task.retry_count == 1  # Should have been retried once
    
    @pytest.mark.asyncio
    async def test_task_ttl(self, sqlite_backend, sqlite_task_queue):
        """Test task TTL functionality."""
        # Create a task with a short TTL
        task = create_task(ttl=timedelta(seconds=-1))  # Already expired
        
        # Enqueue the task
        task_id = await sqlite_task_queue.enqueue_async(task)
        
        # Try to dequeue the task (should return None because it's expired)
        dequeued_task = await sqlite_task_queue.dequeue_async()
        assert dequeued_task is None
        
        # Check that the task is still in the queue but marked as expired
        retrieved_task = await sqlite_task_queue.get_task_async(task_id)
        assert retrieved_task is not None
        assert retrieved_task.is_expired is True
    
    @pytest.mark.asyncio
    async def test_result_ttl(self, sqlite_backend, sqlite_result_storage):
        """Test result TTL functionality."""
        # Create a result with a short TTL
        result = create_result(ttl=timedelta(seconds=-1))  # Already expired
        
        # Store the result
        await sqlite_result_storage.store_async(result)
        
        # Try to get the result (should return None because it's expired)
        retrieved_result = await sqlite_result_storage.get_async(result.task_id)
        assert retrieved_result is None
        
        # Clean up expired results
        cleaned_count = await sqlite_result_storage.cleanup_expired_async()
        assert cleaned_count >= 1
    
    @pytest.mark.asyncio
    async def test_event_querying(self, sqlite_backend, sqlite_event_storage):
        """Test event querying functionality."""
        # Create multiple events for the same task
        task_id = "test-task-123"
        
        from src.omniq.models.event import EventType
        events = [
            create_event(task_id=task_id, event_type=EventType.ENQUEUED),
            create_event(task_id=task_id, event_type=EventType.EXECUTING),
            create_event(task_id=task_id, event_type=EventType.COMPLETED),
            create_event(task_id="other-task", event_type=EventType.ENQUEUED)
        ]
        
        # Log all events
        for event in events:
            await sqlite_event_storage.log_async(event)
        
        # Get all events for the task
        task_events = await sqlite_event_storage.get_events_async(task_id=task_id)
        assert len(task_events) == 3
        
        # Get events by type
        enqueued_events = await sqlite_event_storage.get_events_async(
            task_id=task_id,
            event_type=EventType.ENQUEUED
        )
        assert len(enqueued_events) == 1
        assert enqueued_events[0].event_type == EventType.ENQUEUED
        
        # Get latest events
        latest_events = await sqlite_event_storage.get_latest_events_async(
            task_id=task_id,
            limit=2
        )
        assert len(latest_events) == 2
        assert latest_events[0].event_type == EventType.COMPLETED
        assert latest_events[1].event_type == EventType.EXECUTING
```

### 3.8 Test Configuration (`pytest.ini`)

**Purpose**: Configure pytest for the project.

**Implementation Requirements**:
- Set up pytest configuration
- Configure test discovery
- Set up markers for different test types

**Code Structure**:
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src/omniq
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80

markers =
    unit: Marks tests as unit tests
    integration: Marks tests as integration tests
    performance: Marks tests as performance tests
    slow: Marks tests as slow running
    asyncio: Marks tests as async
```

### 3.9 Test Coverage Configuration (`.coveragerc`)

**Purpose**: Configure coverage reporting.

**Implementation Requirements**:
- Set up coverage configuration
- Exclude non-test files from coverage
- Configure coverage reporting

**Code Structure**:
```ini
# .coveragerc
[run]
source = src/omniq
omit = 
    */tests/*
    */test_*
    */__init__.py
    */conftest.py
    */fixtures/*
    */migrations/*
    */venv/*
    */env/*
    */.env/*
    */.venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:

[html]
directory = htmlcov
```

## Implementation Notes

### Test Organization

The test suite is organized to mirror the source code structure:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **Performance Tests**: Test performance characteristics (optional)

### Async Testing

All async components are tested using pytest-asyncio:

1. **Async Fixtures**: Provide async components for testing
2. **Async Tests**: Use async test functions for async components
3. **Sync Tests**: Test sync wrappers using sync test functions

### Test Data Management

Test data is managed using:

1. **Factories**: Create test objects with default or custom values
2. **Fixtures**: Provide reusable test components
3. **Temporary Directories**: Isolate test data from production data

### Test Coverage

The test suite aims for comprehensive coverage:

1. **Happy Path**: Test normal operation
2. **Error Cases**: Test error handling
3. **Edge Cases**: Test boundary conditions
4. **Integration**: Test component interactions

## Testing Strategy

For Task 3, the following testing approach is used:

1. **Unit Tests**: Verify individual component functionality
2. **Integration Tests**: Verify component interactions
3. **End-to-End Tests**: Verify complete workflows
4. **Performance Tests**: Verify performance characteristics (optional)

## Dependencies

Task 3 requires the following dependencies:

- Testing: `pytest`, `pytest-asyncio`, `pytest-cov`
- Development: Same as Tasks 1 and 2

## Deliverables

1. Complete test suite for all core components
2. Complete test suite for SQLite backend components
3. Integration tests for end-to-end workflows
4. Test configuration and coverage reporting
5. Test fixtures and utilities
6. Documentation for testing approach and conventions