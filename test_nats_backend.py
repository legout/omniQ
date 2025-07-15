#!/usr/bin/env python3
"""
Test script for NATS backend implementation.

This script tests the basic functionality of the NATS storage backend
for OmniQ, including task queuing, result storage, event logging, and
schedule management.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, 'src')

from omniq.storage.nats import (
    AsyncNATSQueue, 
    AsyncNATSResultStorage, 
    AsyncNATSEventStorage, 
    AsyncNATSScheduleStorage,
    NATSBackend,
    create_nats_backend
)
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.models.schedule import Schedule, ScheduleType, ScheduleStatus


async def test_nats_backend():
    """Test the NATS backend implementation."""
    print("🧪 Testing NATS Backend Implementation")
    print("=" * 50)
    
    # Configuration for NATS backend
    config = {
        "servers": ["nats://localhost:4222"],
        "tasks_subject": "test.omniq.tasks",
        "results_subject": "test.omniq.results", 
        "events_subject": "test.omniq.events",
        "schedules_subject": "test.omniq.schedules",
        "queue_group": "test_omniq_workers",
        "connect_timeout": 5.0,
        "reconnect_time_wait": 2.0,
        "max_reconnect_attempts": 3,
    }
    
    try:
        # Test 1: Create NATS backend
        print("1️⃣  Creating NATS backend...")
        backend = create_nats_backend(config)
        print("✅ NATS backend created successfully")
        
        # Test 2: Test connection (this will fail if NATS server is not running)
        print("\n2️⃣  Testing connection...")
        try:
            async with backend.async_context():
                print("✅ Successfully connected to NATS server")
                
                # Test 3: Test task queue
                print("\n3️⃣  Testing task queue...")
                task = Task(
                    id="test-task-1",
                    func="test_function",
                    args=("arg1", "arg2"),
                    kwargs={"key": "value"},
                    queue_name="test_queue",
                    priority=1
                )
                
                task_id = await backend.task_queue.enqueue(task)
                print(f"✅ Task enqueued with ID: {task_id}")
                
                # Test 4: Test result storage
                print("\n4️⃣  Testing result storage...")
                result = TaskResult(
                    task_id=task_id,
                    status=ResultStatus.SUCCESS,
                    result="Test result data",
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                
                await backend.result_storage.set(result)
                print("✅ Result stored successfully")
                
                retrieved_result = await backend.result_storage.get(task_id)
                if retrieved_result:
                    print(f"✅ Result retrieved: {retrieved_result.result}")
                else:
                    print("❌ Failed to retrieve result")
                
                # Test 5: Test event storage
                print("\n5️⃣  Testing event storage...")
                event = TaskEvent(
                    task_id=task_id,
                    event_type=EventType.EXECUTING,
                    message="Task started processing",
                    timestamp=datetime.utcnow()
                )
                
                await backend.event_storage.log_event(event)
                print("✅ Event logged successfully")
                
                # Test 6: Test schedule storage
                print("\n6️⃣  Testing schedule storage...")
                schedule = Schedule.from_cron(
                    cron_expression="0 */5 * * *",  # Every 5 minutes
                    func="scheduled_task",
                    args=("scheduled_arg",),
                    queue_name="scheduled_queue"
                )
                
                await backend.schedule_storage.save_schedule(schedule)
                print(f"✅ Schedule saved with ID: {schedule.id}")
                
                retrieved_schedule = await backend.schedule_storage.get_schedule(schedule.id)
                if retrieved_schedule:
                    print(f"✅ Schedule retrieved: {retrieved_schedule.cron_expression}")
                else:
                    print("❌ Failed to retrieve schedule")
                
                # Test 7: Test ready schedules
                print("\n7️⃣  Testing ready schedules...")
                ready_schedules = await backend.schedule_storage.get_ready_schedules()
                print(f"✅ Found {len(ready_schedules)} ready schedules")
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            print("💡 Make sure NATS server is running on localhost:4222")
            print("   You can start NATS with: docker run -p 4222:4222 nats:latest")
            return False
            
    except Exception as e:
        print(f"❌ Backend creation failed: {e}")
        return False
    
    print("\n🎉 All tests completed successfully!")
    return True


async def test_sync_wrappers():
    """Test the synchronous wrapper classes."""
    print("\n🔄 Testing Synchronous Wrappers")
    print("=" * 50)
    
    config = {
        "servers": ["nats://localhost:4222"],
        "connect_timeout": 5.0,
        "max_reconnect_attempts": 3,
    }
    
    try:
        # Test sync backend
        print("1️⃣  Testing sync backend...")
        backend = create_nats_backend(config)
        
        with backend:
            print("✅ Sync context manager works")
            
            # Test sync task queue
            task = Task(
                id="sync-test-task",
                func="sync_test_function",
                queue_name="sync_test_queue"
            )
            
            task_id = backend.sync_task_queue.enqueue_sync(task)
            print(f"✅ Sync task enqueued: {task_id}")
            
    except Exception as e:
        print(f"❌ Sync wrapper test failed: {e}")
        return False
    
    print("✅ Sync wrapper tests completed!")
    return True


def main():
    """Main test function."""
    print("🚀 NATS Backend Test Suite")
    print("=" * 50)
    
    # Run async tests
    async_success = asyncio.run(test_nats_backend())
    
    # Run sync tests
    sync_success = asyncio.run(test_sync_wrappers())
    
    if async_success and sync_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())