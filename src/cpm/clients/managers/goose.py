"""
Goose CLI client manager
"""

import logging
import os
from typing import Any, Dict, List, Optional

from cpm.clients.base import YAMLClientManager
from cpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class GooseManager(YAMLClientManager):
    """Manages Goose CLI MCP server configurations"""

    client_key = "goose"
    display_name = "Goose CLI"
    download_url = "https://github.com/block/goose"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)
        # Customize YAML formatting
        self.yaml_handler.indent(mapping=2, sequence=0, offset=0)
        self.yaml_handler.preserve_quotes = True

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "goose", "config.yaml")
            else:  # macOS or Linux
                self.config_path = os.path.expanduser("~/.config/goose/config.yaml")

            # Prefer workspace config if it exists
            workspace_config = os.path.join(os.getcwd(), ".goose", "config.yaml")
            if os.path.exists(workspace_config):
                self.config_path = workspace_config

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Goose"""
        return {"extensions": {}}

    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get server config from extensions"""
        return config.get("extensions", {}).get(server_name)

    def _get_all_server_names(self, config: Dict[str, Any]) -> List[str]:
        """Get all server names"""
        return list(config.get("extensions", {}).keys())

    def _add_server_to_config(
        self, config: Dict[str, Any], server_name: str, server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add server to extensions"""
        if "extensions" not in config:
            config["extensions"] = {}
        config["extensions"][server_name] = server_config
        return config

    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove server from extensions"""
        if "extensions" in config and server_name in config["extensions"]:
            del config["extensions"][server_name]
        return config

    def _normalize_server_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Goose config format"""
        normalized = dict(server_config)
        # Map Goose-specific fields to standard fields
        if "cmd" in normalized:
            normalized["command"] = normalized.pop("cmd")
        if "envs" in normalized:
            normalized["env"] = normalized.pop("envs")
        return normalized

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert to Goose format"""
        if isinstance(server_config, STDIOServerConfig):
            result = {
                "cmd": server_config.command,
                "args": server_config.args,
                "type": "stdio",
                "name": server_config.name,
                "enabled": True,
            }
            if server_config.env:
                result["envs"] = {k: v for k, v in server_config.env.items() if v}
            return result
        else:
            result = server_config.model_dump()
            result["type"] = "sse"
            result["name"] = server_config.name
            result["enabled"] = True
            return result
