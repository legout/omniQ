"""
Advanced Configuration System for OmniQ.

This module provides comprehensive configuration loading and management capabilities:
- YAML file configuration support
- Dictionary-based configuration support  
- Type-validated config objects using msgspec.Struct
- Environment-specific configurations
- Configuration validation and merging
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from datetime import timedelta

import yaml
import msgspec
from msgspec import Struct

from .models.config import (
    BaseConfig, OmniQConfig, SQLiteConfig, FileConfig, PostgresConfig, 
    RedisConfig, NATSConfig, WorkerConfig, Settings, get_env_setting
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseConfig)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Advanced configuration loader with support for YAML files, dictionaries,
    and environment-specific configurations.
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self._config_cache: Dict[str, Any] = {}
        self._env_overrides: Dict[str, Any] = {}
        
    def load_yaml_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigValidationError: If YAML file is invalid or not found
        """
        config_path = Path(config_path)
        
        # Make path relative to config_dir if not absolute
        if not config_path.is_absolute():
            config_path = self.config_dir / config_path
            
        try:
            if not config_path.exists():
                raise ConfigValidationError(f"Configuration file not found: {config_path}")
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            if config_data is None:
                config_data = {}
                
            logger.info(f"Loaded configuration from {config_path}")
            return config_data
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error loading configuration from {config_path}: {e}")
    
    def load_environment_config(
        self, 
        environment: str, 
        base_config_name: str = "config"
    ) -> Dict[str, Any]:
        """
        Load environment-specific configuration.
        
        Loads base configuration and overlays environment-specific settings.
        
        Args:
            environment: Environment name (e.g., 'development', 'production')
            base_config_name: Base configuration file name (without extension)
            
        Returns:
            Merged configuration dictionary
        """
        # Load base configuration
        base_config_path = self.config_dir / f"{base_config_name}.yaml"
        base_config = {}
        
        if base_config_path.exists():
            base_config = self.load_yaml_config(base_config_path)
            
        # Load environment-specific configuration
        env_config_path = self.config_dir / f"{base_config_name}.{environment}.yaml"
        env_config = {}
        
        if env_config_path.exists():
            env_config = self.load_yaml_config(env_config_path)
            
        # Merge configurations (environment overrides base)
        merged_config = self.merge_configs(base_config, env_config)
        
        logger.info(f"Loaded environment configuration for '{environment}'")
        return merged_config
    
    def merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Base configuration dictionary
            
        Returns:
            Configuration with environment overrides applied
        """
        result = config.copy()
        
        # Apply OMNIQ_ prefixed environment variables
        for key, value in os.environ.items():
            if key.startswith('OMNIQ_'):
                config_key = key[6:].lower()  # Remove OMNIQ_ prefix and lowercase
                
                # Convert nested keys (e.g., OMNIQ_WORKER_MAX_WORKERS -> worker.max_workers)
                if '_' in config_key:
                    parts = config_key.split('_')
                    current = result
                    
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Convert value to appropriate type
                    current[parts[-1]] = self._convert_env_value(value)
                else:
                    result[config_key] = self._convert_env_value(value)
        
        return result
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def validate_config(self, config: Dict[str, Any], config_class: Type[T]) -> T:
        """
        Validate and convert configuration dictionary to typed config object.
        
        Args:
            config: Configuration dictionary
            config_class: Target configuration class (must inherit from BaseConfig)
            
        Returns:
            Validated configuration object
            
        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            return msgspec.convert(config, config_class)
        except msgspec.ValidationError as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error validating configuration: {e}")


class AdvancedConfigManager:
    """
    Advanced configuration manager providing unified access to all configuration methods.
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize advanced configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.loader = ConfigLoader(config_dir)
        self._cached_configs: Dict[str, BaseConfig] = {}
        self._current_config: Optional[BaseConfig] = None
        
    def from_yaml(
        self, 
        config_path: Union[str, Path], 
        config_class: Type[T] = OmniQConfig
    ) -> T:
        """
        Load and validate configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            config_class: Configuration class to validate against
            
        Returns:
            Validated configuration object
        """
        config_dict = self.loader.load_yaml_config(config_path)
        config_dict = self.loader.apply_env_overrides(config_dict)
        return self.loader.validate_config(config_dict, config_class)
    
    def from_dict(
        self, 
        config_dict: Dict[str, Any], 
        config_class: Type[T] = OmniQConfig,
        apply_env_overrides: bool = True
    ) -> T:
        """
        Load and validate configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            config_class: Configuration class to validate against
            apply_env_overrides: Whether to apply environment variable overrides
            
        Returns:
            Validated configuration object
        """
        if apply_env_overrides:
            config_dict = self.loader.apply_env_overrides(config_dict)
        return self.loader.validate_config(config_dict, config_class)
    
    def from_environment(
        self, 
        environment: str, 
        base_config_name: str = "config",
        config_class: Type[T] = OmniQConfig
    ) -> T:
        """
        Load environment-specific configuration.
        
        Args:
            environment: Environment name
            base_config_name: Base configuration file name
            config_class: Configuration class to validate against
            
        Returns:
            Validated configuration object
        """
        config_dict = self.loader.load_environment_config(environment, base_config_name)
        config_dict = self.loader.apply_env_overrides(config_dict)
        return self.loader.validate_config(config_dict, config_class)
    
    def merge_configs(self, *configs: BaseConfig) -> Dict[str, Any]:
        """
        Merge multiple configuration objects into a single dictionary.
        
        Args:
            *configs: Configuration objects to merge
            
        Returns:
            Merged configuration dictionary
        """
        result = {}
        
        for config in configs:
            config_dict = config.to_dict()
            result = self.loader.merge_configs(result, config_dict)
            
        return result
    
    def update_config(
        self, 
        base_config: T, 
        updates: Dict[str, Any]
    ) -> T:
        """
        Update configuration object with new values.
        
        Args:
            base_config: Base configuration object
            updates: Dictionary of updates to apply
            
        Returns:
            Updated configuration object
        """
        base_dict = base_config.to_dict()
        updated_dict = self.loader.merge_configs(base_dict, updates)
        return self.loader.validate_config(updated_dict, type(base_config))
    
    def get_component_config(
        self, 
        main_config: OmniQConfig, 
        component: str,
        config_class: Type[T]
    ) -> T:
        """
        Extract and validate component-specific configuration.
        
        Args:
            main_config: Main OmniQ configuration
            component: Component name (e.g., 'worker', 'task_queue')
            config_class: Component configuration class
            
        Returns:
            Component configuration object
        """
        component_config = getattr(main_config, component, None)
        
        if component_config is None:
            # Return default configuration
            return config_class()
        
        if isinstance(component_config, dict):
            return self.loader.validate_config(component_config, config_class)
        
        return component_config
    
    def set_config(self, config: BaseConfig) -> None:
        """
        Set the current configuration.
        
        Args:
            config: Configuration object to set as current
        """
        self._current_config = config
    
    def get_config(self) -> Optional[BaseConfig]:
        """
        Get the current configuration.
        
        Returns:
            Current configuration object or None if not set
        """
        return self._current_config
    
    def update_current_config(self, updates: Dict[str, Any]) -> None:
        """
        Update the current configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply to current config
            
        Raises:
            ValueError: If no current configuration is set
        """
        if self._current_config is None:
            raise ValueError("No current configuration set. Use set_config() first.")
        
        updated_config = self.update_config(self._current_config, updates)
        self._current_config = updated_config


# Global configuration manager instance
config_manager = AdvancedConfigManager()


# Convenience functions for common configuration operations
def load_config_from_yaml(
    config_path: Union[str, Path], 
    config_class: Type[T] = OmniQConfig
) -> T:
    """Load configuration from YAML file."""
    return config_manager.from_yaml(config_path, config_class)


def load_config_from_dict(
    config_dict: Dict[str, Any], 
    config_class: Type[T] = OmniQConfig
) -> T:
    """Load configuration from dictionary."""
    return config_manager.from_dict(config_dict, config_class)


def load_environment_config(
    environment: str, 
    config_class: Type[T] = OmniQConfig
) -> T:
    """Load environment-specific configuration."""
    return config_manager.from_environment(environment, config_class=config_class)


def merge_configurations(*configs: BaseConfig) -> Dict[str, Any]:
    """Merge multiple configuration objects."""
    return config_manager.merge_configs(*configs)


def merge_configs(base_config: BaseConfig, overlay_config: BaseConfig) -> BaseConfig:
    """
    Merge two configuration objects, with overlay taking precedence.
    
    Args:
        base_config: Base configuration
        overlay_config: Configuration to overlay on top
        
    Returns:
        BaseConfig: Merged configuration
    """
    return base_config.merge(overlay_config)


# Configuration factory functions for different components
def create_sqlite_config(**kwargs) -> SQLiteConfig:
    """Create SQLite configuration with validation."""
    return config_manager.from_dict(kwargs, SQLiteConfig)


def create_file_config(**kwargs) -> FileConfig:
    """Create file storage configuration with validation."""
    return config_manager.from_dict(kwargs, FileConfig)


def create_postgres_config(**kwargs) -> PostgresConfig:
    """Create PostgreSQL configuration with validation."""
    return config_manager.from_dict(kwargs, PostgresConfig)


def create_redis_config(**kwargs) -> RedisConfig:
    """Create Redis configuration with validation."""
    return config_manager.from_dict(kwargs, RedisConfig)


def create_nats_config(**kwargs) -> NATSConfig:
    """Create NATS configuration with validation."""
    return config_manager.from_dict(kwargs, NATSConfig)


def create_worker_config(**kwargs) -> WorkerConfig:
    """Create worker configuration with validation."""
    return config_manager.from_dict(kwargs, WorkerConfig)


def create_omniq_config(**kwargs) -> OmniQConfig:
    """Create main OmniQ configuration with validation."""
    return config_manager.from_dict(kwargs, OmniQConfig)


def create_config_manager(config: Optional[BaseConfig] = None) -> AdvancedConfigManager:
    """
    Create a new configuration manager instance.
    
    Args:
        config: Optional initial configuration to set
        
    Returns:
        AdvancedConfigManager instance
    """
    manager = AdvancedConfigManager()
    if config is not None:
        manager.set_config(config)
    return manager