"""
Client registry - Central registry of all MCP client managers
"""

import logging
from typing import Dict, List, Optional

from cpm.clients.base import BaseClientManager

logger = logging.getLogger(__name__)


class ClientRegistry:
    """
    Registry of all supported MCP client managers

    Provides client detection, instantiation, and management
    """

    _CLIENT_MANAGERS: Dict[str, type] = {}

    @classmethod
    def register(cls):
        """Register all client managers"""
        # Import managers here to avoid circular imports
        from cpm.clients.managers.claude_desktop import ClaudeDesktopManager
        from cpm.clients.managers.cline import ClineManager
        from cpm.clients.managers.continue_ext import ContinueManager
        from cpm.clients.managers.cursor import CursorManager
        from cpm.clients.managers.goose import GooseManager
        from cpm.clients.managers.vscode import VSCodeManager
        from cpm.clients.managers.windsurf import WindsurfManager

        cls._CLIENT_MANAGERS = {
            "claude-desktop": ClaudeDesktopManager,
            "cursor": CursorManager,
            "windsurf": WindsurfManager,
            "vscode": VSCodeManager,
            "cline": ClineManager,
            "continue": ContinueManager,
            "goose": GooseManager,
        }

    @classmethod
    def get_client_manager(
        cls, client_name: str, config_path_override: Optional[str] = None
    ) -> Optional[BaseClientManager]:
        """
        Get a client manager instance

        Args:
            client_name: Name of the client
            config_path_override: Optional path override

        Returns:
            Client manager instance or None
        """
        if not cls._CLIENT_MANAGERS:
            cls.register()

        manager_class = cls._CLIENT_MANAGERS.get(client_name)
        if manager_class:
            return manager_class(config_path_override=config_path_override)
        return None

    @classmethod
    def get_all_client_managers(cls) -> Dict[str, BaseClientManager]:
        """
        Get all client managers

        Returns:
            Dictionary of client name to manager instance
        """
        if not cls._CLIENT_MANAGERS:
            cls.register()

        return {name: manager() for name, manager in cls._CLIENT_MANAGERS.items()}

    @classmethod
    def detect_installed_clients(cls) -> Dict[str, bool]:
        """
        Detect which clients are installed

        Returns:
            Dictionary of client name to installed status
        """
        if not cls._CLIENT_MANAGERS:
            cls.register()

        return {
            client_name: manager().is_client_installed()
            for client_name, manager in cls._CLIENT_MANAGERS.items()
        }

    @classmethod
    def get_client_info(cls, client_name: str) -> Dict[str, str]:
        """
        Get client display information

        Args:
            client_name: Name of the client

        Returns:
            Dictionary with client info
        """
        manager = cls.get_client_manager(client_name)
        if manager:
            return manager.get_client_info()
        return {}

    @classmethod
    def get_all_client_info(cls) -> Dict[str, Dict[str, str]]:
        """
        Get display information for all clients

        Returns:
            Dictionary of client name to info
        """
        if not cls._CLIENT_MANAGERS:
            cls.register()

        return {
            client_name: manager().get_client_info()
            for client_name, manager in cls._CLIENT_MANAGERS.items()
        }

    @classmethod
    def get_supported_clients(cls) -> List[str]:
        """
        Get list of supported client names

        Returns:
            List of client names
        """
        if not cls._CLIENT_MANAGERS:
            cls.register()

        return list(cls._CLIENT_MANAGERS.keys())
