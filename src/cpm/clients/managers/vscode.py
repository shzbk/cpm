"""
VSCode client manager
"""

import json
import logging
import os
from typing import Any, Dict

from cpm.clients.base import JSONClientManager
from cpm.core.schema import STDIOServerConfig

logger = logging.getLogger(__name__)


class VSCodeManager(JSONClientManager):
    """Manages VSCode MCP server configurations"""

    client_key = "vscode"
    display_name = "VSCode"
    download_url = "https://code.visualstudio.com/"
    configure_key_name = "servers"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "settings.json")
            elif self._system == "Darwin":
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")
            else:  # Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/settings.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load VSCode config (nested under 'mcp' key)"""
        empty_config = {"mcp": {self.configure_key_name: {}}}

        if not os.path.exists(self.config_path):
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "mcp" not in config:
                    config["mcp"] = {}
                if self.configure_key_name not in config["mcp"]:
                    config["mcp"][self.configure_key_name] = {}
                return config["mcp"]
        except Exception as e:
            logger.error(f"Error loading VSCode config: {e}")
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save VSCode config (merge with existing settings)"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Load existing config
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    current_config = json.load(f)
            else:
                current_config = {}

            # Update mcp section
            current_config["mcp"] = config

            # Save
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving VSCode config: {e}")
            return False

    def to_client_format(self, server_config) -> Dict[str, Any]:
        """Convert to VSCode format (requires 'type' field)"""
        if isinstance(server_config, STDIOServerConfig):
            result = {
                "type": "stdio",
                "command": server_config.command,
                "args": server_config.args,
            }
            if server_config.env:
                result["env"] = {k: v for k, v in server_config.env.items() if v}
            return result
        else:
            return super().to_client_format(server_config)
