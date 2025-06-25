# src/omniq/config/loader.py
"""Configuration loader for OmniQ."""

import os
import yaml
from typing import Dict, Any, Type, TypeVar

from omniq.models.config import OmniQConfig, TaskQueueConfig, ResultStoreConfig, EventStoreConfig, WorkerConfig

T = TypeVar('T')

def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def create_config_from_dict(config_dict: Dict[str, Any], config_class: Type[T]) -> T:
    """Create configuration object from dictionary."""
    return config_class(**config_dict)

def load_omniq_config(config_path: str) -> OmniQConfig:
    """Load OmniQ configuration from YAML file."""
    config_dict = load_yaml_config(config_path)
    
    # Process task queue config
    task_queue_dict = config_dict.get("task_queue", {})
    task_queue_config = TaskQueueConfig(
        type=task_queue_dict.get("type", "memory"),
        config=task_queue_dict.get("config", {})
    )
    
    # Process result store config
    result_store_config = None
    if "result_store" in config_dict:
        result_store_dict = config_dict.get("result_store", {})
        result_store_config = ResultStoreConfig(
            type=result_store_dict.get("type", "memory"),
            config=result_store_dict.get("config", {})
        )
    
    # Process event store config
    event_store_config = None
    if "event_store" in config_dict:
        event_store_dict = config_dict.get("event_store", {})
        event_store_config = EventStoreConfig(
            type=event_store_dict.get("type", "memory"),
            config=event_store_dict.get("config", {})
        )
    
    # Process worker config
    worker_config = None
    if "worker" in config_dict:
        worker_dict = config_dict.get("worker", {})
        worker_config = WorkerConfig(
            type=worker_dict.get("type", "thread_pool"),
            config=worker_dict.get("config", {})
        )
    
    return OmniQConfig(
        project_name=config_dict.get("project_name", "omniq"),
        task_queue=task_queue_config,
        result_store=result_store_config,
        event_store=event_store_config,
        worker=worker_config
    )