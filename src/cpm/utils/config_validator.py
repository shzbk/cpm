"""
Configuration validator - Check if servers are properly configured
"""

from typing import Dict, List, Tuple
from cpm.core.schema import ServerConfig


class ConfigValidator:
    """Validates server configurations and identifies missing variables"""

    @staticmethod
    def get_missing_vars(server_config: ServerConfig) -> List[str]:
        """
        Get list of missing environment variables (placeholders like ${VAR})

        Returns:
            List of variable names that need to be configured
        """
        if not hasattr(server_config, 'env') or not server_config.env:
            return []

        missing = []
        for var_name, value in server_config.env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                missing.append(var_name)

        return missing

    @staticmethod
    def is_configured(server_config: ServerConfig) -> bool:
        """Check if server is fully configured (no missing vars)"""
        return len(ConfigValidator.get_missing_vars(server_config)) == 0

    @staticmethod
    def get_configured_count(server_config: ServerConfig) -> Tuple[int, int]:
        """
        Get count of configured vs total env vars

        Returns:
            Tuple of (configured_count, total_count)
        """
        if not hasattr(server_config, 'env') or not server_config.env:
            return (0, 0)

        total = len(server_config.env)
        missing = len(ConfigValidator.get_missing_vars(server_config))
        configured = total - missing

        return (configured, total)

    @staticmethod
    def format_status(server_config: ServerConfig) -> str:
        """Get human-readable status string"""
        if not hasattr(server_config, 'env') or not server_config.env:
            return "[Ready] (no variables needed)"

        configured, total = ConfigValidator.get_configured_count(server_config)

        if configured == total:
            return "[Ready] ({}/{} configured)".format(configured, total)
        else:
            missing_count = total - configured
            if missing_count == 1:
                return "[Incomplete] ({}/{} configured - 1 missing)".format(configured, total)
            else:
                return "[Incomplete] ({}/{} configured - {} missing)".format(
                    configured, total, missing_count
                )


def get_config_status_for_display(servers: Dict[str, ServerConfig]) -> Dict[str, str]:
    """
    Get status for all servers for display in tables

    Returns:
        Dict mapping server name to short status
    """
    statuses = {}
    for name, config in servers.items():
        missing = ConfigValidator.get_missing_vars(config)

        if not missing:
            statuses[name] = "READY"
        elif len(missing) == 1:
            statuses[name] = "INCOMPLETE (1 missing)"
        else:
            statuses[name] = "INCOMPLETE ({} missing)".format(len(missing))

    return statuses
