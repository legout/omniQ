"""
Configuration-Based Usage Example for OmniQ

This example demonstrates the various ways to configure OmniQ components:
1. Using config objects (type-validated)
2. Using dictionaries
3. Loading from YAML files
4. Environment variable overrides

Run this example to see how different configuration methods work.
"""

import os
import datetime as dt
from pathlib import Path

# Import OmniQ components
from omniq import OmniQ
from omniq.models import FileTaskQueueConfig, SQLiteResultStorageConfig
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage


def example_task(name: str, multiplier: int = 1) -> str:
    """Example task function for demonstration."""
    result = f"Hello {name}!" * multiplier
    print(f"Task executed: {result}")
    return result


def config_objects_example():
    """Example 1: Using config objects for type-validated configuration."""
    print("\n=== Example 1: Config Objects (Type-Validated) ===")
    
    # Create components using specific config classes
    queue = FileTaskQueue.from_config(
        FileTaskQueueConfig(
            project_name="config_example",
            base_dir="./temp/config_objects",
            queues=["high", "medium", "low"]
        )
    )
    
    result_store = SQLiteResultStorage.from_config(
        SQLiteResultStorageConfig(
            project_name="config_example",
            base_dir="./temp/config_objects"
        )
    )
    
    # Create OmniQ instance with configured components
    oq = OmniQ(
        project_name="config_example",
        task_queue=queue,
        result_store=result_store
    )
    
    print("✓ Created OmniQ with config objects")
    
    # Start worker and enqueue a task
    with oq:
        oq.start_worker()
        
        task_id = oq.enqueue(
            func=example_task,
            func_args={"name": "Config Objects", "multiplier": 2},
            queue_name="high"
        )
        
        print(f"✓ Enqueued task: {task_id}")
        
        # Wait a moment for task to complete
        import time
        time.sleep(1)
        
        # Get result
        result = oq.get_result(task_id)
        print(f"✓ Task result: {result}")
        
        oq.stop_worker()


def dictionary_config_example():
    """Example 2: Using dictionary-based configuration."""
    print("\n=== Example 2: Dictionary Configuration ===")
    
    # Define configuration as dictionary
    config = {
        "project_name": "dict_example",
        "task_queue": {
            "type": "file",
            "config": {
                "base_dir": "./temp/dict_config",
                "queues": ["high", "medium", "low"]
            }
        },
        "result_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./temp/dict_config"
            }
        },
        "worker": {
            "type": "thread_pool",
            "config": {
                "max_workers": 5
            }
        }
    }
    
    # Create OmniQ from dictionary
    oq = OmniQ.from_dict(config)
    print("✓ Created OmniQ from dictionary config")
    
    # Start worker and enqueue a task
    with oq:
        oq.start_worker()
        
        task_id = oq.enqueue(
            func=example_task,
            func_args={"name": "Dictionary Config", "multiplier": 1},
            queue_name="medium"
        )
        
        print(f"✓ Enqueued task: {task_id}")
        
        # Wait a moment for task to complete
        import time
        time.sleep(1)
        
        # Get result
        result = oq.get_result(task_id)
        print(f"✓ Task result: {result}")
        
        oq.stop_worker()


def yaml_config_example():
    """Example 3: Loading configuration from YAML file."""
    print("\n=== Example 3: YAML File Configuration ===")
    
    # Get the path to the config.yaml file in this directory
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        print("⚠ config.yaml not found, creating a temporary one...")
        
        # Create a temporary config file
        temp_config = """
project_name: yaml_example

task_queue:
  type: file
  config:
    base_dir: ./temp/yaml_config
    queues:
      - high
      - medium
      - low

result_store:
  type: sqlite
  config:
    base_dir: ./temp/yaml_config

worker:
  type: thread_pool
  config:
    max_workers: 8
"""
        with open(config_path, 'w') as f:
            f.write(temp_config)
    
    # Load OmniQ configuration from YAML file
    oq = OmniQ.from_config_file(str(config_path))
    print("✓ Created OmniQ from YAML config file")
    
    # Start worker and enqueue a task
    with oq:
        oq.start_worker()
        
        task_id = oq.enqueue(
            func=example_task,
            func_args={"name": "YAML Config", "multiplier": 3},
            queue_name="low"
        )
        
        print(f"✓ Enqueued task: {task_id}")
        
        # Wait a moment for task to complete
        import time
        time.sleep(1)
        
        # Get result
        result = oq.get_result(task_id)
        print(f"✓ Task result: {result}")
        
        oq.stop_worker()


def environment_variables_example():
    """Example 4: Using environment variables for configuration overrides."""
    print("\n=== Example 4: Environment Variable Overrides ===")
    
    # Set environment variables (these would typically be set externally)
    os.environ["OMNIQ_TASK_QUEUE_TYPE"] = "file"
    os.environ["OMNIQ_RESULT_STORAGE_TYPE"] = "sqlite"
    os.environ["OMNIQ_MAX_WORKERS"] = "12"
    os.environ["OMNIQ_TASK_QUEUE_URL"] = "./temp/env_config"
    os.environ["OMNIQ_RESULT_STORAGE_URL"] = "./temp/env_config"
    
    print("✓ Set environment variables:")
    for key, value in os.environ.items():
        if key.startswith("OMNIQ_"):
            print(f"  {key}={value}")
    
    # Create OmniQ with environment variable configuration
    # Note: This would use the environment variables for configuration
    config = {
        "project_name": "env_example",
        "task_queue": {
            "type": "file",
            "config": {
                "base_dir": "./temp/env_config",
                "queues": ["high", "medium", "low"]
            }
        },
        "result_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./temp/env_config"
            }
        }
    }
    
    oq = OmniQ.from_dict(config)
    print("✓ Created OmniQ with environment variable overrides")
    
    # Start worker and enqueue a task
    with oq:
        oq.start_worker()
        
        task_id = oq.enqueue(
            func=example_task,
            func_args={"name": "Environment Config", "multiplier": 1},
            queue_name="high"
        )
        
        print(f"✓ Enqueued task: {task_id}")
        
        # Wait a moment for task to complete
        import time
        time.sleep(1)
        
        # Get result
        result = oq.get_result(task_id)
        print(f"✓ Task result: {result}")
        
        oq.stop_worker()
    
    # Clean up environment variables
    for key in list(os.environ.keys()):
        if key.startswith("OMNIQ_"):
            del os.environ[key]


def mixed_configuration_example():
    """Example 5: Mixing different configuration methods."""
    print("\n=== Example 5: Mixed Configuration Methods ===")
    
    # Use config objects for some components
    queue_config = FileTaskQueueConfig(
        project_name="mixed_example",
        base_dir="./temp/mixed_config",
        queues=["priority", "normal"]
    )
    
    queue = FileTaskQueue.from_config(queue_config)
    
    # Use dictionary for result storage
    result_store_dict = {
        "project_name": "mixed_example",
        "base_dir": "./temp/mixed_config"
    }
    
    result_store = SQLiteResultStorage.from_dict(result_store_dict)
    
    # Create OmniQ with mixed configuration
    oq = OmniQ(
        project_name="mixed_example",
        task_queue=queue,
        result_store=result_store
    )
    
    print("✓ Created OmniQ with mixed configuration methods")
    
    # Start worker and enqueue a task
    with oq:
        oq.start_worker()
        
        task_id = oq.enqueue(
            func=example_task,
            func_args={"name": "Mixed Config", "multiplier": 2},
            queue_name="priority"
        )
        
        print(f"✓ Enqueued task: {task_id}")
        
        # Wait a moment for task to complete
        import time
        time.sleep(1)
        
        # Get result
        result = oq.get_result(task_id)
        print(f"✓ Task result: {result}")
        
        oq.stop_worker()


def cleanup_temp_files():
    """Clean up temporary files created during examples."""
    import shutil
    
    temp_dirs = [
        "./temp/config_objects",
        "./temp/dict_config", 
        "./temp/yaml_config",
        "./temp/env_config",
        "./temp/mixed_config"
    ]
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up {temp_dir}")


def main():
    """Run all configuration examples."""
    print("OmniQ Configuration-Based Usage Examples")
    print("=" * 50)
    
    try:
        # Run all examples
        config_objects_example()
        dictionary_config_example()
        yaml_config_example()
        environment_variables_example()
        mixed_configuration_example()
        
        print("\n" + "=" * 50)
        print("✅ All configuration examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temporary files
        print("\nCleaning up temporary files...")
        cleanup_temp_files()


if __name__ == "__main__":
    main()