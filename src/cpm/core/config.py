"""
Global configuration manager for CPM
Manages servers, groups, and all CPM configuration
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import TypeAdapter

from .schema import CPMRuntimeConfig, GroupMetadata, ServerConfig, ServerLockfile

logger = logging.getLogger(__name__)

# Default configuration paths
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cpm"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "servers.json"
DEFAULT_LOCKFILE = DEFAULT_CONFIG_DIR / "servers-lock.json"


class GlobalConfigManager:
    """
    Manages the global CPM configuration

    All servers are stored in a single configuration file.
    Groups organize servers via tagging.
    """

    def __init__(self, config_path: Optional[Path] = None, lockfile_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.lockfile_path = lockfile_path or DEFAULT_LOCKFILE
        self.config_dir = self.config_path.parent
        self._servers: Dict[str, ServerConfig] = {}
        self._groups: Dict[str, GroupMetadata] = {}
        self._lockfile: Optional[ServerLockfile] = None
        self._ensure_config_dir()
        self._load_config()
        self._load_lockfile()

    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> None:
        """Load configuration from file"""
        if not self.config_path.exists():
            logger.debug(f"Config file not found: {self.config_path}")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Load servers (may be ServerConfig or CPMRuntimeConfig)
            servers_data = data.get("servers", {})
            for name, config_data in servers_data.items():
                try:
                    # Try CPMRuntimeConfig first (has more fields)
                    try:
                        self._servers[name] = CPMRuntimeConfig.model_validate(config_data)
                    except Exception:
                        # Fall back to ServerConfig
                        self._servers[name] = TypeAdapter(ServerConfig).validate_python(config_data)
                except Exception as e:
                    logger.error(f"Error loading server {name}: {e}")

            # Load groups
            groups_data = data.get("groups", {})
            for name, group_data in groups_data.items():
                try:
                    self._groups[name] = GroupMetadata.model_validate(group_data)
                except Exception as e:
                    logger.error(f"Error loading group {name}: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def _save_config(self) -> bool:
        """Save configuration to file"""
        try:
            self._ensure_config_dir()

            data = {
                "servers": {name: config.model_dump() for name, config in self._servers.items()},
                "groups": {name: group.model_dump() for name, group in self._groups.items()},
            }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def _load_lockfile(self) -> None:
        """Load lockfile from file"""
        if not self.lockfile_path.exists():
            logger.debug(f"Lockfile not found: {self.lockfile_path}")
            self._lockfile = ServerLockfile()
            return

        try:
            with open(self.lockfile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._lockfile = ServerLockfile.model_validate(data)
        except Exception as e:
            logger.error(f"Error loading lockfile: {e}")
            self._lockfile = ServerLockfile()

    def _save_lockfile(self) -> bool:
        """Save lockfile to file"""
        if not self._lockfile:
            self._lockfile = ServerLockfile()

        try:
            self._ensure_config_dir()
            with open(self.lockfile_path, "w", encoding="utf-8") as f:
                json.dump(self._lockfile.model_dump(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving lockfile: {e}")
            return False

    def add_to_lockfile(self, server_name: str, entry) -> bool:
        """Add server entry to lockfile"""
        if not self._lockfile:
            self._lockfile = ServerLockfile()
        self._lockfile.servers[server_name] = entry
        return self._save_lockfile()

    def get_lockfile(self) -> ServerLockfile:
        """Get the lockfile"""
        if not self._lockfile:
            self._lockfile = ServerLockfile()
        return self._lockfile

    def load_lockfile(self) -> ServerLockfile:
        """Load and return the lockfile"""
        if not self._lockfile:
            self._load_lockfile()
        if not self._lockfile:
            self._lockfile = ServerLockfile()
        return self._lockfile

    def save_lockfile(self, lockfile: ServerLockfile) -> bool:
        """Save a lockfile"""
        self._lockfile = lockfile
        return self._save_lockfile()

    # ===== Server Management =====

    def add_server(self, server, force: bool = False) -> bool:
        """Add a server to global configuration (ServerConfig or CPMRuntimeConfig)"""
        if not hasattr(server, 'name'):
            raise ValueError("Server must have a 'name' attribute")

        if server.name in self._servers and not force:
            logger.warning(f"Server '{server.name}' already exists")
            return False

        self._servers[server.name] = server
        return self._save_config()

    def remove_server(self, server_name: str) -> bool:
        """Remove a server from global configuration"""
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        del self._servers[server_name]
        return self._save_config()

    def get_server(self, server_name: str) -> ServerConfig:
        """Get a server by name"""
        if server_name not in self._servers:
            raise KeyError(f"Server not found: {server_name}")
        return self._servers[server_name]

    def list_servers(self) -> Dict[str, ServerConfig]:
        """Get all servers"""
        return self._servers.copy()

    def server_exists(self, server_name: str) -> bool:
        """Check if a server exists"""
        return server_name in self._servers

    def update_server(self, server: ServerConfig) -> bool:
        """Update an existing server"""
        if server.name not in self._servers:
            logger.warning(f"Server '{server.name}' not found")
            return False

        self._servers[server.name] = server
        return self._save_config()

    def update_server_config(self, server_name: str, env_vars: Dict[str, str]) -> bool:
        """Update environment variables for a server"""
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        # Replace entire env dict (not just update) to handle deletions properly
        server = self._servers[server_name]
        server.env = env_vars if env_vars else {}

        return self._save_config()

    # ===== Group Management =====

    def create_group(self, name: str, description: Optional[str] = None) -> bool:
        """Create a new group"""
        if name in self._groups:
            logger.warning(f"Group '{name}' already exists")
            return False

        self._groups[name] = GroupMetadata(name=name, description=description)
        return self._save_config()

    def delete_group(self, name: str) -> bool:
        """Delete a group and remove its tags from all servers"""
        if name not in self._groups:
            logger.warning(f"Group '{name}' not found")
            return False

        # Remove group tags from all servers
        for server in self._servers.values():
            server.remove_group(name)

        # Delete group metadata
        del self._groups[name]
        return self._save_config()

    def rename_group(self, old_name: str, new_name: str) -> bool:
        """Rename a group and update all server tags"""
        if old_name not in self._groups:
            logger.warning(f"Group '{old_name}' not found")
            return False

        if new_name in self._groups:
            logger.warning(f"Group '{new_name}' already exists")
            return False

        # Update group metadata
        self._groups[new_name] = self._groups[old_name]
        self._groups[new_name].name = new_name
        del self._groups[old_name]

        # Update server tags
        for server in self._servers.values():
            if server.has_group(old_name):
                server.remove_group(old_name)
                server.add_group(new_name)

        return self._save_config()

    def get_group(self, name: str) -> Optional[GroupMetadata]:
        """Get group metadata"""
        return self._groups.get(name)

    def list_groups(self) -> Dict[str, GroupMetadata]:
        """Get all groups"""
        return self._groups.copy()

    def group_exists(self, name: str) -> bool:
        """Check if a group exists"""
        return name in self._groups

    # ===== Group-Server Relationships =====

    def add_server_to_group(self, server_name: str, group_name: str) -> bool:
        """Add a server to a group (tag it)"""
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        # Ensure group exists
        if group_name not in self._groups:
            self.create_group(group_name)

        self._servers[server_name].add_group(group_name)
        return self._save_config()

    def remove_server_from_group(self, server_name: str, group_name: str) -> bool:
        """Remove a server from a group (untag it)"""
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        self._servers[server_name].remove_group(group_name)
        return self._save_config()

    def get_servers_in_group(self, group_name: str) -> Dict[str, ServerConfig]:
        """Get all servers that belong to a group"""
        return {
            name: server
            for name, server in self._servers.items()
            if server.has_group(group_name)
        }

    def get_all_groups_tags(self) -> List[str]:
        """Get all unique group tags across all servers"""
        tags = set()
        for server in self._servers.values():
            tags.update(server.groups)
        return sorted(list(tags))
