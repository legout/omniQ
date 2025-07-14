"""
Configuration system for OmniQ library.

This module provides a comprehensive configuration system supporting:
- Default settings constants
- Environment variable overrides with OMNIQ_ prefix
- YAML configuration files
- Programmatic configuration
- Logging configuration management
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import msgspec
import yaml


class Settings(msgspec.Struct):
    """
    Default configuration settings for OmniQ library.
    
    Settings do not use OMNIQ_ prefix - that's only for environment variables.
    """
    
    # Core directories
    BASE_DIR: str = str(Path.home() / ".omniq")
    CONFIG_DIR: str = str(Path.home() / ".omniq" / "config")
    DATA_DIR: str = str(Path.home() / ".omniq" / "data")
    LOG_DIR: str = str(Path.home() / ".omniq" / "logs")
    CACHE_DIR: str = str(Path.home() / ".omniq" / "cache")
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_ENABLED: bool = True
    LOG_CONSOLE_ENABLED: bool = True
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    
    # Backend configuration
    TASK_QUEUE_TYPE: str = "file"
    RESULT_STORAGE_TYPE: str = "file"
    EVENT_STORAGE_TYPE: str = "file"
    
    # Worker configuration
    DEFAULT_WORKER: str = "async"
    WORKER_COUNT: int = 4
    WORKER_TIMEOUT: int = 300  # 5 minutes
    
    # Task configuration
    TASK_TTL: int = 86400  # 24 hours in seconds
    TASK_RETRY_COUNT: int = 3
    TASK_RETRY_DELAY: int = 60  # 1 minute
    
    # Storage configuration
    RESULT_TTL: int = 604800  # 7 days in seconds
    EVENT_TTL: int = 2592000  # 30 days in seconds
    STORAGE_BATCH_SIZE: int = 100
    
    # File backend specific
    FILE_QUEUE_DIR: str = str(Path.home() / ".omniq" / "data" / "queues")
    FILE_RESULT_DIR: str = str(Path.home() / ".omniq" / "data" / "results")
    FILE_EVENT_DIR: str = str(Path.home() / ".omniq" / "data" / "events")
    FILE_SYNC_INTERVAL: int = 5  # seconds
    
    # SQLite backend specific
    SQLITE_DB_PATH: str = str(Path.home() / ".omniq" / "data" / "omniq.db")
    SQLITE_POOL_SIZE: int = 10
    SQLITE_TIMEOUT: int = 30
    
    # PostgreSQL backend specific
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "omniq"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DATABASE: str = "omniq"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_TIMEOUT: int = 30
    
    # Redis backend specific
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_POOL_SIZE: int = 10
    REDIS_TIMEOUT: int = 30
    
    # NATS backend specific
    NATS_SERVERS: List[str] = msgspec.field(default_factory=lambda: ["nats://localhost:4222"])
    NATS_TIMEOUT: int = 30
    NATS_MAX_RECONNECT: int = 10
    
    # Monitoring configuration
    METRICS_ENABLED: bool = False
    METRICS_PORT: int = 8080
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_PORT: int = 8081
    
    # Development configuration
    DEBUG: bool = False
    DEVELOPMENT_MODE: bool = False
    AUTO_RELOAD: bool = False


class LoggingConfig(msgspec.Struct):
    """
    Logging configuration for OmniQ library.
    
    Manages two separate loggers:
    - Library logger: 'omniq' for library operations
    - Event logger: 'omniq.events' for task event logging
    """
    
    # Library logger configuration
    library_level: str = "INFO"
    library_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    library_file_enabled: bool = True
    library_console_enabled: bool = True
    library_file_path: str = str(Path.home() / ".omniq" / "logs" / "omniq.log")
    
    # Event logger configuration
    event_level: str = "INFO"
    event_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    event_file_enabled: bool = True
    event_console_enabled: bool = False
    event_file_path: str = str(Path.home() / ".omniq" / "logs" / "events.log")
    
    # File rotation settings
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 5
    
    def setup_library_logger(self) -> logging.Logger:
        """Setup the main library logger."""
        logger = logging.getLogger("omniq")
        logger.setLevel(getattr(logging, self.library_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        if self.library_file_enabled:
            os.makedirs(os.path.dirname(self.library_file_path), exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.library_file_path,
                maxBytes=self.file_max_size,
                backupCount=self.file_backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.library_format))
            logger.addHandler(file_handler)
        
        # Console handler
        if self.library_console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(self.library_format))
            logger.addHandler(console_handler)
        
        return logger
    
    def setup_event_logger(self) -> logging.Logger:
        """Setup the event logger for task lifecycle events."""
        logger = logging.getLogger("omniq.events")
        logger.setLevel(getattr(logging, self.event_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        if self.event_file_enabled:
            os.makedirs(os.path.dirname(self.event_file_path), exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.event_file_path,
                maxBytes=self.file_max_size,
                backupCount=self.file_backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.event_format))
            logger.addHandler(file_handler)
        
        # Console handler
        if self.event_console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(self.event_format))
            logger.addHandler(console_handler)
        
        return logger


class EnvConfig:
    """
    Environment variable configuration handler.
    
    Handles environment variables with OMNIQ_ prefix for overriding settings.
    """
    
    @classmethod
    def _convert_value(cls, value: str, field_type: type) -> Any:
        """Convert string environment variable to appropriate type."""
        if field_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif field_type == int:
            return int(value)
        elif field_type == float:
            return float(value)
        elif field_type == list:
            # Handle comma-separated lists
            return [item.strip() for item in value.split(",") if item.strip()]
        else:
            return value
    
    @classmethod
    def apply_env_overrides(cls, settings: Settings) -> Settings:
        """Apply environment variable overrides to settings."""
        # Get all Settings fields and their types
        settings_dict = msgspec.structs.asdict(settings)
        field_info = msgspec.structs.fields(Settings)
        
        # Create a mapping of field names to their types
        field_types = {field.name: field.type for field in field_info}
        
        # Check for environment variable overrides
        for field_name, current_value in settings_dict.items():
            env_var_name = f"OMNIQ_{field_name}"
            env_value = os.environ.get(env_var_name)
            
            if env_value is not None:
                try:
                    field_type = field_types.get(field_name, str)
                    # Handle generic types like List[str]
                    if hasattr(field_type, '__origin__'):
                        if field_type.__origin__ is list:
                            field_type = list
                    
                    converted_value = cls._convert_value(env_value, field_type)
                    settings_dict[field_name] = converted_value
                except (ValueError, TypeError) as e:
                    # Log warning but don't fail
                    logger = logging.getLogger("omniq")
                    logger.warning(f"Failed to convert env var {env_var_name}={env_value}: {e}")
        
        # Create new Settings instance with updated values
        return Settings(**settings_dict)


class ConfigProvider:
    """
    Central configuration provider for OmniQ library.
    
    Loads configuration from multiple sources in precedence order:
    1. Programmatic overrides (highest priority)
    2. Environment variables (OMNIQ_ prefix)
    3. YAML configuration file
    4. Default settings (lowest priority)
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self._settings: Optional[Settings] = None
        self._logging_config: Optional[LoggingConfig] = None
        self._overrides: Dict[str, Any] = {}
    
    def load_yaml_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(config_file)
        if not config_path.exists():
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            return config_data
        except Exception as e:
            logger = logging.getLogger("omniq")
            logger.error(f"Failed to load YAML config from {config_file}: {e}")
            return {}
    
    def get_settings(self) -> Settings:
        """Get current settings with all overrides applied."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        if self._logging_config is None:
            self._logging_config = self._load_logging_config()
        return self._logging_config
    
    def _load_settings(self) -> Settings:
        """Load settings from all sources."""
        # Start with defaults
        settings = Settings()
        
        # Apply YAML configuration if provided
        if self.config_file:
            yaml_config = self.load_yaml_config(self.config_file)
            if yaml_config:
                settings_dict = msgspec.structs.asdict(settings)
                # Update with YAML values
                for key, value in yaml_config.items():
                    if key in settings_dict:
                        settings_dict[key] = value
                settings = Settings(**settings_dict)
        
        # Apply environment variable overrides
        settings = EnvConfig.apply_env_overrides(settings)
        
        # Apply programmatic overrides
        if self._overrides:
            settings_dict = msgspec.structs.asdict(settings)
            settings_dict.update(self._overrides)
            settings = Settings(**settings_dict)
        
        return settings
    
    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration."""
        settings = self.get_settings()
        
        # Create logging config from settings
        logging_config = LoggingConfig(
            library_level=settings.LOG_LEVEL,
            library_format=settings.LOG_FORMAT,
            library_file_enabled=settings.LOG_FILE_ENABLED,
            library_console_enabled=settings.LOG_CONSOLE_ENABLED,
            library_file_path=str(Path(settings.LOG_DIR) / "omniq.log"),
            event_file_path=str(Path(settings.LOG_DIR) / "events.log"),
            file_max_size=settings.LOG_FILE_MAX_SIZE,
            file_backup_count=settings.LOG_FILE_BACKUP_COUNT
        )
        
        return logging_config
    
    def set_override(self, key: str, value: Any) -> None:
        """Set a programmatic override for a setting."""
        self._overrides[key] = value
        # Clear cached settings to force reload
        self._settings = None
        self._logging_config = None
    
    def clear_overrides(self) -> None:
        """Clear all programmatic overrides."""
        self._overrides.clear()
        self._settings = None
        self._logging_config = None
    
    def reload_config(self) -> None:
        """Reload configuration from all sources."""
        self._settings = None
        self._logging_config = None
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return list of errors."""
        errors = []
        settings = self.get_settings()
        
        # Validate worker count
        if settings.WORKER_COUNT < 1:
            errors.append("WORKER_COUNT must be at least 1")
        
        # Validate TTL values
        if settings.TASK_TTL < 0:
            errors.append("TASK_TTL must be non-negative")
        if settings.RESULT_TTL < 0:
            errors.append("RESULT_TTL must be non-negative")
        if settings.EVENT_TTL < 0:
            errors.append("EVENT_TTL must be non-negative")
        
        # Validate backend types
        valid_backends = ["file", "memory", "sqlite", "postgres", "redis", "nats"]
        if settings.TASK_QUEUE_TYPE not in valid_backends:
            errors.append(f"TASK_QUEUE_TYPE must be one of: {valid_backends}")
        if settings.RESULT_STORAGE_TYPE not in valid_backends:
            errors.append(f"RESULT_STORAGE_TYPE must be one of: {valid_backends}")
        if settings.EVENT_STORAGE_TYPE not in valid_backends:
            errors.append(f"EVENT_STORAGE_TYPE must be one of: {valid_backends}")
        
        # Validate worker type
        valid_workers = ["async", "thread", "process", "gevent"]
        if settings.DEFAULT_WORKER not in valid_workers:
            errors.append(f"DEFAULT_WORKER must be one of: {valid_workers}")
        
        # Validate timeouts
        if settings.WORKER_TIMEOUT < 1:
            errors.append("WORKER_TIMEOUT must be at least 1 second")
        
        # Validate retry settings
        if settings.TASK_RETRY_COUNT < 0:
            errors.append("TASK_RETRY_COUNT must be non-negative")
        if settings.TASK_RETRY_DELAY < 0:
            errors.append("TASK_RETRY_DELAY must be non-negative")
        
        # Validate ports
        if not (1 <= settings.METRICS_PORT <= 65535):
            errors.append("METRICS_PORT must be between 1 and 65535")
        if not (1 <= settings.HEALTH_CHECK_PORT <= 65535):
            errors.append("HEALTH_CHECK_PORT must be between 1 and 65535")
        
        # Validate log levels
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if settings.LOG_LEVEL.upper() not in valid_levels:
            errors.append(f"LOG_LEVEL must be one of: {valid_levels}")
        
        return errors
    
    def save_config_template(self, output_file: str) -> None:
        """Save a configuration template YAML file."""
        template_config = {
            "# OmniQ Configuration Template": None,
            "# Uncomment and modify values as needed": None,
            "": None,
            "# Core directories": None,
            "# BASE_DIR": str(Path.home() / ".omniq"),
            "# CONFIG_DIR": str(Path.home() / ".omniq" / "config"),
            "# DATA_DIR": str(Path.home() / ".omniq" / "data"),
            "# LOG_DIR": str(Path.home() / ".omniq" / "logs"),
            "": None,
            "# Logging": None,
            "# LOG_LEVEL": "INFO",
            "# LOG_FILE_ENABLED": True,
            "# LOG_CONSOLE_ENABLED": True,
            "": None,
            "# Backends": None,
            "# TASK_QUEUE_TYPE": "file",
            "# RESULT_STORAGE_TYPE": "file",
            "# EVENT_STORAGE_TYPE": "file",
            "": None,
            "# Workers": None,
            "# DEFAULT_WORKER": "async",
            "# WORKER_COUNT": 4,
            "# WORKER_TIMEOUT": 300,
            "": None,
            "# Tasks": None,
            "# TASK_TTL": 86400,
            "# TASK_RETRY_COUNT": 3,
            "# TASK_RETRY_DELAY": 60,
            "": None,
            "# Storage": None,
            "# RESULT_TTL": 604800,
            "# EVENT_TTL": 2592000,
            "# STORAGE_BATCH_SIZE": 100,
        }
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write template
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# OmniQ Configuration Template\n")
            f.write("# Uncomment and modify values as needed\n\n")
            f.write("# Core directories\n")
            f.write(f"# BASE_DIR: {Path.home() / '.omniq'}\n")
            f.write(f"# CONFIG_DIR: {Path.home() / '.omniq' / 'config'}\n")
            f.write(f"# DATA_DIR: {Path.home() / '.omniq' / 'data'}\n")
            f.write(f"# LOG_DIR: {Path.home() / '.omniq' / 'logs'}\n\n")
            f.write("# Logging\n")
            f.write("# LOG_LEVEL: INFO\n")
            f.write("# LOG_FILE_ENABLED: true\n")
            f.write("# LOG_CONSOLE_ENABLED: true\n\n")
            f.write("# Backends\n")
            f.write("# TASK_QUEUE_TYPE: file\n")
            f.write("# RESULT_STORAGE_TYPE: file\n")
            f.write("# EVENT_STORAGE_TYPE: file\n\n")
            f.write("# Workers\n")
            f.write("# DEFAULT_WORKER: async\n")
            f.write("# WORKER_COUNT: 4\n")
            f.write("# WORKER_TIMEOUT: 300\n\n")
            f.write("# Tasks\n")
            f.write("# TASK_TTL: 86400\n")
            f.write("# TASK_RETRY_COUNT: 3\n")
            f.write("# TASK_RETRY_DELAY: 60\n\n")
            f.write("# Storage\n")
            f.write("# RESULT_TTL: 604800\n")
            f.write("# EVENT_TTL: 2592000\n")
            f.write("# STORAGE_BATCH_SIZE: 100\n")


# Default global configuration provider
_default_provider = ConfigProvider()


def get_settings() -> Settings:
    """Get current settings from default provider."""
    return _default_provider.get_settings()


def get_logging_config() -> LoggingConfig:
    """Get logging configuration from default provider."""
    return _default_provider.get_logging_config()


def set_config_file(config_file: str) -> None:
    """Set configuration file for default provider."""
    global _default_provider
    _default_provider = ConfigProvider(config_file)


def set_override(key: str, value: Any) -> None:
    """Set override in default provider."""
    _default_provider.set_override(key, value)


def clear_overrides() -> None:
    """Clear overrides in default provider."""
    _default_provider.clear_overrides()


def reload_config() -> None:
    """Reload configuration in default provider."""
    _default_provider.reload_config()


def validate_config() -> List[str]:
    """Validate configuration using default provider."""
    return _default_provider.validate_config()


def save_config_template(output_file: str) -> None:
    """Save configuration template using default provider."""
    _default_provider.save_config_template(output_file)