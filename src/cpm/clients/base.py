"""
Base client manager classes for MCP clients
"""

import abc
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter
from ruamel.yaml import YAML

from cpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class BaseClientManager(abc.ABC):
    """
    Abstract base class for all client managers

    Defines the interface that all client managers must implement
    """

    # Client information (set by subclasses)
    client_key = ""
    display_name = ""
    download_url = ""
    config_path: str

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the client manager"""
        self._system = platform.system()
        if config_path_override:
            self.config_path = config_path_override

    @abc.abstractmethod
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client"""
        pass

    @abc.abstractmethod
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a specific server configuration"""
        pass

    @abc.abstractmethod
    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server in the client config"""
        pass

    @abc.abstractmethod
    def remove_server(self, server_name: str) -> bool:
        """Remove a server from client config"""
        pass

    @abc.abstractmethod
    def list_servers(self) -> List[str]:
        """List all server names in client config"""
        pass

    @abc.abstractmethod
    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format"""
        pass

    @abc.abstractmethod
    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig"""
        pass

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client"""
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
        }

    def is_client_installed(self) -> bool:
        """Check if this client is installed"""
        return os.path.isdir(os.path.dirname(self.config_path))


class JSONClientManager(BaseClientManager):
    """
    JSON-based client manager implementation

    For clients that use JSON configuration files
    """

    configure_key_name: str = "mcpServers"

    def __init__(self, config_path_override: Optional[str] = None):
        super().__init__(config_path_override=config_path_override)
        self._config = None

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file"""
        empty_config = {self.configure_key_name: {}}

        if not os.path.exists(self.config_path):
            logger.debug(f"Config file not found: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if self.configure_key_name not in config:
                    config[self.configure_key_name] = {}
                return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            # Backup corrupt file
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.rename(self.config_path, backup_path)
                    logger.info(f"Backed up corrupt config to: {backup_path}")
                except Exception:
                    pass
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def get_servers(self) -> Dict[str, Any]:
        """Get all servers"""
        config = self._load_config()
        return config.get(self.configure_key_name, {})

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a specific server"""
        servers = self.get_servers()
        if server_name not in servers:
            return None
        return self.from_client_format(server_name, servers[server_name])

    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server"""
        server_name = server_config.name
        client_config = self.to_client_format(server_config)

        config = self._load_config()
        config[self.configure_key_name][server_name] = client_config

        return self._save_config(config)

    def remove_server(self, server_name: str) -> bool:
        """Remove a server"""
        config = self._load_config()
        servers = config.get(self.configure_key_name, {})

        if server_name not in servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        del config[self.configure_key_name][server_name]
        return self._save_config(config)

    def list_servers(self) -> List[str]:
        """List all server names"""
        return list(self.get_servers().keys())

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client format"""
        # Handle CPMRuntimeConfig with command (STDIO) or url (Remote)
        if hasattr(server_config, 'command') and server_config.command:
            # STDIO-based server
            result = {
                "command": server_config.command,
                "args": server_config.args or [],
            }
            if server_config.env:
                result["env"] = {k: v for k, v in server_config.env.items() if v}
            return result
        elif hasattr(server_config, 'url') and server_config.url:
            # Remote-based server
            return {
                "url": server_config.url,
                "headers": server_config.headers or {},
            }
        else:
            # Fallback: dump entire config
            return server_config.model_dump()

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig"""
        server_data = {"name": server_name}
        server_data.update(client_config)
        return TypeAdapter(ServerConfig).validate_python(server_data)


class YAMLClientManager(BaseClientManager):
    """
    YAML-based client manager implementation

    For clients that use YAML configuration files
    """

    def __init__(self, config_path_override: Optional[str] = None):
        super().__init__(config_path_override=config_path_override)
        self.yaml_handler = YAML()

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file"""
        empty_config = self._get_empty_config()

        if not os.path.exists(self.config_path):
            logger.debug(f"Config file not found: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = self.yaml_handler.load(f)
                return config if config else empty_config
        except Exception as e:
            logger.error(f"Error parsing config file: {e}")
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.yaml_handler.dump(config, f)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    @abc.abstractmethod
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty configuration structure"""
        pass

    @abc.abstractmethod
    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get server config from the loaded config"""
        pass

    @abc.abstractmethod
    def _get_all_server_names(self, config: Dict[str, Any]) -> List[str]:
        """Get all server names from config"""
        pass

    @abc.abstractmethod
    def _add_server_to_config(
        self, config: Dict[str, Any], server_name: str, server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add server to config"""
        pass

    @abc.abstractmethod
    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove server from config"""
        pass

    def get_servers(self) -> Dict[str, Any]:
        """Get all servers"""
        config = self._load_config()
        result = {}
        for server_name in self._get_all_server_names(config):
            server_config = self._get_server_config(config, server_name)
            if server_config:
                result[server_name] = self._normalize_server_config(server_config)
        return result

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a specific server"""
        config = self._load_config()
        server_config = self._get_server_config(config, server_name)
        if not server_config:
            return None
        return self.from_client_format(server_name, self._normalize_server_config(server_config))

    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server"""
        server_name = server_config.name
        client_config = self.to_client_format(server_config)

        config = self._load_config()
        config = self._add_server_to_config(config, server_name, client_config)

        return self._save_config(config)

    def remove_server(self, server_name: str) -> bool:
        """Remove a server"""
        config = self._load_config()
        if not self._get_server_config(config, server_name):
            logger.warning(f"Server '{server_name}' not found")
            return False

        config = self._remove_server_from_config(config, server_name)
        return self._save_config(config)

    def list_servers(self) -> List[str]:
        """List all server names"""
        config = self._load_config()
        return self._get_all_server_names(config)

    def _normalize_server_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize server config for external use"""
        return server_config

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client format"""
        # Handle CPMRuntimeConfig with command (STDIO) or url (Remote)
        if hasattr(server_config, 'command') and server_config.command:
            # STDIO-based server
            result = {
                "command": server_config.command,
                "args": server_config.args or [],
            }
            if server_config.env:
                result["env"] = {k: v for k, v in server_config.env.items() if v}
            return result
        elif hasattr(server_config, 'url') and server_config.url:
            # Remote-based server
            return {
                "url": server_config.url,
                "headers": server_config.headers or {},
            }
        else:
            # Fallback: dump entire config
            return server_config.model_dump()

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig"""
        server_data = {"name": server_name}
        server_data.update(client_config)
        return TypeAdapter(ServerConfig).validate_python(server_data)
