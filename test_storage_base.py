#!/usr/bin/env python3
"""
Test script for OmniQ storage base interfaces.
"""

from uuid import uuid4
from src.omniq.storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage
from src.omniq.models import Task, TaskResult, TaskEvent, TaskStatus, EventType


class TestTaskQueue(BaseTaskQueue):
    """Test implementation of BaseTaskQueue"""
    
    async def enqueue(self, task: Task) -> None:
        pass
    
    async def dequeue(self, queue: str = "default", timeout=None):
        return None
    
    async def ack(self, task_id):
        pass
    
    async def nack(self, task_id, requeue=True):
        pass
    
    async def get_queue_info(self, queue="default"):
        return {"size": 0}
    
    async def list_queues(self):
        return ["default"]
    
    async def purge_queue(self, queue="default"):
        return 0
    
    async def close(self):
        pass
    
    async def connect(self):
        pass


class TestResultStorage(BaseResultStorage):
    """Test implementation of BaseResultStorage"""
    
    async def store_result(self, result):
        pass
    
    async def get_result(self, task_id):
        return None
    
    async def delete_result(self, task_id):
        return False
    
    async def get_results(self, task_ids):
        return {}
    
    async def cleanup_expired_results(self):
        return 0
    
    async def close(self):
        pass
    
    async def connect(self):
        pass


class TestEventStorage(BaseEventStorage):
    """Test implementation of BaseEventStorage"""
    
    async def log_event(self, event):
        pass
    
    async def get_events(self, task_id, limit=None):
        return []
    
    async def get_events_by_type(self, event_type, limit=None):
        return []
    
    async def get_events_by_queue(self, queue, limit=None):
        return []
    
    async def cleanup_old_events(self, max_age_seconds):
        return 0
    
    async def close(self):
        pass
    
    async def connect(self):
        pass


def test_interfaces():
    """Test that the interfaces can be instantiated and used."""
    print("Testing storage base interfaces...")
    
    # Test instantiation
    task_queue = TestTaskQueue()
    result_storage = TestResultStorage()
    event_storage = TestEventStorage()
    
    print("✓ All storage interfaces instantiated successfully")
    
    # Test that sync methods exist
    assert hasattr(task_queue, 'enqueue_sync')
    assert hasattr(task_queue, 'dequeue_sync')
    assert hasattr(result_storage, 'store_result_sync')
    assert hasattr(result_storage, 'get_result_sync')
    assert hasattr(event_storage, 'log_event_sync')
    assert hasattr(event_storage, 'get_events_sync')
    
    print("✓ All sync wrapper methods exist")
    
    # Test context manager methods exist
    assert hasattr(task_queue, '__enter__')
    assert hasattr(task_queue, '__exit__')
    assert hasattr(task_queue, '__aenter__')
    assert hasattr(task_queue, '__aexit__')
    
    print("✓ Context manager methods exist")
    
    # Test creating sample data objects
    task = Task(func=lambda: None)
    result = TaskResult(task_id=task.id, status=TaskStatus.COMPLETE)
    event = TaskEvent(task_id=task.id, event_type=EventType.ENQUEUED)
    
    print("✓ Sample data objects created successfully")
    
    print("\nAll tests passed! Storage base interfaces are working correctly.")


if __name__ == "__main__":
    test_interfaces()