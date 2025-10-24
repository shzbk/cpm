"""
Continue extension client manager
"""

import logging
import os
from typing import Any, Dict, List, Optional

from cpm.clients.base import YAMLClientManager
from cpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class ContinueManager(YAMLClientManager):
    """Manages Continue MCP server configurations"""

    client_key = "continue"
    display_name = "Continue"
    download_url = "https://marketplace.visualstudio.com/items?itemName=Continue.continue"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)
        # Customize YAML formatting
        self.yaml_handler.indent(mapping=2, sequence=4, offset=2)
        self.yaml_handler.preserve_quotes = True

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("USERPROFILE", ""), ".continue", "config.yaml")
            else:  # macOS or Linux
                self.config_path = os.path.expanduser("~/.continue/config.yaml")

            # Prefer workspace config if it exists
            workspace_config = os.path.join(os.getcwd(), ".continue", "config.yaml")
            if os.path.exists(workspace_config):
                self.config_path = workspace_config

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Continue"""
        return {
            "name": "Local Assistant",
            "version": "1.0.0",
            "schema": "v1",
            "models": [],
            "mcpServers": [],
        }

    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get server config from list"""
        for server in config.get("mcpServers", []):
            if server.get("name") == server_name:
                return server
        return None

    def _get_all_server_names(self, config: Dict[str, Any]) -> List[str]:
        """Get all server names"""
        return [s.get("name") for s in config.get("mcpServers", []) if s.get("name")]

    def _add_server_to_config(
        self, config: Dict[str, Any], server_name: str, server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add server to list"""
        if "name" not in server_config:
            server_config["name"] = server_name

        if "mcpServers" not in config:
            config["mcpServers"] = []

        # Update existing or append new
        for i, server in enumerate(config["mcpServers"]):
            if server.get("name") == server_name:
                config["mcpServers"][i] = server_config
                return config

        config["mcpServers"].append(server_config)
        return config

    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove server from list"""
        config["mcpServers"] = [s for s in config.get("mcpServers", []) if s.get("name") != server_name]
        return config
