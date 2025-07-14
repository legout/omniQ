#!/usr/bin/env python3

"""
Test script for OmniQ configuration system.

This script tests:
- Default settings loading
- Environment variable overrides
- YAML configuration loading
- Configuration precedence
- Logging configuration
- Configuration validation
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omniq.config import (
    Settings, 
    EnvConfig, 
    ConfigProvider, 
    LoggingConfig,
    get_settings,
    get_logging_config,
    set_override,
    clear_overrides,
    validate_config,
    save_config_template
)


def test_default_settings():
    """Test default settings loading."""
    print("Testing default settings...")
    
    settings = Settings()
    
    # Test some key defaults
    assert settings.LOG_LEVEL == "INFO"
    assert settings.WORKER_COUNT == 4
    assert settings.TASK_QUEUE_TYPE == "file"
    assert settings.DEFAULT_WORKER == "async"
    assert settings.TASK_TTL == 86400
    assert settings.RESULT_TTL == 604800
    
    print("✓ Default settings loaded correctly")


def test_env_overrides():
    """Test environment variable overrides."""
    print("Testing environment variable overrides...")
    
    # Set test environment variables
    os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"
    os.environ["OMNIQ_WORKER_COUNT"] = "8"
    os.environ["OMNIQ_TASK_QUEUE_TYPE"] = "redis"
    os.environ["OMNIQ_DEBUG"] = "true"
    os.environ["OMNIQ_NATS_SERVERS"] = "nats://server1:4222,nats://server2:4222"
    
    try:
        # Test environment variable application
        settings = Settings()
        settings_with_env = EnvConfig.apply_env_overrides(settings)
        
        assert settings_with_env.LOG_LEVEL == "DEBUG"
        assert settings_with_env.WORKER_COUNT == 8
        assert settings_with_env.TASK_QUEUE_TYPE == "redis"
        assert settings_with_env.DEBUG == True
        assert settings_with_env.NATS_SERVERS == ["nats://server1:4222", "nats://server2:4222"]
        
        print("✓ Environment variable overrides working correctly")
    
    finally:
        # Clean up environment variables
        for key in ["OMNIQ_LOG_LEVEL", "OMNIQ_WORKER_COUNT", "OMNIQ_TASK_QUEUE_TYPE", 
                   "OMNIQ_DEBUG", "OMNIQ_NATS_SERVERS"]:
            if key in os.environ:
                del os.environ[key]


def test_yaml_config():
    """Test YAML configuration loading."""
    print("Testing YAML configuration loading...")
    
    # Create temporary YAML config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
LOG_LEVEL: WARNING
WORKER_COUNT: 6
TASK_QUEUE_TYPE: postgres
DEFAULT_WORKER: thread
TASK_TTL: 3600
DEBUG: true
POSTGRES_HOST: test-db
POSTGRES_PORT: 5433
        """
        f.write(yaml_content)
        yaml_file = f.name
    
    try:
        provider = ConfigProvider(yaml_file)
        yaml_config = provider.load_yaml_config(yaml_file)
        
        assert yaml_config["LOG_LEVEL"] == "WARNING"
        assert yaml_config["WORKER_COUNT"] == 6
        assert yaml_config["TASK_QUEUE_TYPE"] == "postgres"
        assert yaml_config["DEFAULT_WORKER"] == "thread"
        assert yaml_config["TASK_TTL"] == 3600
        assert yaml_config["DEBUG"] == True
        assert yaml_config["POSTGRES_HOST"] == "test-db"
        assert yaml_config["POSTGRES_PORT"] == 5433
        
        print("✓ YAML configuration loaded correctly")
    
    finally:
        os.unlink(yaml_file)


def test_config_precedence():
    """Test configuration precedence order."""
    print("Testing configuration precedence...")
    
    # Create YAML config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
LOG_LEVEL: WARNING
WORKER_COUNT: 6
TASK_QUEUE_TYPE: postgres
        """
        f.write(yaml_content)
        yaml_file = f.name
    
    try:
        # Set environment variable
        os.environ["OMNIQ_LOG_LEVEL"] = "ERROR"
        
        # Create provider with YAML config
        provider = ConfigProvider(yaml_file)
        
        # Set programmatic override
        provider.set_override("WORKER_COUNT", 12)
        
        # Get final settings
        settings = provider.get_settings()
        
        # Check precedence:
        # - LOG_LEVEL should be "ERROR" (env var overrides YAML)
        # - WORKER_COUNT should be 12 (programmatic override is highest)
        # - TASK_QUEUE_TYPE should be "postgres" (from YAML)
        
        assert settings.LOG_LEVEL == "ERROR"  # Environment variable
        assert settings.WORKER_COUNT == 12    # Programmatic override
        assert settings.TASK_QUEUE_TYPE == "postgres"  # YAML config
        
        print("✓ Configuration precedence working correctly")
    
    finally:
        os.unlink(yaml_file)
        if "OMNIQ_LOG_LEVEL" in os.environ:
            del os.environ["OMNIQ_LOG_LEVEL"]


def test_logging_config():
    """Test logging configuration."""
    print("Testing logging configuration...")
    
    # Create temporary directory for logs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Override log directory
        set_override("LOG_DIR", temp_dir)
        
        try:
            logging_config = get_logging_config()
            
            # Test library logger setup
            lib_logger = logging_config.setup_library_logger()
            assert lib_logger.name == "omniq"
            
            # Test event logger setup
            event_logger = logging_config.setup_event_logger()
            assert event_logger.name == "omniq.events"
            
            # Test log file paths
            expected_lib_path = str(Path(temp_dir) / "omniq.log")
            expected_event_path = str(Path(temp_dir) / "events.log")
            
            assert logging_config.library_file_path == expected_lib_path
            assert logging_config.event_file_path == expected_event_path
            
            print("✓ Logging configuration working correctly")
        
        finally:
            clear_overrides()


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    
    # Test valid configuration
    provider = ConfigProvider()
    errors = provider.validate_config()
    assert len(errors) == 0, f"Valid config should have no errors, got: {errors}"
    
    # Test invalid configuration
    provider.set_override("WORKER_COUNT", 0)  # Invalid: must be at least 1
    provider.set_override("TASK_TTL", -1)     # Invalid: must be non-negative
    provider.set_override("TASK_QUEUE_TYPE", "invalid")  # Invalid backend type
    
    errors = provider.validate_config()
    assert len(errors) >= 3, f"Expected at least 3 errors, got {len(errors)}: {errors}"
    
    # Check specific error messages
    error_messages = " ".join(errors)
    assert "WORKER_COUNT must be at least 1" in error_messages
    assert "TASK_TTL must be non-negative" in error_messages
    assert "TASK_QUEUE_TYPE must be one of" in error_messages
    
    print("✓ Configuration validation working correctly")


def test_config_template():
    """Test configuration template generation."""
    print("Testing configuration template generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        template_file = str(Path(temp_dir) / "config_template.yaml")
        
        provider = ConfigProvider()
        provider.save_config_template(template_file)
        
        # Check that template file was created
        assert Path(template_file).exists()
        
        # Check template content
        with open(template_file, 'r') as f:
            content = f.read()
        
        assert "# OmniQ Configuration Template" in content
        assert "# LOG_LEVEL: INFO" in content
        assert "# WORKER_COUNT: 4" in content
        assert "# TASK_QUEUE_TYPE: file" in content
        
        print("✓ Configuration template generation working correctly")


def test_global_functions():
    """Test global convenience functions."""
    print("Testing global convenience functions...")
    
    # Test getting settings
    settings = get_settings()
    assert isinstance(settings, Settings)
    
    # Test getting logging config
    logging_config = get_logging_config()
    assert isinstance(logging_config, LoggingConfig)
    
    # Test setting override
    set_override("WORKER_COUNT", 99)
    updated_settings = get_settings()
    assert updated_settings.WORKER_COUNT == 99
    
    # Test clearing overrides
    clear_overrides()
    default_settings = get_settings()
    assert default_settings.WORKER_COUNT == 4  # Back to default
    
    print("✓ Global convenience functions working correctly")


def run_all_tests():
    """Run all configuration tests."""
    print("=" * 60)
    print("Running OmniQ Configuration System Tests")
    print("=" * 60)
    
    tests = [
        test_default_settings,
        test_env_overrides,
        test_yaml_config,
        test_config_precedence,
        test_logging_config,
        test_config_validation,
        test_config_template,
        test_global_functions
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)