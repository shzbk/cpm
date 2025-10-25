"""
RegistryClient v2 - Client for MCP Official Registry

Fetches servers from the official MCP registry at https://registry.modelcontextprotocol.io
Returns MCPServerConfig objects matching the official schema.

Features:
- Pagination support with cursors
- Version management
- Local caching with TTL
- Graceful fallback to cached data
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from cpm.core.schema import MCPServerConfig

logger = logging.getLogger(__name__)

# Default configuration for official registry
DEFAULT_REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
DEFAULT_CACHE_DIR = Path.home() / ".config" / "cpm" / "cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "official_registry.json"
CACHE_TTL = timedelta(hours=1)


class RegistryClient:
    """
    Client for the official MCP Registry.

    Fetches server metadata from https://registry.modelcontextprotocol.io
    and caches responses locally.

    All returned servers conform to MCPServerConfig (official schema).
    """

    def __init__(
        self,
        registry_url: str = DEFAULT_REGISTRY_URL,
        cache_file: Optional[Path] = None,
        cache_ttl: Optional[timedelta] = None,
    ):
        """
        Initialize registry client.

        Args:
            registry_url: Base URL of registry (defaults to official)
            cache_file: Location for caching registry data
            cache_ttl: Cache time-to-live (default 1 hour)
        """

        self.registry_url = registry_url
        self.cache_file = cache_file or DEFAULT_CACHE_FILE
        self.cache_dir = self.cache_file.parent
        self.cache_ttl = cache_ttl or CACHE_TTL

        self._servers_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._ensure_cache_dir()
        self._load_cache()

    # ========================================================================
    # Public API
    # ========================================================================

    def get_server(
        self,
        server_name: str,
        version: Optional[str] = None,
    ) -> MCPServerConfig:
        """
        Get a specific server by name.

        Args:
            server_name: Full reverse-DNS name (io.github.user/server)
            version: Optional specific version (defaults to latest)

        Returns:
            MCPServerConfig for the server

        Raises:
            ValueError: If server not found
        """

        servers = self.get_servers()

        # Find all versions of this server
        matching_servers = []
        for server_data in servers:
            server = server_data.get("server", {})
            if server.get("name") == server_name:
                matching_servers.append(server)

        if not matching_servers:
            raise ValueError(f"Server not found: {server_name}")

        # Sort by version (newest first)
        matching_servers.sort(
            key=lambda s: self._parse_version(s.get("version", "0.0.0")),
            reverse=True,
        )

        # Select version
        if version and version != "latest":
            for server in matching_servers:
                if server.get("version") == version:
                    return MCPServerConfig(**server)
            raise ValueError(
                f"Version {version} not found for server {server_name}"
            )

        # Return latest
        if matching_servers:
            return MCPServerConfig(**matching_servers[0])

        raise ValueError(f"No versions found for server {server_name}")

    def get_servers(
        self,
        force_refresh: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get all servers from registry.

        Args:
            force_refresh: Force fetch from registry, ignore cache
            limit: Limit results (fetches all if not specified)

        Returns:
            List of server response dicts (with 'server' and '_meta' keys)
        """

        if force_refresh or not self._is_cache_valid():
            self._fetch_all_servers(limit=limit)

        return self._servers_cache or []

    def search_servers(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Search for servers in registry.

        Args:
            query: Search query (matches name, description)
            limit: Limit results

        Returns:
            List of matching server response dicts
        """

        servers = self.get_servers(limit=limit)

        if not query:
            return servers

        # Filter by query
        query_lower = query.lower()
        results = []

        for server_data in servers:
            server = server_data.get("server", {})

            # Check fields
            name = server.get("name", "").lower()
            description = server.get("description", "").lower()
            title = server.get("title", "").lower()

            if (
                query_lower in name
                or query_lower in description
                or query_lower in title
            ):
                results.append(server_data)

        return results

    def get_versions(
        self,
        server_name: str,
    ) -> List[str]:
        """
        Get all available versions of a server.

        Args:
            server_name: Full reverse-DNS name

        Returns:
            List of version strings (newest first)
        """

        servers = self.get_servers()

        # Find all versions
        versions = []
        for server_data in servers:
            server = server_data.get("server", {})
            if server.get("name") == server_name:
                version = server.get("version")
                if version:
                    versions.append(version)

        # Sort (newest first)
        versions.sort(
            key=self._parse_version,
            reverse=True,
        )

        return versions

    def refresh_cache(self) -> bool:
        """Force refresh cache from registry."""

        try:
            self._fetch_all_servers()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh registry cache: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear local cache."""

        self._servers_cache = None
        self._cache_timestamp = None
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cleared registry cache")

    # ========================================================================
    # Private Methods - Caching
    # ========================================================================

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> None:
        """Load cached registry data from disk."""

        if not self.cache_file.exists():
            logger.debug("No cache file found")
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._servers_cache = data.get("servers", [])
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    self._cache_timestamp = datetime.fromisoformat(timestamp_str)
            logger.debug(
                f"Loaded {len(self._servers_cache or [])} servers from cache"
            )
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")

    def _save_cache(self) -> None:
        """Save registry data to cache file."""

        if not self._servers_cache:
            return

        try:
            self._ensure_cache_dir()
            data = {
                "servers": self._servers_cache,
                "timestamp": datetime.now().isoformat(),
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self._servers_cache)} servers to cache")
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""

        if not self._servers_cache or not self._cache_timestamp:
            return False

        age = datetime.now() - self._cache_timestamp
        return age < self.cache_ttl

    # ========================================================================
    # Private Methods - Fetching
    # ========================================================================

    def _fetch_all_servers(self, limit: Optional[int] = None) -> None:
        """
        Fetch all servers from registry with pagination support.

        Args:
            limit: Optional limit on total servers to fetch
        """

        logger.debug(f"Fetching servers from registry: {self.registry_url}")
        all_servers = []
        cursor = None
        fetch_count = 0

        try:
            while True:
                # Build URL with cursor if needed
                url = self.registry_url
                params = {}
                if cursor:
                    params["cursor"] = cursor

                # Fetch page
                response = requests.get(
                    url,
                    params=params if params else None,
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()

                # Add servers from this page
                servers = data.get("servers", [])
                all_servers.extend(servers)
                fetch_count += len(servers)

                logger.debug(f"Fetched {len(servers)} servers, total: {fetch_count}")

                # Check if we've reached limit
                if limit and fetch_count >= limit:
                    all_servers = all_servers[:limit]
                    break

                # Check for next page
                cursor = data.get("metadata", {}).get("nextCursor")
                if not cursor:
                    break

                logger.debug(f"Fetching next page with cursor: {cursor[:20]}...")

            # Update cache
            self._servers_cache = all_servers
            self._cache_timestamp = datetime.now()
            self._save_cache()

            logger.info(f"Successfully fetched {len(all_servers)} servers from registry")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch from registry: {e}")
            # Return cached data if available
            if self._servers_cache:
                logger.info("Using stale cache due to network error")
            else:
                raise

    # ========================================================================
    # Private Methods - Utilities
    # ========================================================================

    @staticmethod
    def _parse_version(version_str: str) -> Tuple[int, ...]:
        """
        Parse semantic version string for sorting.

        Returns tuple of integers for comparison.
        Falls back to string comparison if not valid semver.
        """

        try:
            # Remove pre-release/build metadata
            base_version = version_str.split("-")[0].split("+")[0]
            parts = base_version.split(".")
            return tuple(int(p) for p in parts[:3])  # major.minor.patch
        except (ValueError, IndexError):
            # Not valid semver - return zeros for sorting
            logger.debug(f"Could not parse version: {version_str}")
            return (0, 0, 0)
