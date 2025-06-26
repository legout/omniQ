import pytest

from omniq import OmniQ


@pytest.fixture
def omniq_instance():
    """Provides an OmniQ instance with in-memory storage for isolated tests."""
    return OmniQ(task_queue_url="memory://", result_storage_url="memory://")