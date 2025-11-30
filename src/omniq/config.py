from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from .serialization import Serializer


class BackendType(str, Enum):
    FILE = "file"
    SQLITE = "sqlite"


class Settings:
    """
    Configuration settings for OmniQ with environment variable support.

    Default values are designed for development and can be overridden via environment variables.
    """

    def __init__(
        self,
        *,
        backend: BackendType = BackendType.FILE,
        db_url: Optional[str] = None,
        base_dir: str = "./omniq_data",
        default_timeout: Optional[int] = 300,  # 5 minutes
        default_max_retries: int = 3,
        result_ttl: int = 86400,  # 24 hours in seconds
        serializer: Literal["msgspec", "cloudpickle"] = "msgspec",
        log_level: str = "INFO",
    ):
        self.backend = backend
        self.db_url = db_url
        self.base_dir = Path(base_dir)
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.result_ttl = result_ttl
        self.serializer = serializer
        self.log_level = log_level

    @classmethod
    def from_env(cls) -> Settings:
        """
        Create Settings from environment variables with validation and defaults.

        Environment variables:
        - OMNIQ_BACKEND: Storage backend ('file' or 'sqlite')
        - OMNIQ_DB_URL: Database URL for SQLite backend
        - OMNIQ_BASE_DIR: Base directory for file storage
        - OMNIQ_DEFAULT_TIMEOUT: Default task timeout in seconds
        - OMNIQ_DEFAULT_MAX_RETRIES: Default maximum retry attempts
        - OMNIQ_RESULT_TTL: Result time-to-live in seconds
        - OMNIQ_SERIALIZER: Serializer type ('msgspec' or 'cloudpickle')
        - OMNIQ_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        # Backend selection
        backend_env = os.getenv("OMNIQ_BACKEND", "file").lower()
        if backend_env not in ("file", "sqlite"):
            raise ValueError(
                f"Invalid OMNIQ_BACKEND: {backend_env}. Must be 'file' or 'sqlite'"
            )
        backend = BackendType(backend_env)

        # Database URL (only used for SQLite backend)
        db_url = os.getenv("OMNIQ_DB_URL")

        # Base directory for file storage
        base_dir = os.getenv("OMNIQ_BASE_DIR", "./omniq_data")

        # Default timeout in seconds
        timeout_env = os.getenv("OMNIQ_DEFAULT_TIMEOUT")
        default_timeout = None
        if timeout_env is not None:
            try:
                default_timeout = int(timeout_env)
                if default_timeout < 0:
                    raise ValueError("OMNIQ_DEFAULT_TIMEOUT must be non-negative")
            except ValueError as e:
                raise ValueError(f"Invalid OMNIQ_DEFAULT_TIMEOUT: {e}")
        else:
            default_timeout = 300  # 5 minutes

        # Default max retries
        retries_env = os.getenv("OMNIQ_DEFAULT_MAX_RETRIES")
        default_max_retries = 3
        if retries_env is not None:
            try:
                default_max_retries = int(retries_env)
                if default_max_retries < 0:
                    raise ValueError("OMNIQ_DEFAULT_MAX_RETRIES must be non-negative")
            except ValueError as e:
                raise ValueError(f"Invalid OMNIQ_DEFAULT_MAX_RETRIES: {e}")

        # Result TTL in seconds
        ttl_env = os.getenv("OMNIQ_RESULT_TTL")
        result_ttl = 86400  # 24 hours
        if ttl_env is not None:
            try:
                result_ttl = int(ttl_env)
                if result_ttl < 0:
                    raise ValueError("OMNIQ_RESULT_TTL must be non-negative")
            except ValueError as e:
                raise ValueError(f"Invalid OMNIQ_RESULT_TTL: {e}")

        # Serializer selection
        serializer_env = os.getenv("OMNIQ_SERIALIZER", "msgspec").lower()
        if serializer_env not in ("msgspec", "cloudpickle"):
            raise ValueError(
                f"Invalid OMNIQ_SERIALIZER: {serializer_env}. Must be 'msgspec' or 'cloudpickle'"
            )
        serializer = serializer_env

        # Log level
        log_level_env = os.getenv("OMNIQ_LOG_LEVEL", "INFO").upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if log_level_env not in valid_levels:
            raise ValueError(
                f"Invalid OMNIQ_LOG_LEVEL: {log_level_env}. Must be one of {valid_levels}"
            )
        log_level = log_level_env

        return cls(
            backend=backend,
            db_url=db_url,
            base_dir=base_dir,
            default_timeout=default_timeout,
            default_max_retries=default_max_retries,
            result_ttl=result_ttl,
            serializer=serializer,
            log_level=log_level,
        )

    def create_serializer(self) -> Serializer:
        """Create a serializer instance based on settings."""
        if self.serializer == "msgspec":
            from .serialization import MsgspecSerializer

            return MsgspecSerializer()
        elif self.serializer == "cloudpickle":
            from .serialization import CloudpickleSerializer

            return CloudpickleSerializer()
        else:
            raise ValueError(f"Unknown serializer: {self.serializer}")

    def validate(self) -> None:
        """Validate settings and raise errors for invalid configurations."""
        # Validate backend-specific requirements
        if self.backend == BackendType.SQLITE and not self.db_url:
            raise ValueError("OMNIQ_DB_URL is required when using SQLite backend")

        # Validate base directory
        if not self.base_dir:
            raise ValueError("Base directory cannot be empty")

        # Validate timeout
        if self.default_timeout is not None and self.default_timeout < 0:
            raise ValueError("Default timeout must be non-negative")

        # Validate retries
        if self.default_max_retries < 0:
            raise ValueError("Default max retries must be non-negative")

        # Validate TTL
        if self.result_ttl < 0:
            raise ValueError("Result TTL must be non-negative")
