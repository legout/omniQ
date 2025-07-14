import anyio
import asyncio

class AsyncABC:
    async def async_method(self):
        return "Async Method Executed"

class SyncABC(AsyncABC):

    def sync_method(self):
        return asyncio.run(super().async_method())

def test_abc_sync():
    """Test the SyncABC class."""
    print("Testing SyncABC...")
    
    sync_abc = SyncABC()
    
    # Test synchronous method
    result = sync_abc.sync_method()
    assert result == "Async Method Executed"
    
    print("✓ SyncABC tests passed")


if __name__ == "__main__":
    test_abc_sync()
    print("🎉 All tests in test_abc.py passed!")