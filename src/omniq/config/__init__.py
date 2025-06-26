import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# This is a simple implementation. A more robust one might use Pydantic or a similar library
# and support loading from YAML/TOML files as mentioned in the plan.

@dataclass
class OmniQConfig:
    """OmniQ configuration settings."""

    task_queue_url: str = field(
        default=os.environ.get("OMNIQ_TASK_QUEUE_URL", "memory://")
    )
    result_storage_url: str = field(
        default=os.environ.get("OMNIQ_RESULT_STORAGE_URL", "memory://")
    )
    event_storage_url: Optional[str] = field(
        default=os.environ.get("OMNIQ_EVENT_STORAGE_URL")
    )
    schedule_storage_url: str = field(
        default=os.environ.get("OMNIQ_SCHEDULE_STORAGE_URL", "memory://")
    )
    # Storage options can be passed for fsspec, etc.
    storage_options: Dict[str, Dict[str, Any]] = field(default_factory=dict)

def get_config(**overrides: Any) -> OmniQConfig:
    """Get the application configuration, with optional overrides."""
    config = OmniQConfig()
    for key, value in overrides.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)
    return config