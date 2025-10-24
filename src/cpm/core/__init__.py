"""Core CPM functionality"""

from .config import GlobalConfigManager
from .registry import RegistryClient
from .schema import ServerConfig, STDIOServerConfig, RemoteServerConfig, GroupMetadata

__all__ = [
    "GlobalConfigManager",
    "RegistryClient",
    "ServerConfig",
    "STDIOServerConfig",
    "RemoteServerConfig",
    "GroupMetadata",
]
