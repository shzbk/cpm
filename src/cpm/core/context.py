"""
Unified context manager for global vs local configuration

Global: ~/.config/cpm/servers.json
Local:  ./server.json
"""

import logging
from pathlib import Path
from typing import Dict, List, Literal, Optional

from cpm.core.config import GlobalConfigManager
from cpm.core.local_config import LocalConfigManager
from cpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class ConfigContext:
    """
    Unified configuration interface that works with both global and local contexts.

    Automatically detects context based on presence of server.json or explicit flags.
    Provides a consistent API regardless of context.

    Global: ~/.config/cpm/servers.json
    Local:  ./server.json (auto-detected)
    """

    def __init__(
        self,
        local: bool = False,
        global_force: bool = False,
        project_dir: Optional[Path] = None,
    ):
        """
        Initialize config context

        Args:
            local: Force local context (error if no server.json)
            global_force: Force global context (ignores server.json)
            project_dir: Project directory for local context
        """
        # Determine context
        if global_force:
            # Explicit global flag - ignore local detection
            self.context: Literal["global", "local"] = "global"
            self.manager = GlobalConfigManager()
        elif local:
            # Explicit local flag - require server.json
            if not LocalConfigManager.detect_project(project_dir):
                raise FileNotFoundError("No server.json found. Run 'cpm init' first.")
            self.context = "local"
            self.manager = LocalConfigManager(project_dir)
        elif LocalConfigManager.detect_project(project_dir):
            # Auto-detect: server.json exists
            self.context = "local"
            self.manager = LocalConfigManager(project_dir)
        else:
            # Default: global context
            self.context = "global"
            self.manager = GlobalConfigManager()

        logger.debug(f"ConfigContext initialized: {self.context} mode")

    @property
    def is_local(self) -> bool:
        """Check if using local context"""
        return self.context == "local"

    @property
    def is_global(self) -> bool:
        """Check if using global context"""
        return self.context == "global"

    # Unified server operations
    def add_server(self, name: str, server_config: ServerConfig, **kwargs):
        """Add server to context"""
        force = kwargs.get("force", False)
        if self.is_local:
            version = kwargs.get("version", "latest")
            dev = kwargs.get("dev", False)
            self.manager.add_server(name, version, server_config, dev)
        else:
            # For global config, ensure server has the name field set
            if not hasattr(server_config, 'name') or server_config.name != name:
                server_config.name = name
            self.manager.add_server(server_config, force=force)

    def remove_server(self, name: str):
        """Remove server from context"""
        if self.is_local:
            self.manager.remove_server(name)
        else:
            self.manager.remove_server(name)

    def get_server(self, name: str) -> ServerConfig:
        """Get server configuration"""
        return self.manager.get_server(name)

    def list_servers(self) -> Dict[str, ServerConfig]:
        """List all servers"""
        return self.manager.list_servers()

    def server_exists(self, name: str) -> bool:
        """Check if server exists"""
        try:
            self.get_server(name)
            return True
        except KeyError:
            return False

    def update_server_config(self, name: str, env_vars: Dict[str, str]):
        """Update server environment variables"""
        self.manager.update_server_config(name, env_vars)

    # Group operations
    def create_group(self, name: str, description: Optional[str] = None):
        """Create a group"""
        self.manager.create_group(name, description)

    def delete_group(self, name: str):
        """Delete a group"""
        self.manager.delete_group(name)

    def rename_group(self, old_name: str, new_name: str):
        """Rename a group"""
        self.manager.rename_group(old_name, new_name)

    def get_group(self, name: str):
        """Get group metadata"""
        return self.manager.get_group(name)

    def add_server_to_group(self, server_name: str, group_name: str):
        """Add server to group"""
        self.manager.add_server_to_group(server_name, group_name)

    def remove_server_from_group(self, server_name: str, group_name: str):
        """Remove server from group"""
        self.manager.remove_server_from_group(server_name, group_name)

    def get_servers_in_group(self, group_name: str) -> Dict[str, ServerConfig]:
        """Get all servers in a group"""
        return self.manager.get_servers_in_group(group_name)

    def list_groups(self) -> Dict[str, any]:
        """List all groups"""
        return self.manager.list_groups()

    def group_exists(self, name: str) -> bool:
        """Check if group exists"""
        return self.manager.group_exists(name)

    # Context-specific operations
    def get_version(self, name: str) -> Optional[str]:
        """Get server version (local context only)"""
        if self.is_local:
            return self.manager.get_version(name)
        return None

    def get_context_info(self) -> Dict[str, any]:
        """Get context information"""
        info = {"context": self.context}

        if self.is_local:
            info["project_dir"] = str(self.manager.project_dir)
            info["config_file"] = str(self.manager.config_file)
            info["lock_file"] = str(self.manager.lock_file)
        else:
            info["config_path"] = str(self.manager.config_path)

        return info

    def __repr__(self) -> str:
        return f"ConfigContext(context='{self.context}')"
