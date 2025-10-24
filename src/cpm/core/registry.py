"""
Registry client for fetching MCP servers from the central registry
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Default registry configuration
DEFAULT_REGISTRY_URL = "http://localhost:8000/api/servers.json"
DEFAULT_CACHE_DIR = Path.home() / ".config" / "cpm" / "cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "registry.json"
CACHE_TTL = timedelta(hours=1)


class RegistryClient:
    """
    Client for interacting with the CPM registry

    Features:
    - Fetch server metadata from central registry
    - Local caching with TTL
    - Search and filter servers
    """

    def __init__(
        self,
        registry_url: str = DEFAULT_REGISTRY_URL,
        cache_file: Optional[Path] = None,
    ):
        self.registry_url = registry_url
        self.cache_file = cache_file or DEFAULT_CACHE_FILE
        self.cache_dir = self.cache_file.parent
        self._servers_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._ensure_cache_dir()
        self._load_cache()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> None:
        """Load cached registry data from disk"""
        if not self.cache_file.exists():
            logger.debug("No cache file found")
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._servers_cache = data.get("servers")
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    # Remove timezone info to make it naive for comparison
                    self._cache_timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=None)
                logger.debug(f"Loaded cache from {self.cache_file}")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def _save_cache(self) -> None:
        """Save registry data to cache file"""
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
            logger.debug(f"Saved cache to {self.cache_file}")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._servers_cache or not self._cache_timestamp:
            return False
        age = datetime.now() - self._cache_timestamp
        return age < CACHE_TTL

    def _fetch_from_registry(self) -> Dict[str, Dict[str, Any]]:
        """Fetch server data from registry"""
        try:
            logger.debug(f"Fetching from registry: {self.registry_url}")
            response = requests.get(self.registry_url, timeout=10)
            response.raise_for_status()
            servers = response.json()

            self._servers_cache = servers
            self._cache_timestamp = datetime.now()
            self._save_cache()

            return servers
        except requests.RequestException as e:
            logger.error(f"Failed to fetch from registry: {e}")
            # Return cached data if available, even if stale
            return self._servers_cache or {}

    def get_servers(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get all servers from registry

        Args:
            force_refresh: Force fetch from registry, ignore cache

        Returns:
            Dictionary of server name -> server metadata
        """
        if force_refresh or not self._is_cache_valid():
            return self._fetch_from_registry()
        return self._servers_cache or {}

    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific server"""
        servers = self.get_servers()
        return servers.get(server_name)

    def search_servers(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for servers in the registry

        Args:
            query: Search query (matches name, description, display_name)
            tags: Filter by tags
            categories: Filter by categories

        Returns:
            List of matching server metadata
        """
        servers = self.get_servers()
        results = list(servers.values())

        # Filter by query
        if query:
            query_lower = query.lower()
            filtered = []
            for server in results:
                # Check name, description, display_name
                if (
                    query_lower in server.get("name", "").lower()
                    or query_lower in server.get("description", "").lower()
                    or query_lower in server.get("display_name", "").lower()
                ):
                    filtered.append(server)
                    continue

                # Check tags
                if "tags" in server and any(query_lower in tag.lower() for tag in server["tags"]):
                    filtered.append(server)
                    continue

                # Check categories
                if "categories" in server and any(query_lower in cat.lower() for cat in server["categories"]):
                    filtered.append(server)
                    continue

            results = filtered

        # Filter by tags
        if tags:
            results = [
                server
                for server in results
                if "tags" in server and any(tag in server["tags"] for tag in tags)
            ]

        # Filter by categories
        if categories:
            results = [
                server
                for server in results
                if "categories" in server and any(cat in server["categories"] for cat in categories)
            ]

        return results

    def refresh_cache(self) -> bool:
        """Force refresh the cache from registry"""
        try:
            self._fetch_from_registry()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            return False
