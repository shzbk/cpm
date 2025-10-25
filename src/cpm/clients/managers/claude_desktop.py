"""
Claude Desktop client manager
"""

import logging
import os
from typing import Any, Dict

from cpm.clients.base import JSONClientManager
from cpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class ClaudeDesktopManager(JSONClientManager):
    """Manages Claude Desktop MCP server configurations"""

    client_key = "claude-desktop"
    display_name = "Claude Desktop"
    download_url = "https://claude.ai/download"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser(
                    "~/Library/Application Support/Claude/claude_desktop_config.json"
                )
            elif self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json"
                )
            else:  # Linux
                self.config_path = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert to Claude Desktop format (stdio only currently)"""
        # Check if this is a remote server (has url but no command)
        if hasattr(server_config, 'url') and server_config.url and not (hasattr(server_config, 'command') and server_config.command):
            # Claude Desktop doesn't support remote servers
            logger.warning(f"Claude Desktop doesn't support remote servers, skipping {server_config.name}")
            return {}
        return super().to_client_format(server_config)
