"""Test script for the core API and configuration system implementation."""

import asyncio
import uuid
from datetime import datetime, timedelta

# Test imports
try:
    from src.omniq.core import AsyncOmniQ, OmniQ
    from src.omniq.models.config import OmniQConfig
    from src.omniq.config import settings, env, loader
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)


def test_configuration_system():
    """Test the configuration system."""
    print("\n=== Testing Configuration System ===")
    
    # Test settings
    print(f"Default worker: {settings.DEFAULT_WORKER}")
    print(f"Default base dir: {settings.BASE_DIR}")
    print(f"Default task TTL: {settings.TASK_TTL}")
    
    # Test environment variables (these will use defaults since no env vars are set)
    print(f"Env default worker: {env.default_worker}")
    print(f"Env base dir: {env.base_dir}")
    print(f"Env task TTL: {env.task_ttl}")
    
    # Test configuration loading
    config_dict = {
        "project_name": "test_project",
        "task_ttl": 7200,
        "worker_type": "thread"
    }
    
    loaded_config = loader.from_dict(config_dict)
    print(f"Loaded config: {loaded_config}")
    
    # Test configuration object
    config = OmniQConfig(
        project_name="test_project",
        task_queue_type="memory",
        result_storage_type="memory",
        worker_type="async"
    )
    print(f"Config object: {config}")
    
    print("✓ Configuration system tests passed")


async def test_async_omniq():
    """Test AsyncOmniQ basic functionality."""
    print("\n=== Testing AsyncOmniQ ===")
    
    # Create basic instance
    config = OmniQConfig(project_name="test_async")
    omniq = AsyncOmniQ(config=config)
    
    print(f"Project name: {omniq.project_name}")
    print(f"Config: {omniq.config}")
    
    # Test context manager
    async with AsyncOmniQ(config=config) as omniq_ctx:
        print(f"Context manager works: {omniq_ctx.project_name}")
    
    # Test factory methods
    omniq_from_dict = await AsyncOmniQ.from_dict({
        "project_name": "test_from_dict",
        "task_ttl": 3600
    })
    print(f"From dict: {omniq_from_dict.project_name}")
    
    print("✓ AsyncOmniQ tests passed")


def test_sync_omniq():
    """Test OmniQ synchronous wrapper."""
    print("\n=== Testing OmniQ (Sync) ===")
    
    # Create basic instance
    config = OmniQConfig(project_name="test_sync")
    omniq = OmniQ(config=config)
    
    print(f"Project name: {omniq._async_omniq.project_name}")
    print(f"Config: {omniq._async_omniq.config}")
    
    # Test context manager
    with OmniQ(config=config) as omniq_ctx:
        print(f"Sync context manager works: {omniq_ctx._async_omniq.project_name}")
    
    # Test factory methods
    omniq_from_dict = OmniQ.from_dict({
        "project_name": "test_sync_from_dict",
        "task_ttl": 1800
    })
    print(f"Sync from dict: {omniq_from_dict._async_omniq.project_name}")
    
    print("✓ OmniQ sync tests passed")


def test_configuration_models():
    """Test configuration model validation."""
    print("\n=== Testing Configuration Models ===")
    
    from src.omniq.models.config import (
        SQLiteQueueConfig,
        FileResultStorageConfig,
        AsyncWorkerConfig,
        OmniQConfig
    )
    
    # Test queue config
    queue_config = SQLiteQueueConfig(
        project_name="test",
        base_dir="/tmp/test",
        queues=["high", "medium", "low"]
    )
    print(f"Queue config: {queue_config}")
    
    # Test result storage config
    storage_config = FileResultStorageConfig(
        project_name="test",
        base_dir="/tmp/test",
        fsspec_uri="file://"
    )
    print(f"Storage config: {storage_config}")
    
    # Test worker config
    worker_config = AsyncWorkerConfig(
        max_workers=8,
        task_timeout=600
    )
    print(f"Worker config: {worker_config}")
    
    # Test main config
    main_config = OmniQConfig(
        project_name="test_models",
        task_queue_type="sqlite",
        result_storage_type="file",
        worker_type="async",
        task_ttl=7200
    )
    print(f"Main config: {main_config}")
    
    print("✓ Configuration model tests passed")


def main():
    """Run all tests."""
    print("Testing OmniQ Core API and Configuration System")
    print("=" * 50)
    
    try:
        test_configuration_system()
        
        # Run async tests
        print("\n=== Running Async Tests ===")
        asyncio.run(test_async_omniq())
        
        # Run sync tests
        print("\n=== Running Sync Tests ===")
        test_sync_omniq()
        
        test_configuration_models()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed successfully!")
        print("\nCore API and Configuration System implementation is working correctly.")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)