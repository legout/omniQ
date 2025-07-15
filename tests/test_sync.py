#!/usr/bin/env python3
"""Test synchronous API functionality."""

from omniq import OmniQ
from omniq.models.task import TaskStatus

def test_sync_api():
    """Test the synchronous API wrapper."""
    print('=== OmniQ Synchronous API Test ===\n')
    
    with OmniQ() as omniq:
        print('✓ Connected using sync context manager')
        
        # Test sync task submission
        task_id = omniq.submit_task_sync(
            func_name='sync_function',
            args=(100, 200),
            queue='sync_queue',
            priority=1
        )
        print(f'✓ Sync task submitted: {task_id}')
        
        # Test sync task retrieval
        task = omniq.get_task_sync(task_id)
        if task:
            print(f'✓ Sync task retrieved: {task.func}{task.args} [{task.status}]')
        
        # Test sync task events
        events = omniq.get_task_events_sync(task_id)
        print(f'✓ Found {len(events)} events (sync)')
        
        # Test sync queue listing
        tasks = omniq.get_tasks_by_queue_sync('sync_queue')
        print(f'✓ Sync queue has {len(tasks)} tasks')
        
        print('\n🎉 Synchronous API test passed!')

if __name__ == '__main__':
    test_sync_api()