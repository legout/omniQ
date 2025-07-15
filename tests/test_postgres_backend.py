"""
Tests for PostgreSQL backend implementation.

These tests require a running PostgreSQL server and are designed to verify
the core functionality of the PostgreSQL storage backend.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from omniq.backend.postgres import (
    AsyncPostgreSQLBackend,
    PostgreSQLBackend,
    create_postgres_backend,
    create_async_postgres_backend
)
from omniq.storage.postgres import (
    AsyncPostgresQueue,
    PostgresQueue,
    AsyncPostgresResultStorage,
    PostgresResultStorage,
    AsyncPostgresEventStorage,
    PostgresEventStorage,
    AsyncPostgresScheduleStorage,
    PostgresScheduleStorage
)
from omniq.models.config import PostgresConfig
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType


class TestPostgresConfig:
    """Test PostgreSQL configuration."""
    
    def test_postgres_config_defaults(self):
        """Test default configuration values."""
        config = PostgresConfig()
        
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "omniq"
        assert config.username == "postgres"
        assert config.password == ""
        assert config.min_connections == 1
        assert config.max_connections == 10
        assert config.command_timeout == 60.0
        assert config.schema == "public"
        assert config.tasks_table == "tasks"
        assert config.results_table == "results"
        assert config.events_table == "events"
        assert config.schedules_table == "schedules"
    
    def test_postgres_config_custom(self):
        """Test custom configuration values."""
        config = PostgresConfig(
            host="db.example.com",
            port=5433,
            database="custom_db",
            username="custom_user",
            password="secret",
            min_connections=5,
            max_connections=20,
            command_timeout=30.0,
            schema="custom_schema",
            tasks_table="custom_tasks",
            results_table="custom_results",
            events_table="custom_events",
            schedules_table="custom_schedules"
        )
        
        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.database == "custom_db"
        assert config.username == "custom_user"
        assert config.password == "secret"
        assert config.min_connections == 5
        assert config.max_connections == 20
        assert config.command_timeout == 30.0
        assert config.schema == "custom_schema"
        assert config.tasks_table == "custom_tasks"
        assert config.results_table == "custom_results"
        assert config.events_table == "custom_events"
        assert config.schedules_table == "custom_schedules"


class TestPostgresBackendCreation:
    """Test PostgreSQL backend creation functions."""
    
    def test_create_postgres_backend(self):
        """Test sync backend creation."""
        backend = create_postgres_backend(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        assert isinstance(backend, PostgreSQLBackend)
        assert backend.config.host == "localhost"
        assert backend.config.port == 5432
        assert backend.config.database == "test_db"
        assert backend.config.username == "test_user"
        assert backend.config.password == "test_pass"
        
        # Check storage components
        assert isinstance(backend.task_queue, PostgresQueue)
        assert isinstance(backend.result_storage, PostgresResultStorage)
        assert isinstance(backend.event_storage, PostgresEventStorage)
        assert isinstance(backend.schedule_storage, PostgresScheduleStorage)
    
    def test_create_async_postgres_backend(self):
        """Test async backend creation."""
        backend = create_async_postgres_backend(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        assert isinstance(backend, AsyncPostgreSQLBackend)
        assert backend.config.host == "localhost"
        assert backend.config.port == 5432
        assert backend.config.database == "test_db"
        assert backend.config.username == "test_user"
        assert backend.config.password == "test_pass"
        
        # Check storage components
        assert isinstance(backend.task_queue, AsyncPostgresQueue)
        assert isinstance(backend.result_storage, AsyncPostgresResultStorage)
        assert isinstance(backend.event_storage, AsyncPostgresEventStorage)
        assert isinstance(backend.schedule_storage, AsyncPostgresScheduleStorage)


class TestPostgresBackendInterface:
    """Test PostgreSQL backend interface without actual database connection."""
    
    def test_sync_backend_interface(self):
        """Test sync backend interface."""
        config = PostgresConfig(database="test_db")
        backend = PostgreSQLBackend(config)
        
        # Test that all required components are present
        assert hasattr(backend, 'task_queue')
        assert hasattr(backend, 'result_storage')
        assert hasattr(backend, 'event_storage')
        assert hasattr(backend, 'schedule_storage')
        
        # Test that all components have sync methods
        assert hasattr(backend.task_queue, 'connect_sync')
        assert hasattr(backend.task_queue, 'disconnect_sync')
        assert hasattr(backend.task_queue, 'enqueue_sync')
        assert hasattr(backend.task_queue, 'dequeue_sync')
        
        assert hasattr(backend.result_storage, 'connect_sync')
        assert hasattr(backend.result_storage, 'disconnect_sync')
        assert hasattr(backend.result_storage, 'get_sync')
        assert hasattr(backend.result_storage, 'set_sync')
        
        assert hasattr(backend.event_storage, 'connect_sync')
        assert hasattr(backend.event_storage, 'disconnect_sync')
        assert hasattr(backend.event_storage, 'log_event_sync')
        assert hasattr(backend.event_storage, 'get_events_sync')
        
        assert hasattr(backend.schedule_storage, 'connect_sync')
        assert hasattr(backend.schedule_storage, 'disconnect_sync')
        assert hasattr(backend.schedule_storage, 'save_schedule_sync')
        assert hasattr(backend.schedule_storage, 'get_schedule_sync')
    
    def test_async_backend_interface(self):
        """Test async backend interface."""
        config = PostgresConfig(database="test_db")
        backend = AsyncPostgreSQLBackend(config)
        
        # Test that all required components are present
        assert hasattr(backend, 'task_queue')
        assert hasattr(backend, 'result_storage')
        assert hasattr(backend, 'event_storage')
        assert hasattr(backend, 'schedule_storage')
        
        # Test that all components have async methods
        assert hasattr(backend.task_queue, 'connect')
        assert hasattr(backend.task_queue, 'disconnect')
        assert hasattr(backend.task_queue, 'enqueue')
        assert hasattr(backend.task_queue, 'dequeue')
        
        assert hasattr(backend.result_storage, 'connect')
        assert hasattr(backend.result_storage, 'disconnect')
        assert hasattr(backend.result_storage, 'get')
        assert hasattr(backend.result_storage, 'set')
        
        assert hasattr(backend.event_storage, 'connect')
        assert hasattr(backend.event_storage, 'disconnect')
        assert hasattr(backend.event_storage, 'log_event')
        assert hasattr(backend.event_storage, 'get_events')
        
        assert hasattr(backend.schedule_storage, 'connect')
        assert hasattr(backend.schedule_storage, 'disconnect')
        assert hasattr(backend.schedule_storage, 'save_schedule')
        assert hasattr(backend.schedule_storage, 'get_schedule')


class TestPostgresStorageComponents:
    """Test individual PostgreSQL storage components."""
    
    def test_task_queue_initialization(self):
        """Test task queue initialization."""
        queue = AsyncPostgresQueue(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            schema="test_schema",
            tasks_table="test_tasks"
        )
        
        assert queue.host == "localhost"
        assert queue.port == 5432
        assert queue.database == "test_db"
        assert queue.username == "test_user"
        assert queue.password == "test_pass"
        assert queue.schema == "test_schema"
        assert queue.tasks_table == "test_tasks"
        assert queue._pool is None
    
    def test_result_storage_initialization(self):
        """Test result storage initialization."""
        storage = AsyncPostgresResultStorage(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            schema="test_schema",
            results_table="test_results"
        )
        
        assert storage.host == "localhost"
        assert storage.port == 5432
        assert storage.database == "test_db"
        assert storage.username == "test_user"
        assert storage.password == "test_pass"
        assert storage.schema == "test_schema"
        assert storage.results_table == "test_results"
        assert storage._pool is None
    
    def test_event_storage_initialization(self):
        """Test event storage initialization."""
        storage = AsyncPostgresEventStorage(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            schema="test_schema",
            events_table="test_events"
        )
        
        assert storage.host == "localhost"
        assert storage.port == 5432
        assert storage.database == "test_db"
        assert storage.username == "test_user"
        assert storage.password == "test_pass"
        assert storage.schema == "test_schema"
        assert storage.events_table == "test_events"
        assert storage._pool is None
    
    def test_schedule_storage_initialization(self):
        """Test schedule storage initialization."""
        storage = AsyncPostgresScheduleStorage(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            schema="test_schema",
            schedules_table="test_schedules"
        )
        
        assert storage.host == "localhost"
        assert storage.port == 5432
        assert storage.database == "test_db"
        assert storage.username == "test_user"
        assert storage.password == "test_pass"
        assert storage.schema == "test_schema"
        assert storage.schedules_table == "test_schedules"
        assert storage._pool is None


class TestPostgresSerialization:
    """Test PostgreSQL serialization methods."""
    
    def test_task_serialization(self):
        """Test task serialization."""
        queue = AsyncPostgresQueue()
        
        task = Task(
            func="test.function",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            queue_name="test_queue",
            priority=5
        )
        
        serialized = queue._serialize_task(task)
        
        assert serialized["id"] == task.id
        assert serialized["func"] == "test.function"
        assert serialized["queue_name"] == "test_queue"
        assert serialized["priority"] == 5
        assert serialized["status"] == TaskStatus.PENDING.value
        assert "task_data" in serialized
    
    def test_result_serialization(self):
        """Test result serialization."""
        storage = AsyncPostgresResultStorage()
        
        result = TaskResult(
            task_id="test-task-id",
            status=ResultStatus.SUCCESS,
            result={"output": "test"},
            execution_time=1.5
        )
        
        serialized = storage._serialize_result(result)
        
        assert serialized["task_id"] == "test-task-id"
        assert serialized["status"] == ResultStatus.SUCCESS.value
        assert serialized["execution_time"] == 1.5
        assert "result_data" in serialized
    
    def test_event_serialization(self):
        """Test event serialization."""
        storage = AsyncPostgresEventStorage()
        
        event = TaskEvent(
            task_id="test-task-id",
            event_type=EventType.COMPLETED,
            message="Task completed successfully",
            worker_id="worker-1"
        )
        
        serialized = storage._serialize_event(event)
        
        assert serialized["task_id"] == "test-task-id"
        assert serialized["event_type"] == EventType.COMPLETED.value
        assert serialized["message"] == "Task completed successfully"
        assert serialized["worker_id"] == "worker-1"
        assert "event_data" in serialized
    
    def test_schedule_serialization(self):
        """Test schedule serialization."""
        storage = AsyncPostgresScheduleStorage()
        
        schedule = Schedule(
            func="test.function",
            args=(1, 2),
            schedule_type=ScheduleType.INTERVAL,
            interval=timedelta(minutes=5),
            queue_name="scheduled_queue"
        )
        
        serialized = storage._serialize_schedule(schedule)
        
        assert serialized["id"] == schedule.id
        assert serialized["func"] == "test.function"
        assert serialized["schedule_type"] == ScheduleType.INTERVAL.value
        assert serialized["interval_seconds"] == 300.0  # 5 minutes
        assert serialized["queue_name"] == "scheduled_queue"
        assert "schedule_data" in serialized


# Integration tests (require actual PostgreSQL connection)
@pytest.mark.integration
class TestPostgresIntegration:
    """Integration tests requiring actual PostgreSQL connection."""
    
    @pytest.fixture
    def postgres_config(self):
        """Provide PostgreSQL configuration for testing."""
        return PostgresConfig(
            host="localhost",
            port=5432,
            database="omniq_test",
            username="postgres",
            password="password",
            schema="test_schema"
        )
    
    @pytest.mark.asyncio
    async def test_async_backend_lifecycle(self, postgres_config):
        """Test async backend full lifecycle."""
        backend = AsyncPostgreSQLBackend(postgres_config)
        
        # Test connection
        await backend.connect()
        
        try:
            # Test task operations
            task = Task(
                func="test.function",
                args=(1, 2),
                queue_name="test_queue"
            )
            
            await backend.task_queue.enqueue(task)
            dequeued = await backend.task_queue.dequeue(["test_queue"])
            
            assert dequeued is not None
            assert dequeued.id == task.id
            
            # Test result operations
            result = TaskResult(
                task_id=task.id,
                status=ResultStatus.SUCCESS,
                result=3
            )
            
            await backend.result_storage.set(result)
            retrieved = await backend.result_storage.get(task.id)
            
            assert retrieved is not None
            assert retrieved.task_id == task.id
            assert retrieved.result == 3
            
            # Test event operations
            event = TaskEvent(
                task_id=task.id,
                event_type=EventType.COMPLETED,
                message="Test completed"
            )
            
            await backend.event_storage.log_event(event)
            events = await backend.event_storage.get_events(task_id=task.id)
            
            assert len(events) > 0
            assert events[0].task_id == task.id
            
        finally:
            await backend.disconnect()
    
    def test_sync_backend_lifecycle(self, postgres_config):
        """Test sync backend full lifecycle."""
        backend = PostgreSQLBackend(postgres_config)
        
        # Test connection
        backend.connect()
        
        try:
            # Test task operations
            task = Task(
                func="test.function",
                args=(1, 2),
                queue_name="test_queue"
            )
            
            backend.task_queue.enqueue_sync(task)
            dequeued = backend.task_queue.dequeue_sync(["test_queue"])
            
            assert dequeued is not None
            assert dequeued.id == task.id
            
            # Test result operations
            result = TaskResult(
                task_id=task.id,
                status=ResultStatus.SUCCESS,
                result=3
            )
            
            backend.result_storage.set_sync(result)
            retrieved = backend.result_storage.get_sync(task.id)
            
            assert retrieved is not None
            assert retrieved.task_id == task.id
            assert retrieved.result == 3
            
        finally:
            backend.disconnect()


if __name__ == "__main__":
    # Run basic tests without database connection
    pytest.main([__file__, "-v", "-m", "not integration"])