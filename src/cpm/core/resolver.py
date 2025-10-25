"""
ServerNameResolver - Maps simple names to full reverse-DNS registry names

Handles:
- Resolving simple names (mysql) to full names (io.github.user/mysql)
- Caching resolved names locally
- Interactive disambiguation for multiple matches
- Direct passthrough for full names
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class ServerNameResolver:
    """
    Resolves simple server names to full reverse-DNS format.

    MCP registry uses reverse-DNS naming: io.github.user/servername
    CPM users want simple names: mysql, brave-search

    This resolver bridges the gap:
    - mysql -> searches registry, finds io.github.user/mysql
    - io.github.user/mysql -> passes through unchanged
    - ambiguous names -> prompts user to clarify
    """

    def __init__(
        self,
        registry_client,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize resolver.

        Args:
            registry_client: RegistryClient instance for looking up servers
            cache_dir: Optional directory for caching resolved names
        """

        self.registry = registry_client
        self.cache_dir = cache_dir or Path.home() / ".config" / "cpm" / "cache"
        self.cache_file = self.cache_dir / "name_resolution.json"
        self._cache: Dict[str, str] = {}
        self._load_cache()

    def resolve(self, name: str) -> str:
        """
        Resolve a name to full registry format.

        Args:
            name: Simple name (mysql) or full name (io.github.user/mysql)

        Returns:
            Full reverse-DNS name (io.github.user/mysql)

        Raises:
            ValueError: If name cannot be resolved
            KeyboardInterrupt: If user cancels disambiguation
        """

        # If already in full format, return as-is
        if "/" in name:
            logger.debug(f"Name already in full format: {name}")
            return name

        # Check cache first
        if name in self._cache:
            logger.debug(f"Found {name} in cache: {self._cache[name]}")
            return self._cache[name]

        # Search registry
        logger.debug(f"Searching registry for: {name}")
        matches = self._search_registry(name)

        if len(matches) == 0:
            raise ValueError(f"No server found matching '{name}'")

        elif len(matches) == 1:
            # Single match - cache and return
            full_name = matches[0]["name"]
            self._cache[name] = full_name
            self._save_cache()
            logger.debug(f"Resolved {name} -> {full_name}")
            return full_name

        else:
            # Multiple matches - ask user
            full_name = self._prompt_user_selection(name, matches)
            self._cache[name] = full_name
            self._save_cache()
            logger.debug(f"Resolved {name} -> {full_name} (user selection)")
            return full_name

    def _search_registry(self, query: str) -> List[Dict]:
        """
        Search registry for servers matching the query.

        Searches for:
        1. Servers with simple name containing query
        2. Servers with description containing query
        3. Exact namespace matches

        Returns:
            List of matching server dicts with 'name' and 'description'
        """

        try:
            # Get all servers from registry
            all_servers = self.registry.get_servers()

            # Build unique server list (registry returns multiple versions)
            unique_servers = {}
            for server_response in all_servers:
                if isinstance(server_response, dict):
                    server = server_response.get("server", server_response)
                else:
                    server = server_response

                server_name = server.get("name", "")
                if server_name not in unique_servers:
                    unique_servers[server_name] = server

            # Search for matches
            matches = []
            query_lower = query.lower()

            for server_name, server_data in unique_servers.items():
                simple_name = server_name.split("/")[-1] if "/" in server_name else server_name

                # Match criteria
                matches_simple = query_lower in simple_name.lower()
                matches_full = query_lower in server_name.lower()
                matches_desc = query_lower in server_data.get("description", "").lower()

                if matches_simple or matches_full or matches_desc:
                    matches.append({
                        "name": server_name,
                        "description": server_data.get("description", ""),
                        "version": server_data.get("version", ""),
                    })

            # Sort results - exact simple name matches first
            matches.sort(
                key=lambda x: (
                    x["name"].split("/")[-1].lower() != query_lower,  # Exact match first
                    x["name"].lower() != query_lower,  # Then full name match
                    len(x["name"]),  # Then shorter names
                )
            )

            logger.debug(f"Found {len(matches)} servers matching '{query}'")
            return matches

        except Exception as e:
            logger.error(f"Error searching registry: {e}")
            raise

    def _prompt_user_selection(
        self,
        query: str,
        matches: List[Dict],
        max_show: int = 10,
    ) -> str:
        """
        Prompt user to select from matching servers.

        Shows up to max_show matches with descriptions.
        Returns the selected full server name.
        """

        console.print(
            f"\n[yellow]Multiple servers match '[bold]{query}[/bold]':[/yellow]\n"
        )

        # Show matches
        shown_matches = matches[:max_show]
        for i, match in enumerate(shown_matches, 1):
            desc = match["description"][:60]
            if len(match["description"]) > 60:
                desc += "..."

            console.print(f"  [cyan]{i}[/cyan]. {match['name']}")
            console.print(f"     [dim]{desc}[/dim]")
            console.print()

        if len(matches) > max_show:
            console.print(
                f"  [dim]... and {len(matches) - max_show} more[/dim]\n"
            )

        # Get user choice
        while True:
            try:
                choice = console.input(
                    "[bold]Select server (number) or (q) to quit:[/bold] "
                ).strip()

                if choice.lower() in ("q", "quit", "exit"):
                    raise KeyboardInterrupt("User cancelled")

                choice_num = int(choice) - 1
                if 0 <= choice_num < len(shown_matches):
                    return shown_matches[choice_num]["name"]
                else:
                    console.print(f"[red]Invalid choice: {choice}[/red]")

            except ValueError:
                console.print("[red]Please enter a valid number[/red]")

    def _load_cache(self) -> None:
        """Load cached name resolutions from disk."""

        if not self.cache_file.exists():
            self._cache = {}
            return

        try:
            with open(self.cache_file, "r") as f:
                self._cache = json.load(f)
            logger.debug(f"Loaded {len(self._cache)} cached name resolutions")
        except Exception as e:
            logger.warning(f"Could not load resolution cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save name resolutions to cache file."""

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)
            logger.debug(f"Saved {len(self._cache)} name resolutions to cache")
        except Exception as e:
            logger.warning(f"Could not save resolution cache: {e}")

    def clear_cache(self) -> None:
        """Clear the resolution cache."""

        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cleared name resolution cache")

    def get_cached_name(self, simple_name: str) -> Optional[str]:
        """Get cached full name for simple name, if available."""

        return self._cache.get(simple_name)

    def cache_resolution(self, simple_name: str, full_name: str) -> None:
        """Manually cache a name resolution."""

        self._cache[simple_name] = full_name
        self._save_cache()
