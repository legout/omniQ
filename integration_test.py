#!/usr/bin/env python3
"""
Integration test to verify serialization works with OmniQ components.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from omniq.serialization import serialize, deserialize, serialize_with_metadata, deserialize_with_metadata
from omniq.models import Task, TaskStatus, TaskPriority, TaskResult, TaskEvent, EventType
from omniq.config import OmniQConfig
from datetime import datetime
from uuid import uuid4

def test_integration():
    """Test integration with various OmniQ components."""
    print("Testing integration with OmniQ components...")
    
    # Test with OmniQ config
    config = OmniQConfig(
        task_queue_type="memory",
        result_storage_type="memory",
        log_level="INFO"
    )
    
    # Serialize config
    config_data = serialize_with_metadata(config)
    deserialized_config = deserialize_with_metadata(config_data)
    assert deserialized_config.task_queue_type == config.task_queue_type
    print("✓ Config serialization works")
    
    # Test with TaskResult
    result = TaskResult(
        task_id=uuid4(),
        status=TaskStatus.COMPLETE,
        result={"message": "Task completed successfully"},
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        execution_time=1.5
    )
    
    result_data = serialize_with_metadata(result)
    deserialized_result = deserialize_with_metadata(result_data)
    assert deserialized_result.task_id == result.task_id
    assert deserialized_result.status == result.status
    print("✓ TaskResult serialization works")
    
    # Test with TaskEvent
    event = TaskEvent.create_complete(
        task_id=uuid4(),
        worker_id="worker-1",
        execution_time=2.0
    )
    
    event_data = serialize_with_metadata(event)
    deserialized_event = deserialize_with_metadata(event_data)
    assert deserialized_event.task_id == event.task_id
    assert deserialized_event.event_type == event.event_type
    print("✓ TaskEvent serialization works")
    
    # Test with complex nested data
    complex_data = {
        "task": Task(
            func=lambda x: x * 2,
            args=(5,),
            kwargs={"multiplier": 2}
        ),
        "config": config,
        "results": [result],
        "events": [event]
    }
    
    complex_data_serialized = serialize_with_metadata(complex_data)
    deserialized_complex = deserialize_with_metadata(complex_data_serialized)
    
    assert deserialized_complex["config"].task_queue_type == config.task_queue_type
    assert len(deserialized_complex["results"]) == 1
    assert len(deserialized_complex["events"]) == 1
    print("✓ Complex nested data serialization works")
    
    print("✅ All integration tests passed!")

if __name__ == "__main__":
    test_integration()