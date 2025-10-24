"""
Windsurf client manager
"""

import logging
import os
from typing import Any, Dict

from cpm.clients.base import JSONClientManager
from cpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class WindsurfManager(JSONClientManager):
    """Manages Windsurf MCP server configurations"""

    client_key = "windsurf"
    display_name = "Windsurf"
    download_url = "https://codeium.com/windsurf/download"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("USERPROFILE", ""), ".codeium", "windsurf", "mcp_config.json"
                )
            else:  # macOS or Linux
                self.config_path = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert to Windsurf format (uses 'serverUrl' instead of 'url')"""
        if isinstance(server_config, STDIOServerConfig):
            return super().to_client_format(server_config)
        else:
            result = server_config.model_dump()
            result["serverUrl"] = result.pop("url")
            return result

    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert from Windsurf format"""
        if "serverUrl" in client_config:
            client_config["url"] = client_config.pop("serverUrl")
        return super().from_client_format(server_name, client_config)
