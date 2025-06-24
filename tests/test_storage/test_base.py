import pytest
from omniq.storage.base import BaseTaskStorage, BaseResultStorage, BaseEventStorage
from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.models.task_event import TaskEvent
from typing import Optional, List
from datetime import datetime

def test_base_task_storage_interface():
    """Test the BaseTaskStorage interface methods are defined."""
    # Create a mock implementation of BaseTaskStorage
    class MockTaskStorage(BaseTaskStorage):
        def store_task(self, task: Task) -> None:
            pass
        
        async def store_task_async(self, task: Task) -> None:
            pass
        
        def get_task(self, task_id: str) -> Optional[Task]:
            return None
        
        async def get_task_async(self, task_id: str) -> Optional[Task]:
            return None
        
        def get_tasks(self, limit: int = 100) -> List[Task]:
            return []
        
        async def get_tasks_async(self, limit: int = 100) -> List[Task]:
            return []
        
        def delete_task(self, task_id: str) -> bool:
            return False
        
        async def delete_task_async(self, task_id: str) -> bool:
            return False
        
        def cleanup_expired_tasks(self, current_time: datetime) -> int:
            return 0
        
        async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
            return 0
        
        def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
            return False
        
        async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
            return False
        
        def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
            return None
        
        async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
            return None
    
    storage = MockTaskStorage()
    assert hasattr(storage, 'store_task')
    assert hasattr(storage, 'store_task_async')
    assert hasattr(storage, 'get_task')
    assert hasattr(storage, 'get_task_async')
    assert hasattr(storage, 'get_tasks')
    assert hasattr(storage, 'get_tasks_async')
    assert hasattr(storage, 'delete_task')
    assert hasattr(storage, 'delete_task_async')
    assert hasattr(storage, 'cleanup_expired_tasks')
    assert hasattr(storage, 'cleanup_expired_tasks_async')
    assert hasattr(storage, 'update_schedule_state')
    assert hasattr(storage, 'update_schedule_state_async')
    assert hasattr(storage, 'get_schedule_state')
    assert hasattr(storage, 'get_schedule_state_async')
    
    # Test that methods can be called without raising exceptions
    storage.store_task(Task(func=lambda x: x, id="test-task"))
    storage.get_task("test-task")
    storage.get_tasks()
    storage.delete_task("test-task")
    storage.cleanup_expired_tasks(datetime.now())
    storage.update_schedule_state("test-schedule", True)
    storage.get_schedule_state("test-schedule")

@pytest.mark.asyncio
async def test_base_task_storage_async_interface():
    """Test the async methods of BaseTaskStorage interface."""
    class MockTaskStorage(BaseTaskStorage):
        def store_task(self, task: Task) -> None:
            pass
        
        async def store_task_async(self, task: Task) -> None:
            pass
        
        def get_task(self, task_id: str) -> Optional[Task]:
            return None
        
        async def get_task_async(self, task_id: str) -> Optional[Task]:
            return None
        
        def get_tasks(self, limit: int = 100) -> List[Task]:
            return []
        
        async def get_tasks_async(self, limit: int = 100) -> List[Task]:
            return []
        
        def delete_task(self, task_id: str) -> bool:
            return False
        
        async def delete_task_async(self, task_id: str) -> bool:
            return False
        
        def cleanup_expired_tasks(self, current_time: datetime) -> int:
            return 0
        
        async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
            return 0
        
        def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
            return False
        
        async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
            return False
        
        def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
            return None
        
        async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
            return None
    
    storage = MockTaskStorage()
    await storage.store_task_async(Task(func=lambda x: x, id="test-task"))
    await storage.get_task_async("test-task")
    await storage.get_tasks_async()
    await storage.delete_task_async("test-task")
    await storage.cleanup_expired_tasks_async(datetime.now())
    await storage.update_schedule_state_async("test-schedule", True)
    await storage.get_schedule_state_async("test-schedule")

def test_base_result_storage_interface():
    """Test the BaseResultStorage interface methods are defined."""
    class MockResultStorage(BaseResultStorage):
        def store_result(self, result: TaskResult) -> None:
            pass
        
        async def store_result_async(self, result: TaskResult) -> None:
            pass
        
        def get_result(self, task_id: str) -> Optional[TaskResult]:
            return None
        
        async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
            return None
        
        def get_results(self, limit: int = 100) -> List[TaskResult]:
            return []
        
        async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
            return []
        
        def delete_result(self, task_id: str) -> bool:
            return False
        
        async def delete_result_async(self, task_id: str) -> bool:
            return False
        
        def cleanup_expired_results(self, current_time: datetime) -> int:
            return 0
        
        async def cleanup_expired_results_async(self, current_time: datetime) -> int:
            return 0
    
    storage = MockResultStorage()
    assert hasattr(storage, 'store_result')
    assert hasattr(storage, 'store_result_async')
    assert hasattr(storage, 'get_result')
    assert hasattr(storage, 'get_result_async')
    assert hasattr(storage, 'get_results')
    assert hasattr(storage, 'get_results_async')
    assert hasattr(storage, 'delete_result')
    assert hasattr(storage, 'delete_result_async')
    assert hasattr(storage, 'cleanup_expired_results')
    assert hasattr(storage, 'cleanup_expired_results_async')
    
    # Test that methods can be called without raising exceptions
    storage.store_result(TaskResult(task_id="test-task", status="success", result=None, error=None, completed_at=datetime.now()))
    storage.get_result("test-task")
    storage.get_results()
    storage.delete_result("test-task")
    storage.cleanup_expired_results(datetime.now())

@pytest.mark.asyncio
async def test_base_result_storage_async_interface():
    """Test the async methods of BaseResultStorage interface."""
    class MockResultStorage(BaseResultStorage):
        def store_result(self, result: TaskResult) -> None:
            pass
        
        async def store_result_async(self, result: TaskResult) -> None:
            pass
        
        def get_result(self, task_id: str) -> Optional[TaskResult]:
            return None
        
        async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
            return None
        
        def get_results(self, limit: int = 100) -> List[TaskResult]:
            return []
        
        async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
            return []
        
        def delete_result(self, task_id: str) -> bool:
            return False
        
        async def delete_result_async(self, task_id: str) -> bool:
            return False
        
        def cleanup_expired_results(self, current_time: datetime) -> int:
            return 0
        
        async def cleanup_expired_results_async(self, current_time: datetime) -> int:
            return 0
    
    storage = MockResultStorage()
    await storage.store_result_async(TaskResult(task_id="test-task", status="success", result=None, error=None, completed_at=datetime.now()))
    await storage.get_result_async("test-task")
    await storage.get_results_async()
    await storage.delete_result_async("test-task")
    await storage.cleanup_expired_results_async(datetime.now())

def test_base_event_storage_interface():
    """Test the BaseEventStorage interface methods are defined."""
    class MockEventStorage(BaseEventStorage):
        def log_event(self, event: TaskEvent) -> None:
            pass
        
        async def log_event_async(self, event: TaskEvent) -> None:
            pass
        
        def get_events(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
            return []
        
        async def get_events_async(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
            return []
        
        def cleanup_old_events(self, retention_days: int) -> int:
            return 0
        
        async def cleanup_old_events_async(self, retention_days: int) -> int:
            return 0
    
    storage = MockEventStorage()
    assert hasattr(storage, 'log_event')
    assert hasattr(storage, 'log_event_async')
    assert hasattr(storage, 'get_events')
    assert hasattr(storage, 'get_events_async')
    assert hasattr(storage, 'cleanup_old_events')
    assert hasattr(storage, 'cleanup_old_events_async')
    
    # Test that methods can be called without raising exceptions
    from omniq.events.types import EventType
    storage.log_event(TaskEvent(task_id="test-task", event_type=EventType.ENQUEUED.value, timestamp=datetime.now().timestamp(), metadata={}))
    assert storage.get_events() == []
    storage.cleanup_old_events(30)

@pytest.mark.asyncio
async def test_base_event_storage_async_interface():
    """Test the async methods of BaseEventStorage interface."""
    class MockEventStorage(BaseEventStorage):
        def log_event(self, event: TaskEvent) -> None:
            pass
        
        async def log_event_async(self, event: TaskEvent) -> None:
            pass
        
        def get_events(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
            return []
        
        async def get_events_async(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
            return []
        
        def cleanup_old_events(self, retention_days: int) -> int:
            return 0
        
        async def cleanup_old_events_async(self, retention_days: int) -> int:
            return 0
    
    storage = MockEventStorage()
    from omniq.events.types import EventType
    await storage.log_event_async(TaskEvent(task_id="test-task", event_type=EventType.ENQUEUED.value, timestamp=datetime.now().timestamp(), metadata={}))
    assert await storage.get_events_async() == []
    await storage.cleanup_old_events_async(30)
