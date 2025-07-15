"""
Advanced Configuration Example for OmniQ

This example demonstrates the advanced configuration system with:
- YAML configuration loading
- Dictionary-based configuration
- Environment variable overlays
- Deep merging of configurations
- Type validation with msgspec.Struct
- Runtime configuration updates
"""

import os
import tempfile
from pathlib import Path

from omniq.config import (
    ConfigLoader,
    AdvancedConfigManager,
    load_config_from_yaml,
    load_config_from_dict,
    merge_configurations,
    create_config_manager
)
from omniq.models.config import OmniQConfig, WorkerConfig, SQLiteConfig


def demo_basic_config_loading():
    """Demonstrate basic configuration loading from different sources."""
    print("=== Basic Configuration Loading ===")
    
    # 1. Load from dictionary
    config_dict = {
        "project_name": "my_project",
        "default_queue": "high_priority",
        "log_level": "DEBUG",
        "worker": {
            "worker_type": "thread",
            "max_workers": 4,
            "task_timeout": 120.0
        }
    }
    
    config = load_config_from_dict(config_dict)
    print(f"Config from dict: {config}")
    print(f"Project name: {config.project_name}")
    print(f"Default queue: {config.default_queue}")
    print(f"Log level: {config.log_level}")
    if config.worker:
        print(f"Worker max_workers: {config.worker.get('max_workers', 'N/A')}")
    print()


def demo_yaml_config_loading():
    """Demonstrate YAML configuration loading."""
    print("=== YAML Configuration Loading ===")
    
    # Create temporary YAML config file
    yaml_content = """
project_name: "yaml_project"
default_queue: "yaml_queue"
log_level: "INFO"
worker:
  worker_type: "process"
  max_workers: 8
  task_timeout: 300.0
  queues:
    - "high"
    - "medium"
    - "low"
task_queue:
  type: "sqlite"
  database_path: "yaml_tasks.db"
  timeout: 30.0
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name
    
    try:
        config = load_config_from_yaml(yaml_path)
        print(f"Config from YAML: {config}")
        print(f"Project name: {config.project_name}")
        print(f"Default queue: {config.default_queue}")
        if config.task_queue:
            print(f"Database path: {config.task_queue.get('database_path', 'N/A')}")
        print()
    finally:
        os.unlink(yaml_path)


def demo_environment_config():
    """Demonstrate environment variable configuration."""
    print("=== Environment Variable Configuration ===")
    
    # Set environment variables
    os.environ["OMNIQ_PROJECT_NAME"] = "env_project"
    os.environ["OMNIQ_LOG_LEVEL"] = "WARNING"
    os.environ["OMNIQ_DEFAULT_QUEUE"] = "env_queue"
    
    try:
        config = OmniQConfig.from_env()
        print(f"Config from env: {config}")
        print(f"Project name: {config.project_name}")
        print(f"Log level: {config.log_level}")
        print(f"Default queue: {config.default_queue}")
        print()
    finally:
        # Clean up environment variables
        for key in ["OMNIQ_PROJECT_NAME", "OMNIQ_LOG_LEVEL", "OMNIQ_DEFAULT_QUEUE"]:
            os.environ.pop(key, None)


def demo_config_merging():
    """Demonstrate configuration merging."""
    print("=== Configuration Merging ===")
    
    # Base configuration
    base_config = load_config_from_dict({
        "project_name": "base_project",
        "log_level": "INFO",
        "worker": {
            "worker_type": "async",
            "max_workers": 4,
            "task_timeout": 300.0
        },
        "task_queue": {
            "type": "sqlite",
            "database_path": "base.db"
        }
    })
    
    # Development overrides
    dev_config = load_config_from_dict({
        "log_level": "DEBUG",
        "worker": {
            "max_workers": 2  # Fewer workers for dev
        },
        "task_queue": {
            "database_path": "dev.db"
        }
    })
    
    # Production overrides
    prod_config = load_config_from_dict({
        "log_level": "ERROR",
        "worker": {
            "max_workers": 16,  # More workers for prod
            "task_timeout": 600.0
        },
        "task_queue": {
            "database_path": "prod.db"
        }
    })
    
    # Merge configurations using the merge_configurations function
    dev_final_dict = merge_configurations(base_config, dev_config)
    prod_final_dict = merge_configurations(base_config, prod_config)
    
    print(f"Dev config dict: {dev_final_dict}")
    print(f"Prod config dict: {prod_final_dict}")
    
    # Convert back to structured configs
    dev_structured = load_config_from_dict(dev_final_dict)
    prod_structured = load_config_from_dict(prod_final_dict)
    
    print(f"Dev log level: {dev_structured.log_level}")
    print(f"Prod log level: {prod_structured.log_level}")
    print()


def demo_advanced_config_manager():
    """Demonstrate the AdvancedConfigManager for runtime updates."""
    print("=== Advanced Configuration Manager ===")
    
    # Start with base configuration
    manager = AdvancedConfigManager()
    
    # Load initial config
    initial_config = load_config_from_dict({
        "project_name": "runtime_project",
        "log_level": "INFO",
        "worker": {
            "worker_type": "thread",
            "max_workers": 4,
            "task_timeout": 300.0
        }
    })
    
    manager.set_config(initial_config)
    print(f"Initial config: {manager.get_config()}")
    
    # Runtime update - increase worker capacity
    worker_update = {
        "worker": {
            "max_workers": 8,
            "task_timeout": 600.0
        }
    }
    
    manager.update_current_config(worker_update)
    updated_config = manager.get_config()
    print(f"After worker update: {updated_config}")
    if updated_config and isinstance(updated_config, OmniQConfig) and updated_config.worker:
        print(f"Updated max_workers: {updated_config.worker.get('max_workers', 'N/A')}")
    print()
    
    # Another update - change logging
    logging_update = {
        "log_level": "DEBUG"
    }
    
    manager.update_current_config(logging_update)
    final_config = manager.get_config()
    print(f"After logging update: {final_config}")
    if final_config and isinstance(final_config, OmniQConfig):
        print(f"Log level: {final_config.log_level}")
    print()


def demo_structured_configs():
    """Demonstrate working with structured configuration classes."""
    print("=== Structured Configuration Classes ===")
    
    # Create a WorkerConfig directly
    worker_config = WorkerConfig(
        worker_type="process",
        max_workers=8,
        queues=["high", "medium", "low"],
        task_timeout=600.0,
        max_retries=5
    )
    
    print(f"Worker config: {worker_config}")
    print(f"Worker type: {worker_config.worker_type}")
    print(f"Max workers: {worker_config.max_workers}")
    print(f"Queues: {worker_config.queues}")
    
    # Convert to dict and back
    worker_dict = worker_config.to_dict()
    print(f"As dict: {worker_dict}")
    
    worker_from_dict = WorkerConfig.from_dict(worker_dict)
    print(f"From dict: {worker_from_dict}")
    
    # Create SQLite config
    sqlite_config = SQLiteConfig(
        database_path="structured.db",
        timeout=60.0,
        cache_size=-128000  # 128MB
    )
    
    print(f"SQLite config: {sqlite_config}")
    print(f"Database path: {sqlite_config.database_path}")
    print(f"Cache size: {sqlite_config.cache_size}")
    print()


def demo_config_validation():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation ===")
    
    try:
        # This should work
        valid_config = OmniQConfig(
            project_name="valid_project",
            log_level="INFO",
            default_queue="default"
        )
        print(f"Valid config created: {valid_config}")
        
        # Test with flexible data types (msgspec handles conversion)
        config_dict = {
            "project_name": "test",
            "log_level": "DEBUG",
            "disable_logging": False
        }
        
        flexible_config = load_config_from_dict(config_dict)
        print(f"Flexible config: {flexible_config}")
        
    except Exception as e:
        print(f"Validation error: {e}")
    
    print()


def demo_factory_functions():
    """Demonstrate factory functions for easy config creation."""
    print("=== Factory Functions ===")
    
    # Create config manager with default settings
    manager = create_config_manager()
    print(f"Default manager: {manager}")
    
    # Create with custom config
    custom_config = OmniQConfig(
        project_name="factory_project",
        log_level="DEBUG"
    )
    
    custom_manager = create_config_manager(custom_config)
    print(f"Custom manager: {custom_manager}")
    print(f"Custom config: {custom_manager.get_config()}")
    print()


def demo_integration_example():
    """Demonstrate a complete integration example."""
    print("=== Integration Example ===")
    
    # Simulate a real-world scenario
    # 1. Load base config from YAML
    base_yaml = """
project_name: "production_app"
default_queue: "default"
log_level: "INFO"
worker:
  worker_type: "process"
  max_workers: 4
  task_timeout: 300.0
  queues: ["default", "high", "low"]
task_queue:
  type: "sqlite"
  database_path: "app.db"
  timeout: 30.0
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(base_yaml)
        yaml_path = f.name
    
    try:
        # Load base config
        base_config = load_config_from_yaml(yaml_path)
        
        # Create environment-specific overrides as a config object
        env_overrides = load_config_from_dict({
            "log_level": "DEBUG",
            "worker": {
                "max_workers": 8
            }
        })
        
        # Merge configurations using the merge_configurations function
        final_config_dict = merge_configurations(base_config, env_overrides)
        final_config = load_config_from_dict(final_config_dict)
        
        # Use with manager for runtime updates
        manager = AdvancedConfigManager()
        manager.set_config(final_config)
        
        print(f"Final integrated config: {manager.get_config()}")
        
        # Simulate runtime update
        runtime_update = {
            "worker": {
                "task_timeout": 600.0
            }
        }
        
        manager.update_current_config(runtime_update)
        updated = manager.get_config()
        
        print(f"After runtime update: {updated}")
        if updated and isinstance(updated, OmniQConfig) and updated.worker:
            print(f"Updated timeout: {updated.worker.get('task_timeout', 'N/A')}")
        
    finally:
        os.unlink(yaml_path)
    
    print()


if __name__ == "__main__":
    print("OmniQ Advanced Configuration System Demo")
    print("=" * 50)
    
    demo_basic_config_loading()
    demo_yaml_config_loading()
    demo_environment_config()
    demo_config_merging()
    demo_advanced_config_manager()
    demo_structured_configs()
    demo_config_validation()
    demo_factory_functions()
    demo_integration_example()
    
    print("Demo completed successfully!")