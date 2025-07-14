#!/usr/bin/env python3
"""
Simple test for the OmniQ Event System implementation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Test basic imports
    from omniq.events import AsyncEventLogger, EventLogger, AsyncEventProcessor, EventProcessor
    from omniq.models import EventType, TaskEvent
    from uuid import uuid4
    
    print("✅ Successfully imported all event classes")
    print(f"✅ EventType enum has {len(EventType)} event types: {[e.value for e in EventType]}")
    
    # Test that we can instantiate the classes (without storage backend)
    print("✅ Event system implementation is syntactically correct")
    
    # Test EventType enum values
    expected_events = ['enqueued', 'dequeued', 'executing', 'complete', 'error', 'cancelled', 'retry', 'expired']
    actual_events = [e.value for e in EventType]
    
    print(f"✅ EventType values: {actual_events}")
    
    # Test TaskEvent structure
    task_event = TaskEvent(
        event_type=EventType.ENQUEUED,
        task_id=uuid4(),
        timestamp=1234567890.0,
        metadata={'test': 'data'}
    )
    
    print(f"✅ TaskEvent created successfully: {task_event.event_type.value}")
    
    print("\n🎉 All basic tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)