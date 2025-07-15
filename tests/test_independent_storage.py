"""
Tests for independent storage backend selection functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from omniq import OmniQ
from omniq.models.config import OmniQConfig, StorageBackendConfig
from omniq.storage.factory import StorageBackendFactory


class TestIndependentStorageSelection:
    """Test independent storage backend selection."""
    
    def test_storage_backend_factory_creation(self):
        """Test that the factory can create different storage backends."""
        # Test memory backend creation
        memory_config = StorageBackendConfig(backend_type="memory")
        
        task_queue = StorageBackendFactory.create_task_queue(memory_config, async_mode=True)
        result_storage = StorageBackendFactory.create_result_storage(memory_config, async_mode=True)
        event_storage = StorageBackendFactory.create_event_storage(memory_config, async_mode=True)
        schedule_storage = StorageBackendFactory.create_schedule_storage(memory_config, async_mode=True)
        
        assert task_queue is not None
        assert result_storage is not None
        assert event_storage is not None
        assert schedule_storage is not None
        
        # Check that they are different instances
        assert task_queue is not result_storage
        assert result_storage is not event_storage
        assert event_storage is not schedule_storage
    
    def test_sqlite_backend_with_url(self):
        """Test SQLite backend creation with URL configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            
            sqlite_config = StorageBackendConfig(
                backend_type="sqlite",
                url=f"sqlite:///{db_path}"
            )
            
            task_queue = StorageBackendFactory.create_task_queue(sqlite_config, async_mode=True)
            assert task_queue is not None
    
    def test_file_backend_with_config(self):
        """Test file backend creation with config dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_config = StorageBackendConfig(
                backend_type="file",
                config={
                    "base_dir": temp_dir,
                    "serialization_format": "json"
                }
            )
            
            result_storage = StorageBackendFactory.create_result_storage(file_config, async_mode=True)
            assert result_storage is not None
    
    def test_unsupported_backend_error(self):
        """Test that unsupported backends raise appropriate errors."""
        unsupported_config = StorageBackendConfig(backend_type="unsupported_backend")
        
        with pytest.raises(ValueError, match="Unsupported task queue backend"):
            StorageBackendFactory.create_task_queue(unsupported_config, async_mode=True)
    
    def test_omniq_config_backend_methods(self):
        """Test that OmniQConfig provides correct backend configurations."""
        config = OmniQConfig(
            task_queue_backend=StorageBackendConfig(backend_type="memory"),
            result_storage_backend=StorageBackendConfig(backend_type="sqlite", url="sqlite:///test.db"),
            event_storage_backend=StorageBackendConfig(backend_type="file", config={"base_dir": "./events"}),
            schedule_storage_backend=StorageBackendConfig(backend_type="memory")
        )
        
        # Test that helper methods return correct configurations
        task_config = config.get_task_queue_backend_config()
        assert task_config.backend_type == "memory"
        
        result_config = config.get_result_storage_backend_config()
        assert result_config.backend_type == "sqlite"
        assert result_config.url == "sqlite:///test.db"
        
        event_config = config.get_event_storage_backend_config()
        assert event_config.backend_type == "file"
        assert event_config.config is not None
        assert event_config.config["base_dir"] == "./events"
        
        schedule_config = config.get_schedule_storage_backend_config()
        assert schedule_config.backend_type == "memory"
    
    def test_omniq_config_fallback_to_env(self):
        """Test that OmniQConfig falls back to environment variables."""
        # Set environment variables
        os.environ["OMNIQ_TASK_QUEUE_TYPE"] = "sqlite"
        os.environ["OMNIQ_TASK_QUEUE_URL"] = "sqlite:///env_test.db"
        os.environ["OMNIQ_RESULT_STORAGE_TYPE"] = "memory"
        
        try:
            # Create config without explicit backend configurations
            config = OmniQConfig()
            
            # Test fallback behavior
            task_config = config.get_task_queue_backend_config()
            assert task_config.backend_type == "sqlite"
            assert task_config.url == "sqlite:///env_test.db"
            
            result_config = config.get_result_storage_backend_config()
            assert result_config.backend_type == "memory"
            
            # Event storage should fall back to task queue backend
            event_config = config.get_event_storage_backend_config()
            assert event_config.backend_type == "sqlite"
            
        finally:
            # Clean up environment variables
            for key in ["OMNIQ_TASK_QUEUE_TYPE", "OMNIQ_TASK_QUEUE_URL", "OMNIQ_RESULT_STORAGE_TYPE"]:
                if key in os.environ:
                    del os.environ[key]
    
    def test_omniq_config_from_env_method(self):
        """Test OmniQConfig.from_env() method."""
        # Set environment variables
        os.environ["OMNIQ_PROJECT_NAME"] = "test_project"
        os.environ["OMNIQ_DEFAULT_QUEUE"] = "test_queue"
        os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"
        
        try:
            config = OmniQConfig.from_env()
            
            assert config.project_name == "test_project"
            assert config.default_queue == "test_queue"
            assert config.log_level == "DEBUG"
            
        finally:
            # Clean up environment variables
            for key in ["OMNIQ_PROJECT_NAME", "OMNIQ_DEFAULT_QUEUE", "OMNIQ_LOG_LEVEL"]:
                if key in os.environ:
                    del os.environ[key]
    
    def test_mixed_backend_configuration(self):
        """Test mixed backend configuration (different backends for different components)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = OmniQConfig(
                task_queue_backend=StorageBackendConfig(backend_type="memory"),
                result_storage_backend=StorageBackendConfig(
                    backend_type="file",
                    config={"base_dir": temp_dir}
                ),
                event_storage_backend=StorageBackendConfig(backend_type="memory"),
                schedule_storage_backend=StorageBackendConfig(
                    backend_type="sqlite",
                    url="sqlite:///schedules.db"
                )
            )
            
            # Test that we can create OmniQ instance with mixed configuration
            omniq = OmniQ(config=config)
            assert omniq is not None
            assert omniq.config == config
            
            # Test that the configuration is properly set
            assert omniq.config.get_task_queue_backend_config().backend_type == "memory"
            assert omniq.config.get_result_storage_backend_config().backend_type == "file"
            assert omniq.config.get_event_storage_backend_config().backend_type == "memory"
            assert omniq.config.get_schedule_storage_backend_config().backend_type == "sqlite"
    
    def test_supported_backends_list(self):
        """Test that factory returns list of supported backends."""
        supported = StorageBackendFactory.get_supported_backends()
        
        assert isinstance(supported, dict)
        assert "task_queue" in supported
        assert "result_storage" in supported
        assert "event_storage" in supported
        assert "schedule_storage" in supported
        
        # Memory and SQLite should always be supported
        assert "memory" in supported["task_queue"]
        assert "sqlite" in supported["task_queue"]
        assert "memory" in supported["result_storage"]
        assert "sqlite" in supported["result_storage"]
    
    def test_backward_compatibility_with_legacy_backend(self):
        """Test that legacy backend parameter still works."""
        from omniq.backend.sqlite import SQLiteBackend
        
        # Test legacy backend approach
        backend = SQLiteBackend()
        omniq = OmniQ(backend=backend)
        
        assert omniq.backend is backend
        assert omniq.config is not None  # Should still have config
    
    @pytest.mark.asyncio
    async def test_independent_storage_connection(self):
        """Test that independent storage components can be connected."""
        config = OmniQConfig(
            task_queue_backend=StorageBackendConfig(backend_type="memory"),
            result_storage_backend=StorageBackendConfig(backend_type="memory"),
            event_storage_backend=StorageBackendConfig(backend_type="memory"),
            schedule_storage_backend=StorageBackendConfig(backend_type="memory")
        )
        
        omniq = OmniQ(config=config)
        
        # Test async connection
        await omniq.connect()
        
        # Verify storage components are initialized
        assert omniq._task_queue is not None
        assert omniq._result_storage is not None
        assert omniq._event_storage is not None
        assert omniq._schedule_storage is not None
        
        # Test that they are different instances (independent)
        assert omniq._task_queue is not omniq._result_storage
        
        await omniq.disconnect()
    
    def test_independent_storage_connection_sync(self):
        """Test that independent storage components can be connected synchronously."""
        config = OmniQConfig(
            task_queue_backend=StorageBackendConfig(backend_type="memory"),
            result_storage_backend=StorageBackendConfig(backend_type="memory"),
            event_storage_backend=StorageBackendConfig(backend_type="memory"),
            schedule_storage_backend=StorageBackendConfig(backend_type="memory")
        )
        
        omniq = OmniQ(config=config)
        
        # Test sync connection
        omniq.connect_sync()
        
        # Verify storage components are initialized
        assert omniq._task_queue is not None
        assert omniq._result_storage is not None
        assert omniq._event_storage is not None
        assert omniq._schedule_storage is not None
        
        omniq.disconnect_sync()


if __name__ == "__main__":
    pytest.main([__file__])