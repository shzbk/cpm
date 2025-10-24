"""
Local configuration manager for project-specific servers (server.json)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ValidationError

from cpm.core.schema import ServerConfig, STDIOServerConfig, RemoteServerConfig

logger = logging.getLogger(__name__)


class LocalManifest(BaseModel):
    """Project manifest (server.json)"""

    name: str
    version: str = "1.0.0"
    servers: Dict[str, str] = {}  # name → version
    devServers: Dict[str, str] = {}  # dev dependencies
    groups: Dict[str, List[str]] = {}  # group → servers
    config: Dict[str, Dict[str, str]] = {}  # server → env vars


class LocalConfigManager:
    """Manages project-level servers (server.json)"""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.config_file = self.project_dir / "server.json"
        self.lock_file = self.project_dir / "server-lock.json"
        self.local_dir = self.project_dir / ".cpm"
        self.servers_dir = self.local_dir / "servers"
        self.config_dir = self.local_dir / "config"

    @staticmethod
    def detect_project(path: Optional[Path] = None) -> bool:
        """Check if directory contains server.json"""
        check_path = path or Path.cwd()
        return (check_path / "server.json").exists()

    def init_project(
        self,
        name: str,
        version: str = "1.0.0",
        template: Optional[str] = None,
    ) -> LocalManifest:
        """Initialize a new project with server.json"""
        if self.config_file.exists():
            raise FileExistsError(f"Project already initialized: {self.config_file}")

        # Create directories
        self.local_dir.mkdir(exist_ok=True)
        self.servers_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)

        # Create manifest
        manifest = LocalManifest(name=name, version=version)

        # Apply template if specified
        if template:
            manifest = self._apply_template(manifest, template)

        # Save manifest
        self._save_manifest(manifest)

        logger.info(f"Initialized project: {name} at {self.project_dir}")
        return manifest

    def _apply_template(self, manifest: LocalManifest, template: str) -> LocalManifest:
        """Apply template to manifest"""
        templates = {
            "ai-agent": {
                "servers": {"brave-search": "latest", "filesystem": "latest"},
                "groups": {"research": ["brave-search"], "tools": ["filesystem"]},
            },
            "basic": {
                "servers": {},
                "groups": {},
            },
        }

        if template in templates:
            template_data = templates[template]
            manifest.servers.update(template_data.get("servers", {}))
            manifest.groups.update(template_data.get("groups", {}))

        return manifest

    def load_manifest(self) -> LocalManifest:
        """Load server.json"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"No server.json found in {self.project_dir}")

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return LocalManifest(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Invalid server.json: {e}")

    def _save_manifest(self, manifest: LocalManifest):
        """Save manifest to server.json"""
        with open(self.config_file, "w") as f:
            json.dump(manifest.model_dump(), f, indent=2)

    def add_server(
        self,
        name: str,
        version: str,
        server_config: ServerConfig,
        dev: bool = False,
    ):
        """Add server to manifest"""
        manifest = self.load_manifest()

        # Add to appropriate section
        if dev:
            manifest.devServers[name] = version
        else:
            manifest.servers[name] = version

        # Save server config
        self._save_server_config(name, server_config)

        # Update manifest
        self._save_manifest(manifest)

        logger.info(f"Added {name}@{version} to project")

    def remove_server(self, name: str):
        """Remove server from manifest"""
        manifest = self.load_manifest()

        # Remove from servers or devServers
        removed = False
        if name in manifest.servers:
            del manifest.servers[name]
            removed = True
        if name in manifest.devServers:
            del manifest.devServers[name]
            removed = True

        if not removed:
            raise KeyError(f"Server not found: {name}")

        # Remove from groups
        for group_name, servers in manifest.groups.items():
            if name in servers:
                servers.remove(name)

        # Remove server config
        config_file = self.config_dir / f"{name}.json"
        if config_file.exists():
            config_file.unlink()

        # Update manifest
        self._save_manifest(manifest)

        logger.info(f"Removed {name} from project")

    def _save_server_config(self, name: str, server_config: ServerConfig):
        """Save server configuration"""
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        config_file = self.config_dir / f"{name}.json"
        with open(config_file, "w") as f:
            json.dump(server_config.model_dump(), f, indent=2)

    def get_server(self, name: str) -> ServerConfig:
        """Get server configuration"""
        config_file = self.config_dir / f"{name}.json"
        if not config_file.exists():
            raise KeyError(f"Server not found: {name}")

        with open(config_file, "r") as f:
            data = json.load(f)

        # Determine type and parse
        if "command" in data:
            return STDIOServerConfig(**data)
        elif "url" in data:
            return RemoteServerConfig(**data)
        else:
            raise ValueError(f"Invalid server config for {name}")

    def list_servers(self) -> Dict[str, ServerConfig]:
        """List all servers (including devServers)"""
        manifest = self.load_manifest()
        servers = {}

        for name in list(manifest.servers.keys()) + list(manifest.devServers.keys()):
            try:
                servers[name] = self.get_server(name)
            except Exception as e:
                logger.warning(f"Failed to load server {name}: {e}")

        return servers

    def get_version(self, name: str) -> Optional[str]:
        """Get server version from manifest"""
        manifest = self.load_manifest()
        return manifest.servers.get(name) or manifest.devServers.get(name)

    def update_server_config(self, name: str, env_vars: Dict[str, str]):
        """Update server environment variables"""
        server = self.get_server(name)

        # Update env vars - replace entire dict to allow deletions
        if hasattr(server, "env"):
            server.env = env_vars if env_vars else {}
            self._save_server_config(name, server)
            logger.info(f"Updated config for {name}")
        else:
            raise ValueError(f"Server {name} does not support env vars")

    # Group operations
    def create_group(self, name: str, description: Optional[str] = None):
        """Create a group"""
        manifest = self.load_manifest()

        if name in manifest.groups:
            raise KeyError(f"Group already exists: {name}")

        manifest.groups[name] = []
        self._save_manifest(manifest)

        logger.info(f"Created group: {name}")

    def delete_group(self, name: str):
        """Delete a group and remove its tags from all servers"""
        manifest = self.load_manifest()

        if name not in manifest.groups:
            raise KeyError(f"Group not found: {name}")

        # Get servers in this group before deleting
        servers_in_group = manifest.groups[name]

        # Delete group from manifest
        del manifest.groups[name]
        self._save_manifest(manifest)

        # Remove group tag from all server config files
        for server_name in servers_in_group:
            try:
                server = self.get_server(server_name)
                if hasattr(server, "groups") and isinstance(server.groups, list):
                    if name in server.groups:
                        server.groups.remove(name)
                        self._save_server_config(server_name, server)
            except Exception as e:
                logger.warning(f"Could not update server {server_name}: {e}")

        logger.info(f"Deleted group: {name}")

    def rename_group(self, old_name: str, new_name: str):
        """Rename a group and update all server references"""
        manifest = self.load_manifest()

        if old_name not in manifest.groups:
            raise KeyError(f"Group not found: {old_name}")

        if new_name in manifest.groups:
            raise KeyError(f"Group already exists: {new_name}")

        # Rename in manifest
        manifest.groups[new_name] = manifest.groups[old_name]
        del manifest.groups[old_name]
        self._save_manifest(manifest)

        # Update server config files
        for server_name in manifest.groups[new_name]:
            try:
                server = self.get_server(server_name)
                if hasattr(server, "groups") and isinstance(server.groups, list):
                    if old_name in server.groups:
                        server.groups.remove(old_name)
                        server.groups.append(new_name)
                        self._save_server_config(server_name, server)
            except Exception as e:
                logger.warning(f"Could not update server {server_name}: {e}")

        logger.info(f"Renamed group {old_name} to {new_name}")

    def add_server_to_group(self, server_name: str, group_name: str):
        """Add server to group"""
        manifest = self.load_manifest()

        if group_name not in manifest.groups:
            raise KeyError(f"Group not found: {group_name}")

        if server_name not in manifest.servers and server_name not in manifest.devServers:
            raise KeyError(f"Server not found: {server_name}")

        added = False
        if server_name not in manifest.groups[group_name]:
            manifest.groups[group_name].append(server_name)
            self._save_manifest(manifest)
            added = True

        # Always update the server config file to include the group
        try:
            server = self.get_server(server_name)
            if hasattr(server, "groups") and isinstance(server.groups, list):
                if group_name not in server.groups:
                    server.groups.append(group_name)
                    self._save_server_config(server_name, server)
        except Exception as e:
            logger.warning(f"Could not update server groups: {e}")

        if added:
            logger.info(f"Added {server_name} to group {group_name}")

    def remove_server_from_group(self, server_name: str, group_name: str):
        """Remove server from group"""
        manifest = self.load_manifest()

        if group_name not in manifest.groups:
            raise KeyError(f"Group not found: {group_name}")

        if server_name in manifest.groups[group_name]:
            manifest.groups[group_name].remove(server_name)
            self._save_manifest(manifest)

            # Also update the server config file to remove the group
            try:
                server = self.get_server(server_name)
                if hasattr(server, "groups") and group_name in server.groups:
                    server.groups.remove(group_name)
                    self._save_server_config(server_name, server)
            except Exception as e:
                logger.warning(f"Could not update server groups: {e}")

        logger.info(f"Removed {server_name} from group {group_name}")

    def get_servers_in_group(self, group_name: str) -> Dict[str, ServerConfig]:
        """Get all servers in a group"""
        manifest = self.load_manifest()

        if group_name not in manifest.groups:
            raise KeyError(f"Group not found: {group_name}")

        servers = {}
        for server_name in manifest.groups[group_name]:
            try:
                servers[server_name] = self.get_server(server_name)
            except Exception as e:
                logger.warning(f"Failed to load server {server_name}: {e}")

        return servers

    def list_groups(self) -> Dict[str, List[str]]:
        """List all groups"""
        manifest = self.load_manifest()
        return manifest.groups

    def get_group(self, name: str) -> Optional[Dict]:
        """Get group metadata"""
        manifest = self.load_manifest()
        if name not in manifest.groups:
            return None
        return {"name": name, "description": None}

    def group_exists(self, name: str) -> bool:
        """Check if group exists"""
        manifest = self.load_manifest()
        return name in manifest.groups
