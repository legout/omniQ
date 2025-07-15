"""Azure Backend for OmniQ.

This module provides a unified Azure backend that manages all Azure Blob Storage-based storage components
for tasks, results, events, and schedules using fsspec and adlfs.
"""

from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from ..storage.azure import (
    AsyncAzureQueue,
    AsyncAzureResultStorage,
    AsyncAzureEventStorage,
    AsyncAzureScheduleStorage,
    AzureQueue,
    AzureResultStorage,
    AzureEventStorage,
    AzureScheduleStorage,
)
from ..storage.base import (
    BaseTaskQueue,
    BaseResultStorage,
    BaseEventStorage,
    BaseScheduleStorage,
)


class AzureBackend:
    """Unified Azure backend for OmniQ.
    
    This backend provides both async and sync storage interfaces for all OmniQ
    storage types (tasks, results, events, schedules) using Azure Blob Storage.
    
    Args:
        container_name: Azure container name
        prefix: Optional prefix for all keys (default: "omniq/")
        connection_string: Azure storage connection string (optional, can use environment)
        account_name: Azure storage account name (optional, can use environment)
        account_key: Azure storage account key (optional, can use environment)
        sas_token: Azure SAS token (optional)
        tenant_id: Azure tenant ID for service principal auth (optional)
        client_id: Azure client ID for service principal auth (optional)
        client_secret: Azure client secret for service principal auth (optional)
        **azure_kwargs: Additional arguments passed to adlfs.AzureBlobFileSystem
    """
    
    def __init__(
        self,
        container_name: str,
        prefix: str = "omniq/",
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **azure_kwargs: Any,
    ):
        self.container_name = container_name
        self.prefix = prefix
        self.connection_string = connection_string
        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.azure_kwargs = azure_kwargs
        
        # Storage instances (created lazily)
        self._async_task_storage: Optional[AsyncAzureQueue] = None
        self._async_result_storage: Optional[AsyncAzureResultStorage] = None
        self._async_event_storage: Optional[AsyncAzureEventStorage] = None
        self._async_schedule_storage: Optional[AsyncAzureScheduleStorage] = None
        
        self._sync_task_storage: Optional[AzureQueue] = None
        self._sync_result_storage: Optional[AzureResultStorage] = None
        self._sync_event_storage: Optional[AzureEventStorage] = None
        self._sync_schedule_storage: Optional[AzureScheduleStorage] = None
        
        # Track if we're in an async context
        self._async_context_active = False
    
    def _get_storage_kwargs(self) -> Dict[str, Any]:
        """Get common kwargs for storage initialization."""
        return {
            "container_name": self.container_name,
            "base_prefix": self.prefix,
            "connection_string": self.connection_string,
            "account_name": self.account_name,
            "account_key": self.account_key,
            "sas_token": self.sas_token,
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "azure_additional_kwargs": self.azure_kwargs,
        }
    
    # Async storage properties
    @property
    def async_task_storage(self) -> "AsyncAzureQueue":
        """Get async task storage."""
        if self._async_task_storage is None:
            self._async_task_storage = AsyncAzureQueue(**self._get_storage_kwargs())
        return self._async_task_storage
    
    @property
    def async_result_storage(self) -> "AsyncAzureResultStorage":
        """Get async result storage."""
        if self._async_result_storage is None:
            self._async_result_storage = AsyncAzureResultStorage(**self._get_storage_kwargs())
        return self._async_result_storage
    
    @property
    def async_event_storage(self) -> "AsyncAzureEventStorage":
        """Get async event storage."""
        if self._async_event_storage is None:
            self._async_event_storage = AsyncAzureEventStorage(**self._get_storage_kwargs())
        return self._async_event_storage
    
    @property
    def async_schedule_storage(self) -> "AsyncAzureScheduleStorage":
        """Get async schedule storage."""
        if self._async_schedule_storage is None:
            self._async_schedule_storage = AsyncAzureScheduleStorage(**self._get_storage_kwargs())
        return self._async_schedule_storage
    
    # Sync storage properties
    @property
    def task_storage(self) -> "AzureQueue":
        """Get sync task storage."""
        if self._sync_task_storage is None:
            self._sync_task_storage = AzureQueue(**self._get_storage_kwargs())
        return self._sync_task_storage
    
    @property
    def result_storage(self) -> "AzureResultStorage":
        """Get sync result storage."""
        if self._sync_result_storage is None:
            self._sync_result_storage = AzureResultStorage(**self._get_storage_kwargs())
        return self._sync_result_storage
    
    @property
    def event_storage(self) -> "AzureEventStorage":
        """Get sync event storage."""
        if self._sync_event_storage is None:
            self._sync_event_storage = AzureEventStorage(**self._get_storage_kwargs())
        return self._sync_event_storage
    
    @property
    def schedule_storage(self) -> "AzureScheduleStorage":
        """Get sync schedule storage."""
        if self._sync_schedule_storage is None:
            self._sync_schedule_storage = AzureScheduleStorage(**self._get_storage_kwargs())
        return self._sync_schedule_storage
    
    # Async context manager support
    async def __aenter__(self):
        """Enter async context."""
        self._async_context_active = True
        
        # Initialize all async storage instances if they exist
        if self._async_task_storage:
            await self._async_task_storage.__aenter__()
        if self._async_result_storage:
            await self._async_result_storage.__aenter__()
        if self._async_event_storage:
            await self._async_event_storage.__aenter__()
        if self._async_schedule_storage:
            await self._async_schedule_storage.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        self._async_context_active = False
        
        # Clean up all async storage instances
        if self._async_task_storage:
            await self._async_task_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_result_storage:
            await self._async_result_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_event_storage:
            await self._async_event_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_schedule_storage:
            await self._async_schedule_storage.__aexit__(exc_type, exc_val, exc_tb)
    
    # Sync context manager support
    def __enter__(self):
        """Enter sync context."""
        # Initialize all sync storage instances if they exist
        if self._sync_task_storage:
            self._sync_task_storage.__enter__()
        if self._sync_result_storage:
            self._sync_result_storage.__enter__()
        if self._sync_event_storage:
            self._sync_event_storage.__enter__()
        if self._sync_schedule_storage:
            self._sync_schedule_storage.__enter__()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context."""
        # Clean up all sync storage instances
        if self._sync_task_storage:
            self._sync_task_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_result_storage:
            self._sync_result_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_event_storage:
            self._sync_event_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_schedule_storage:
            self._sync_schedule_storage.__exit__(exc_type, exc_val, exc_tb)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"AzureBackend(container='{self.container_name}', prefix='{self.prefix}')"


# Convenience function for creating Azure backend from config
def create_azure_backend_from_config(config: Dict[str, Any]) -> AzureBackend:
    """Create AzureBackend from configuration dictionary.
    
    Args:
        config: Configuration dictionary with Azure settings
        
    Returns:
        Configured AzureBackend instance
    """
    return AzureBackend(
        container_name=config["container_name"],
        prefix=config.get("prefix", "omniq/"),
        connection_string=config.get("connection_string"),
        account_name=config.get("account_name"),
        account_key=config.get("account_key"),
        sas_token=config.get("sas_token"),
        tenant_id=config.get("tenant_id"),
        client_id=config.get("client_id"),
        client_secret=config.get("client_secret"),
        **config.get("azure_kwargs", {}),
    )