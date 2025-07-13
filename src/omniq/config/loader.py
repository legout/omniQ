"""ConfigProvider and LoggingConfig for loading and validation."""

from __future__ import annotations

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from ..models.config import OmniQConfig
from .env import get_env_config, get_storage_config, is_development, is_production


class LoggingConfig:
    """Logging configuration and setup."""
    
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    
    @classmethod
    def setup_logging(
        cls,
        level: str = "INFO",
        format_string: Optional[str] = None,
        handlers: Optional[Dict[str, Any]] = None,
        disable_existing: bool = False
    ) -> None:
        """
        Setup logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED)
            format_string: Custom format string
            handlers: Custom handlers configuration
            disable_existing: Whether to disable existing loggers
        """
        if level.upper() == "DISABLED":
            logging.disable(logging.CRITICAL)
            return
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Use detailed format in development
        if format_string is None:
            format_string = cls.DETAILED_FORMAT if is_development() else cls.DEFAULT_FORMAT
        
        # Default handlers
        if handlers is None:
            handlers = {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": level.upper(),
                    "formatter": "default",
                    "stream": "ext://sys.stdout"
                }
            }
        
        # Logging configuration
        config = {
            "version": 1,
            "disable_existing_loggers": disable_existing,
            "formatters": {
                "default": {
                    "format": format_string
                }
            },
            "handlers": handlers,
            "loggers": {
                "omniq": {
                    "level": level.upper(),
                    "handlers": list(handlers.keys()),
                    "propagate": False
                }
            },
            "root": {
                "level": "WARNING",
                "handlers": list(handlers.keys())
            }
        }
        
        logging.config.dictConfig(config)
    
    @classmethod
    def setup_file_logging(
        cls,
        log_file: Union[str, Path],
        level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """Setup logging to file with rotation."""
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        handlers = {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level.upper(),
                "formatter": "default",
                "filename": str(log_file),
                "maxBytes": max_bytes,
                "backupCount": backup_count
            }
        }
        
        cls.setup_logging(level=level, handlers=handlers)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get logger instance with omniq prefix."""
        return logging.getLogger(f"omniq.{name}")


class ConfigProvider:
    """Configuration loading and validation."""
    
    def __init__(self):
        self._config_cache: Optional[OmniQConfig] = None
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> OmniQConfig:
        """Load configuration from dictionary."""
        try:
            # Handle nested configuration structure
            if "queue" in config_dict or "worker" in config_dict:
                return OmniQConfig(**config_dict)
            else:
                # Flat configuration - need to organize into components
                return self._organize_flat_config(config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}") from e
    
    def load_from_yaml(self, file_path: Union[str, Path]) -> OmniQConfig:
        """Load configuration from YAML file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, "r") as f:
                config_dict = yaml.safe_load(f)
            
            return self.load_from_dict(config_dict)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}") from e
    
    def load_from_env(self) -> OmniQConfig:
        """Load configuration from environment variables."""
        env_config = get_env_config()
        storage_config = get_storage_config()
        
        # Merge storage config into main config
        env_config.update(storage_config)
        
        return self._organize_flat_config(env_config)
    
    def load_default(self) -> OmniQConfig:
        """Load default configuration."""
        return OmniQConfig()
    
    def load_auto(
        self,
        config_file: Optional[Union[str, Path]] = None,
        use_env: bool = True,
        use_cache: bool = True
    ) -> OmniQConfig:
        """
        Auto-load configuration from multiple sources.
        
        Priority (highest to lowest):
        1. Explicit config file
        2. Environment variables (if use_env=True)
        3. Default configuration
        
        Args:
            config_file: Optional path to config file
            use_env: Whether to use environment variables
            use_cache: Whether to cache the configuration
        
        Returns:
            Loaded configuration
        """
        if use_cache and self._config_cache is not None:
            return self._config_cache
        
        # Start with default configuration
        config = self.load_default()
        
        # Override with environment variables
        if use_env:
            try:
                env_config = self.load_from_env()
                config = self._merge_configs(config, env_config)
            except Exception:
                pass  # Continue with defaults if env loading fails
        
        # Override with explicit config file
        if config_file:
            try:
                file_config = self.load_from_yaml(config_file)
                config = self._merge_configs(config, file_config)
            except Exception as e:
                raise ValueError(f"Failed to load config file {config_file}: {e}") from e
        
        # Cache the result
        if use_cache:
            self._config_cache = config
        
        return config
    
    def find_config_file(self) -> Optional[Path]:
        """Find configuration file in common locations."""
        possible_files = [
            "omniq.yaml",
            "omniq.yml", 
            ".omniq.yaml",
            ".omniq.yml",
            "config/omniq.yaml",
            "config/omniq.yml",
            Path.home() / ".omniq" / "config.yaml",
            Path.home() / ".omniq" / "config.yml",
        ]
        
        for file_path in possible_files:
            path = Path(file_path)
            if path.exists():
                return path
        
        return None
    
    def _organize_flat_config(self, flat_config: Dict[str, Any]) -> OmniQConfig:
        """Organize flat configuration into structured components."""
        from ..models.config import (
            QueueConfig, WorkerConfig, StorageConfig, 
            SerializationConfig, EventConfig
        )
        
        # Extract component configurations
        queue_config = QueueConfig()
        worker_config = WorkerConfig()
        storage_config = StorageConfig()
        serialization_config = SerializationConfig()
        event_config = EventConfig()
        
        # Map flat config to components
        config_mapping = {
            # Queue config
            "TASK_QUEUE_TYPE": ("queue", "backend_type"),
            "DEFAULT_QUEUE_NAME": ("queue", "name"),
            "QUEUE_MAX_SIZE": ("queue", "max_size"),
            "QUEUE_PRIORITY_ENABLED": ("queue", "priority_enabled"),
            
            # Worker config
            "DEFAULT_WORKER": ("worker", "worker_type"),
            "WORKER_POOL_SIZE": ("worker", "pool_size"),
            "TASK_TIMEOUT": ("worker", "task_timeout"),
            "QUEUE_POLLING_INTERVAL": ("worker", "polling_interval"),
            
            # Storage config
            "RESULT_STORAGE_TYPE": ("storage", "backend_type"),
            "STORAGE_COMPRESSION": ("storage", "compression"),
            "STORAGE_POOL_SIZE": ("storage", "pool_size"),
            
            # Serialization config
            "SERIALIZATION_PRIMARY": ("serialization", "primary_serializer"),
            "SERIALIZATION_FALLBACK": ("serialization", "fallback_serializer"),
            "SERIALIZATION_COMPRESSION": ("serialization", "compress"),
            
            # Event config
            "EVENT_LOGGING_ENABLED": ("events", "enabled"),
            "EVENT_STORAGE_TYPE": ("events", "storage_backend"),
            "EVENT_BATCH_SIZE": ("events", "batch_size"),
        }
        
        # Apply mappings
        components = {
            "queue": queue_config,
            "worker": worker_config,
            "storage": storage_config,
            "serialization": serialization_config,
            "events": event_config,
        }
        
        for flat_key, (component, attr) in config_mapping.items():
            if flat_key in flat_config:
                value = flat_config[flat_key]
                setattr(components[component], attr, value)
        
        # Create main config
        main_config = {
            "queue": components["queue"],
            "worker": components["worker"],
            "storage": components["storage"],
            "serialization": components["serialization"],
            "events": components["events"],
        }
        
        # Add main-level settings
        if "LOG_LEVEL" in flat_config:
            main_config["log_level"] = flat_config["LOG_LEVEL"]
        if "DEBUG" in flat_config:
            main_config["debug"] = flat_config["DEBUG"]
        
        return OmniQConfig(**main_config)
    
    def _merge_configs(self, base: OmniQConfig, override: OmniQConfig) -> OmniQConfig:
        """Merge two configurations, with override taking precedence."""
        # For now, just return the override config
        # In a full implementation, we'd merge the individual components
        return override


# Global config provider instance
config_provider = ConfigProvider()