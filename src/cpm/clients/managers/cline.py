"""
Cline client manager
"""

import logging
import os

from cpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class ClineManager(JSONClientManager):
    """Manages Cline MCP server configurations"""

    client_key = "cline"
    display_name = "Cline"
    download_url = "https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser(
                    "~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
                )
            elif self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("APPDATA", ""),
                    "Code",
                    "User",
                    "globalStorage",
                    "saoudrizwan.claude-dev",
                    "settings",
                    "cline_mcp_settings.json",
                )
            else:  # Linux
                self.config_path = os.path.expanduser(
                    "~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
                )
