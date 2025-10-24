"""
Search command - Find servers in registry
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core import RegistryClient

console = Console(legacy_windows=False)
registry = RegistryClient()


@click.command()
@click.argument("query", required=False)
@click.option("--tag", multiple=True, help="Filter by tag")
@click.option("--category", multiple=True, help="Filter by category")
def search(query: str, tag: tuple, category: tuple):
    """
    Search for MCP servers in the registry

    Examples:

        cpm search
        cpm search "web search"
        cpm search --tag productivity
        cpm search database --category data
    """
    # Search registry
    results = registry.search_servers(
        query=query,
        tags=list(tag) if tag else None,
        categories=list(category) if category else None,
    )

    if not results:
        console.print("[yellow]No servers found[/]")
        return

    # Display results
    table = Table(title=f"Registry Search Results ({len(results)} servers)")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="dim", no_wrap=False)
    table.add_column("Tags", style="yellow")

    for server in results[:20]:  # Limit to 20 results
        name = server.get("name", "")
        description = server.get("description", "")[:60]
        # Sanitize description to handle encoding issues
        description = description.encode('ascii', 'ignore').decode('ascii') + "..."
        tags = ", ".join(server.get("tags", [])[:3])

        table.add_row(name, description, tags)

    console.print(table)

    if len(results) > 20:
        console.print(f"\n[dim]... and {len(results) - 20} more[/]")

    console.print(f"\n[dim]Install:[/] [cyan]cpm install <server-name>[/]")
