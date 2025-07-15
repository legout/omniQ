"""
Tests for Azure Backend functionality.

These tests verify the Azure backend implementation works correctly.
Note: These tests require Azure credentials to be configured.
"""

import os
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from omniq.backend.azure import AzureBackend
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus


@pytest.fixture
def azure_backend():
    """Create an Azure backend for testing."""
    return AzureBackend(
        container_name="omniq-test",
        prefix="test/",
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", "mock://test")
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        func="test_function",
        id="test-task-1",
        queue_name="test-queue",
        args=(1, 2),
        kwargs={"key": "value"},
        priority=1,
        run_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )


@pytest.fixture
def sample_result():
    """Create a sample result for testing."""
    return TaskResult(
        task_id="test-task-1",
        status=ResultStatus.SUCCESS,
        result={"answer": 42},
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return TaskEvent(
        task_id="test-task-1",
        event_type=EventType.COMPLETED,
        worker_id="test-worker",
        queue_name="test-queue",
        message="Task completed successfully",
    )


@pytest.fixture
def sample_schedule():
    """Create a sample schedule for testing."""
    return Schedule(
        schedule_type=ScheduleType.CRON,
        func="test_function",
        id="test-schedule-1",
        cron_expression="0 */6 * * *",
        args=(1, 2),
        status=ScheduleStatus.ACTIVE,
        created_at=datetime.utcnow(),
        next_run=datetime.utcnow() + timedelta(hours=6),
    )


class TestAzureBackend:
    """Test Azure backend functionality."""
    
    def test_backend_initialization(self, azure_backend):
        """Test backend initialization."""
        assert azure_backend.container_name == "omniq-test"
        assert azure_backend.prefix == "test/"
        assert str(azure_backend) == "AzureBackend(container='omniq-test', prefix='test/')"
    
    def test_storage_properties(self, azure_backend):
        """Test storage property access."""
        # Test async properties
        assert azure_backend.async_task_storage is not None
        assert azure_backend.async_result_storage is not None
        assert azure_backend.async_event_storage is not None
        assert azure_backend.async_schedule_storage is not None
        
        # Test sync properties
        assert azure_backend.task_storage is not None
        assert azure_backend.result_storage is not None
        assert azure_backend.event_storage is not None
        assert azure_backend.schedule_storage is not None
    
    def test_storage_property_caching(self, azure_backend):
        """Test that storage properties are cached."""
        # Test async properties are cached
        task_storage1 = azure_backend.async_task_storage
        task_storage2 = azure_backend.async_task_storage
        assert task_storage1 is task_storage2
        
        # Test sync properties are cached
        sync_storage1 = azure_backend.task_storage
        sync_storage2 = azure_backend.task_storage
        assert sync_storage1 is sync_storage2
    
    def test_get_storage_kwargs(self, azure_backend):
        """Test storage kwargs generation."""
        kwargs = azure_backend._get_storage_kwargs()
        
        expected_keys = {
            "container_name", "base_prefix", "connection_string",
            "account_name", "account_key", "sas_token",
            "tenant_id", "client_id", "client_secret",
            "azure_additional_kwargs"
        }
        
        assert set(kwargs.keys()) == expected_keys
        assert kwargs["container_name"] == "omniq-test"
        assert kwargs["base_prefix"] == "test/"


class TestAzureBackendIntegration:
    """Integration tests for Azure backend (require real Azure credentials)."""
    
    @pytest.mark.skipif(
        not os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        reason="Azure credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_async_task_lifecycle(self, azure_backend, sample_task):
        """Test complete async task lifecycle."""
        async with azure_backend:
            task_queue = azure_backend.async_task_storage
            
            # Enqueue task
            task_id = await task_queue.enqueue(sample_task)
            assert task_id == sample_task.id
            
            # Check queue size
            size = await task_queue.get_queue_size("test-queue")
            assert size >= 1
            
            # Dequeue task
            dequeued_task = await task_queue.dequeue(["test-queue"])
            assert dequeued_task is not None
            assert dequeued_task.id == sample_task.id
            assert dequeued_task.status == TaskStatus.RUNNING
            
            # Clean up
            await task_queue.delete_task(task_id)
    
    @pytest.mark.skipif(
        not os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        reason="Azure credentials not configured"
    )
    def test_sync_task_lifecycle(self, azure_backend, sample_task):
        """Test complete sync task lifecycle."""
        with azure_backend:
            task_queue = azure_backend.task_storage
            
            # Enqueue task
            task_id = task_queue.enqueue_sync(sample_task)
            assert task_id == sample_task.id
            
            # Check queue size
            size = task_queue.get_queue_size_sync("test-queue")
            assert size >= 1
            
            # Dequeue task
            dequeued_task = task_queue.dequeue_sync(["test-queue"])
            assert dequeued_task is not None
            assert dequeued_task.id == sample_task.id
            assert dequeued_task.status == TaskStatus.RUNNING
            
            # Clean up
            task_queue.delete_task_sync(task_id)
    
    @pytest.mark.skipif(
        not os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        reason="Azure credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_async_result_operations(self, azure_backend, sample_result):
        """Test async result operations."""
        async with azure_backend:
            result_storage = azure_backend.async_result_storage
            
            # Store result
            await result_storage.set(sample_result)
            
            # Retrieve result
            retrieved_result = await result_storage.get(sample_result.task_id)
            assert retrieved_result is not None
            assert retrieved_result.task_id == sample_result.task_id
            assert retrieved_result.status == sample_result.status
            
            # List results
            results = await result_storage.list_results()
            assert len(results) >= 1
            
            # Clean up
            await result_storage.delete(sample_result.task_id)
    
    @pytest.mark.skipif(
        not os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        reason="Azure credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_async_event_operations(self, azure_backend, sample_event):
        """Test async event operations."""
        async with azure_backend:
            event_storage = azure_backend.async_event_storage
            
            # Log event
            await event_storage.log_event(sample_event)
            
            # Get events
            events = await event_storage.get_events(task_id=sample_event.task_id)
            assert len(events) >= 1
            
            found_event = next(
                (e for e in events if e.id == sample_event.id), None
            )
            assert found_event is not None
            assert found_event.task_id == sample_event.task_id
            assert found_event.event_type == sample_event.event_type
    
    @pytest.mark.skipif(
        not os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        reason="Azure credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_async_schedule_operations(self, azure_backend, sample_schedule):
        """Test async schedule operations."""
        async with azure_backend:
            schedule_storage = azure_backend.async_schedule_storage
            
            # Save schedule
            await schedule_storage.save_schedule(sample_schedule)
            
            # Get schedule
            retrieved_schedule = await schedule_storage.get_schedule(sample_schedule.id)
            assert retrieved_schedule is not None
            assert retrieved_schedule.id == sample_schedule.id
            assert retrieved_schedule.schedule_type == sample_schedule.schedule_type
            
            # List schedules
            schedules = await schedule_storage.list_schedules()
            assert len(schedules) >= 1
            
            # Clean up
            await schedule_storage.delete_schedule(sample_schedule.id)


class TestAzureBackendConfiguration:
    """Test different Azure backend configurations."""
    
    def test_connection_string_config(self):
        """Test connection string configuration."""
        backend = AzureBackend(
            container_name="test",
            connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net"
        )
        
        kwargs = backend._get_storage_kwargs()
        assert kwargs["connection_string"] == "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net"
    
    def test_account_key_config(self):
        """Test account name and key configuration."""
        backend = AzureBackend(
            container_name="test",
            account_name="testaccount",
            account_key="testkey"
        )
        
        kwargs = backend._get_storage_kwargs()
        assert kwargs["account_name"] == "testaccount"
        assert kwargs["account_key"] == "testkey"
    
    def test_service_principal_config(self):
        """Test service principal configuration."""
        backend = AzureBackend(
            container_name="test",
            account_name="testaccount",
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret"
        )
        
        kwargs = backend._get_storage_kwargs()
        assert kwargs["account_name"] == "testaccount"
        assert kwargs["tenant_id"] == "tenant-id"
        assert kwargs["client_id"] == "client-id"
        assert kwargs["client_secret"] == "client-secret"
    
    def test_sas_token_config(self):
        """Test SAS token configuration."""
        backend = AzureBackend(
            container_name="test",
            account_name="testaccount",
            sas_token="?sv=2020-08-04&ss=bfqt&srt=sco&sp=rwdlacupx"
        )
        
        kwargs = backend._get_storage_kwargs()
        assert kwargs["account_name"] == "testaccount"
        assert kwargs["sas_token"] == "?sv=2020-08-04&ss=bfqt&srt=sco&sp=rwdlacupx"
    
    def test_additional_kwargs_config(self):
        """Test additional kwargs configuration."""
        additional_kwargs = {
            "client_kwargs": {
                "connection_timeout": 30,
                "read_timeout": 60,
            }
        }
        
        backend = AzureBackend(
            container_name="test",
            connection_string="test",
            azure_additional_kwargs=additional_kwargs
        )
        
        kwargs = backend._get_storage_kwargs()
        assert kwargs["azure_additional_kwargs"] == additional_kwargs


def test_create_azure_backend_from_config():
    """Test creating Azure backend from configuration dictionary."""
    from omniq.backend.azure import create_azure_backend_from_config
    
    config = {
        "container_name": "test-container",
        "prefix": "test-prefix/",
        "connection_string": "test-connection-string",
        "account_name": "test-account",
        "account_key": "test-key",
        "azure_kwargs": {
            "client_kwargs": {"timeout": 30}
        }
    }
    
    backend = create_azure_backend_from_config(config)
    
    assert backend.container_name == "test-container"
    assert backend.prefix == "test-prefix/"
    assert backend.connection_string == "test-connection-string"
    assert backend.account_name == "test-account"
    assert backend.account_key == "test-key"
    assert backend.azure_kwargs == {"client_kwargs": {"timeout": 30}}


if __name__ == "__main__":
    # Run basic tests without pytest
    backend = AzureBackend(
        container_name="omniq-test",
        connection_string="mock://test"
    )
    
    print("Testing Azure backend initialization...")
    assert backend.container_name == "omniq-test"
    print("✓ Backend initialization works")
    
    print("Testing storage properties...")
    assert backend.async_task_storage is not None
    assert backend.task_storage is not None
    print("✓ Storage properties work")
    
    print("All basic tests passed!")