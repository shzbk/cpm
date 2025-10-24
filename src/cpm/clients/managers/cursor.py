"""
Cursor client manager
"""

import logging
import os
from typing import Any, Dict

from cpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class CursorManager(JSONClientManager):
    """Manages Cursor MCP server configurations"""

    client_key = "cursor"
    display_name = "Cursor"
    download_url = "https://cursor.sh/download"

    def __init__(self, config_path_override: str = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Platform-specific config paths
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("USERPROFILE", ""), ".cursor", "mcp.json")
            else:  # macOS or Linux
                self.config_path = os.path.expanduser("~/.cursor/mcp.json")
