#!/usr/bin/env python3
"""
Quick test script for the serialization module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from omniq.serialization import (
    SerializationDetector, MsgspecSerializer, DillSerializer, 
    SerializationManager, SerializationFormat,
    serialize, deserialize, serialize_with_metadata, deserialize_with_metadata
)
from omniq.models import Task, TaskStatus, TaskPriority


def test_serialization_detector():
    """Test the SerializationDetector class."""
    print("Testing SerializationDetector...")
    
    detector = SerializationDetector()
    
    # Test basic types
    assert detector.can_use_msgspec(42) == True
    assert detector.can_use_msgspec("hello") == True
    assert detector.can_use_msgspec([1, 2, 3]) == True
    assert detector.can_use_msgspec({"key": "value"}) == True
    assert detector.can_use_msgspec(None) == True
    
    # Test complex types that need dill
    def test_func():
        return "test"
    
    assert detector.can_use_msgspec(test_func) == False
    assert detector.can_use_msgspec(lambda x: x) == False
    
    # Test format detection
    assert detector.detect_format(42) == SerializationFormat.MSGSPEC
    assert detector.detect_format(test_func) == SerializationFormat.DILL
    
    print("✓ SerializationDetector tests passed")


def test_msgspec_serializer():
    """Test the MsgspecSerializer class."""
    print("Testing MsgspecSerializer...")
    
    serializer = MsgspecSerializer()
    
    # Test basic serialization
    data = {"test": 42, "list": [1, 2, 3]}
    serialized = serializer.serialize(data)
    assert serialized is not None
    
    deserialized = serializer.deserialize(serialized)
    assert deserialized == data
    
    print("✓ MsgspecSerializer tests passed")


def test_dill_serializer():
    """Test the DillSerializer class."""
    print("Testing DillSerializer...")
    
    serializer = DillSerializer()
    
    # Test function serialization
    def test_func(x):
        return x * 2
    
    serialized = serializer.serialize(test_func)
    deserialized = serializer.deserialize(serialized)
    
    assert deserialized(5) == 10
    
    print("✓ DillSerializer tests passed")


def test_serialization_manager():
    """Test the SerializationManager class."""
    print("Testing SerializationManager...")
    
    manager = SerializationManager()
    
    # Test basic data
    basic_data = {"key": "value", "number": 42}
    serialized_data, format_used = manager.serialize(basic_data)
    assert format_used == SerializationFormat.MSGSPEC
    
    deserialized = manager.deserialize(serialized_data, format_used)
    assert deserialized == basic_data
    
    # Test complex data
    def complex_func(x):
        return x + 1
    
    serialized_data, format_used = manager.serialize(complex_func)
    assert format_used == SerializationFormat.DILL
    
    deserialized = manager.deserialize(serialized_data, format_used)
    assert deserialized(5) == 6
    
    print("✓ SerializationManager tests passed")


def test_metadata_serialization():
    """Test serialization with metadata."""
    print("Testing metadata serialization...")
    
    manager = SerializationManager()
    
    # Test with metadata
    data = {"test": "data"}
    serialized_dict = manager.serialize_with_metadata(data)
    
    assert 'data' in serialized_dict
    assert 'format' in serialized_dict
    assert 'metadata' in serialized_dict
    
    deserialized = manager.deserialize_with_metadata(serialized_dict)
    assert deserialized == data
    
    print("✓ Metadata serialization tests passed")


def test_omniq_models():
    """Test serialization with OmniQ models."""
    print("Testing OmniQ models serialization...")
    
    manager = SerializationManager()
    
    # Create a simple test function
    def test_function(arg1, arg2, key=None):
        return f"Hello {arg1} {arg2} {key}"
    
    # Create a sample task
    task = Task(
        func=test_function,
        args=("arg1", "arg2"),
        kwargs={"key": "value"},
        queue="default",
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    
    # Test serialization (this should use DILL because of the function)
    serialized_data, format_used = manager.serialize(task)
    assert format_used == SerializationFormat.DILL
    
    deserialized = manager.deserialize(serialized_data, format_used, Task)
    assert deserialized.id == task.id
    assert deserialized.func(("arg1", "arg2"), {"key": "value"}) == test_function(("arg1", "arg2"), {"key": "value"})
    assert deserialized.args == task.args
    assert deserialized.kwargs == task.kwargs
    
    print("✓ OmniQ models serialization tests passed")


def test_convenience_functions():
    """Test the convenience functions."""
    print("Testing convenience functions...")
    
    # Test basic convenience functions
    data = {"test": 42}
    serialized_data, format_used = serialize(data)
    deserialized = deserialize(serialized_data, format_used)
    assert deserialized == data
    
    # Test metadata convenience functions
    serialized_dict = serialize_with_metadata(data)
    deserialized = deserialize_with_metadata(serialized_dict)
    assert deserialized == data
    
    print("✓ Convenience functions tests passed")


if __name__ == "__main__":
    print("Running serialization module tests...")
    print("=" * 50)
    
    try:
        test_serialization_detector()
        test_msgspec_serializer()
        test_dill_serializer()
        test_serialization_manager()
        test_metadata_serialization()
        test_omniq_models()
        test_convenience_functions()
        
        print("=" * 50)
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)