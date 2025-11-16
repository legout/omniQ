"""Configuration settings for OmniQ."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class BackendType(str, Enum):
    """Supported storage backends."""

    FILE = "file"
    SQLITE = "sqlite"


class SerializerType(str, Enum):
    """Supported serializers."""

    MSGSPEC = "msgspec"
    CLOUDPICKLE = "cloudpickle"


@dataclass
class Settings:
    """Configuration settings for OmniQ.

    These settings can be configured via environment variables with the
    OMNIQ_ prefix, or by modifying the Settings instance directly.
    """

    # Storage backend configuration
    backend: BackendType = BackendType.FILE

    # File backend settings
    base_dir: Path = field(default_factory=lambda: Path.home() / ".omniq")

    # SQLite backend settings
    db_url: str = ":memory:"

    # Task execution defaults
    default_timeout: Optional[int] = None
    default_max_retries: int = 0
    result_ttl: int = 3600  # 1 hour in seconds

    # Serialization
    serializer: SerializerType = SerializerType.MSGSPEC

    # Logging
    log_level: str = "INFO"

    # Internal settings
    _env_prefix: str = "OMNIQ_"
    _custom_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate current settings."""
        # Validate base directory
        if not isinstance(self.base_dir, Path):
            self.base_dir = Path(self.base_dir)

        # Validate timeout
        if self.default_timeout is not None and self.default_timeout <= 0:
            raise ValueError("default_timeout must be positive or None")

        # Validate max retries
        if self.default_max_retries < 0:
            raise ValueError("default_max_retries must be non-negative")

        # Validate result TTL
        if self.result_ttl <= 0:
            raise ValueError("result_ttl must be positive")

        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")

        # Validate backend-specific settings
        if self.backend == BackendType.SQLITE and self.db_url == ":memory:":
            # For SQLite, if using memory database, we need a file path for testing
            # In production, users should specify a proper database path
            pass

    @classmethod
    def from_env(cls, environ: Optional[Dict[str, str]] = None) -> Settings:
        """Create Settings from environment variables.

        Args:
            environ: Dictionary of environment variables to use.
                    If None, uses os.environ.

        Returns:
            Settings instance configured from environment.
        """
        if environ is None:
            environ = dict(os.environ)

        # Extract environment variables with OMNIQ_ prefix
        env_settings = {}

        for key, value in environ.items():
            if key.startswith(cls._env_prefix):
                # Remove prefix and convert to lowercase for setting name
                setting_name = key[len(cls._env_prefix) :].lower()
                env_settings[setting_name] = value

        # Parse and validate environment values
        if "backend" in env_settings:
            env_settings["backend"] = BackendType(env_settings["backend"].lower())

        if "base_dir" in env_settings:
            env_settings["base_dir"] = Path(env_settings["base_dir"])

        if "default_timeout" in env_settings:
            timeout_val = env_settings["default_timeout"]
            env_settings["default_timeout"] = int(timeout_val) if timeout_val else None

        if "default_max_retries" in env_settings:
            env_settings["default_max_retries"] = int(
                env_settings["default_max_retries"]
            )

        if "result_ttl" in env_settings:
            env_settings["result_ttl"] = int(env_settings["result_ttl"])

        if "serializer" in env_settings:
            env_settings["serializer"] = SerializerType(
                env_settings["serializer"].lower()
            )

        if "log_level" in env_settings:
            env_settings["log_level"] = env_settings["log_level"].upper()

        # Create settings instance with defaults
        settings = cls()

        # Update with environment values
        for key, value in env_settings.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        # Re-validate after environment updates
        settings._validate()

        return settings

    def validate(self) -> None:
        """Validate current settings."""
        self._validate()

    def get_storage_config(self) -> Dict[str, Any]:
        """Get configuration dict for storage backend."""
        if self.backend == BackendType.FILE:
            return {
                "backend": "file",
                "base_dir": self.base_dir,
            }
        elif self.backend == BackendType.SQLITE:
            return {
                "backend": "sqlite",
                "db_path": self.db_url if self.db_url != ":memory:" else ":memory:",
            }
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def get_serializer_config(self) -> Dict[str, Any]:
        """Get configuration for serializer."""
        return {
            "type": self.serializer.value,
        }

    def __repr__(self) -> str:
        """String representation of settings."""
        return (
            f"Settings(backend={self.backend}, "
            f"base_dir={self.base_dir}, "
            f"serializer={self.serializer}, "
            f"log_level={self.log_level})"
        )


def get_settings() -> Settings:
    """Get current settings, loaded from environment if available."""
    return Settings.from_env()


def create_settings(**kwargs) -> Settings:
    """Create settings with overrides."""
    settings = Settings.from_env()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    settings._validate()
    return settings
