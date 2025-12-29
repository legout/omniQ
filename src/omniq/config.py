from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from .serialization import Serializer


class BackendType(str, Enum):
    """Storage backend options for task persistence.

    OmniQ supports multiple storage backends with different tradeoffs for
    scalability, performance, and deployment requirements.

    Attributes:
        FILE: File-based storage using JSON files. Simple and portable with no
            external dependencies. Suitable for development and single-process
            deployments. Not recommended for production with high concurrency.
        SQLITE: SQLite database storage. Provides ACID guarantees and better
            concurrency support. Suitable for production use with moderate loads.
            Requires a database file path configuration.

    Example:
        >>> from omniq.config import Settings, BackendType
        >>>
        >>> # Use file backend (simple, no dependencies)
        >>> settings = Settings(backend=BackendType.FILE)
        >>>
        >>> # Use SQLite backend (better concurrency)
        >>> settings = Settings(
        ...     backend=BackendType.SQLITE,
        ...     db_url="sqlite:///omniq.db"
        ... )
    """

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
        serializer: Literal["msgspec", "cloudpickle", "json"] = "msgspec",
        log_level: str = "INFO",
    ):
        """Initialize OmniQ configuration settings.

        Args:
            backend: Storage backend type (FILE or SQLITE). Defaults to FILE.
            db_url: Database URL for SQLite backend (e.g., "sqlite:///path/to/db").
                Required when backend is SQLITE. Ignored for FILE backend.
                Defaults to None.
            base_dir: Base directory for file storage backend. Defaults to
                "./omniq_data". Ignored for SQLITE backend.
            default_timeout: Default task timeout in seconds. If None, no timeout
                is enforced. Defaults to 300 (5 minutes).
            default_max_retries: Default maximum retry attempts for failed tasks.
                Defaults to 3. Set to 0 to disable retries.
            result_ttl: Time-to-live for task results in seconds. Results older
                than this may be garbage collected. Defaults to 86400 (24 hours).
            serializer: Serializer type for task arguments and results. Options:
                "msgspec" (fast, Python types only), "cloudpickle" (supports any
                Python object), or "json" (universal but slower). Defaults to
                "msgspec".
            log_level: Logging level for task execution logs. Must be one of
                "DEBUG", "INFO", "WARNING", "ERROR", or "CRITICAL". Defaults to
                "INFO".

        Raises:
            ValueError: If db_url is not provided when using SQLITE backend.

        Example:
            >>> from omniq.config import Settings, BackendType
            >>>
            >>> # Minimal configuration with defaults
            >>> settings = Settings()
            >>>
            >>> # SQLite backend with custom path
            >>> settings = Settings(
            ...     backend=BackendType.SQLITE,
            ...     db_url="sqlite:///data/omniq.db"
            ... )
            >>>
            >>> # Custom timeout and retries
            >>> settings = Settings(
            ...     default_timeout=600,  # 10 minutes
            ...     default_max_retries=5
            ... )
        """
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
        """Create Settings from environment variables with validation and defaults.

        Reads configuration from environment variables and creates a Settings
        instance. All variables are optional and have sensible defaults.

        Environment variables:
        - OMNIQ_BACKEND: Storage backend ('file' or 'sqlite')
        - OMNIQ_DB_URL: Database URL for SQLite backend
        - OMNIQ_BASE_DIR: Base directory for file storage
        - OMNIQ_DEFAULT_TIMEOUT: Default task timeout in seconds
        - OMNIQ_DEFAULT_MAX_RETRIES: Default maximum retry attempts
        - OMNIQ_RESULT_TTL: Result time-to-live in seconds
        - OMNIQ_SERIALIZER: Serializer type ('msgspec', 'cloudpickle', or 'json')
        - OMNIQ_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Returns:
            Settings instance configured from environment variables

        Raises:
            ValueError: If any environment variable has an invalid value

        Example:
            >>> # Set environment variables (e.g., in .env file)
            >>> # export OMNIQ_BACKEND=sqlite
            >>> # export OMNIQ_DB_URL=sqlite:///data/omniq.db
            >>> # export OMNIQ_DEFAULT_MAX_RETRIES=5
            >>>
            >>> # Create settings from environment
            >>> settings = Settings.from_env()
            >>> print(settings.backend)  # BackendType.SQLITE
            >>> print(settings.default_max_retries)  # 5
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
        if serializer_env not in ("msgspec", "cloudpickle", "json"):
            raise ValueError(
                f"Invalid OMNIQ_SERIALIZER: {serializer_env}. Must be 'msgspec', 'cloudpickle', or 'json'"
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
        elif self.serializer == "json":
            from .serialization import JSONSerializer

            return JSONSerializer()
        else:
            raise ValueError(f"Unknown serializer: {self.serializer}")

    def validate(self) -> None:
        """Validate settings and raise errors for invalid configurations."""
        # Validate backend selection
        if not isinstance(self.backend, BackendType):
            raise ValueError(
                f"Invalid storage backend: {self.backend}. Must be 'file' or 'sqlite'"
            )

        # Validate backend-specific requirements
        if self.backend == BackendType.SQLITE:
            if not self.db_url:
                raise ValueError("db_url is required when using SQLite backend")

            # Validate SQLite URL format
            if not self.db_url.startswith("sqlite:///"):
                raise ValueError(
                    f"Invalid SQLite URL format: {self.db_url}. Must start with 'sqlite:///'"
                )

            # Validate SQLite URL path
            from urllib.parse import urlparse

            parsed = urlparse(self.db_url)
            if not parsed.path or parsed.path == "/":
                raise ValueError(
                    f"SQLite URL must specify a database file path: {self.db_url}"
                )

        # Validate base directory (required for file backend)
        if self.backend == BackendType.FILE and not self.base_dir:
            raise ValueError("Base directory is required when using file backend")

        # Validate timeout
        if self.default_timeout is not None and self.default_timeout < 0:
            raise ValueError("Default timeout must be non-negative")

        # Validate retries
        if self.default_max_retries < 0:
            raise ValueError("Default max retries must be non-negative")

        # Validate TTL
        if self.result_ttl < 0:
            raise ValueError("Result TTL must be non-negative")

        # Validate serializer
        if self.serializer not in ("msgspec", "cloudpickle", "json"):
            raise ValueError(
                f"Invalid serializer: {self.serializer}. Must be 'msgspec', 'cloudpickle', or 'json'"
            )
