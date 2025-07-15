import asyncio
import pytest
from tests.test_queue_manager_integration import TestQueueManagerIntegration
from src.omniq.core import OmniQ
from src.omniq.models.config import OmniQConfig, QueueConfig

async def test_cross_queue_routing_isolated():
    """Test cross-queue task routing in isolation."""
    
    # Create fresh config
    config = OmniQConfig()
    config.add_queue_config(QueueConfig(
        name="test_queue",
        priority_algorithm="weighted",
        default_priority=5,
        min_priority=1,
        max_priority=10,
        max_size=100,
        timeout=300.0,
        max_retries=3,
        retry_delay=1.0,
        priority_weights={"urgent": 2.0, "important": 1.5}
    ))
    config.add_queue_config(QueueConfig(
        name="high_priority",
        priority_algorithm="numeric",
        default_priority=8,
        min_priority=1,
        max_priority=10
    ))
    config.queue_routing_strategy = "priority"
    
    # Create fresh OmniQ instance
    omniq = OmniQ(config=config)
    await omniq.connect()
    
    try:
        # Create test instance
        test_instance = TestQueueManagerIntegration()
        
        # Run the test
        await test_instance.test_cross_queue_routing(omniq)
        print("✅ Test passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await omniq.disconnect()

if __name__ == "__main__":
    asyncio.run(test_cross_queue_routing_isolated())