"""
Info command - Show detailed server information
"""

import click
from rich.console import Console
from rich.panel import Panel

from cpm.core import RegistryClient

console = Console()
registry = RegistryClient()


@click.command()
@click.argument("server_name")
def info(server_name: str):
    """
    Show detailed information about a server

    Examples:

        cpm info brave-search
        cpm info filesystem
    """
    # Get server from registry
    server = registry.get_server(server_name)

    if not server:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in registry")
        return

    # Display server info
    display_name = server.get("display_name", server_name)
    description = server.get("description", "No description available")
    author = server.get("author", {})
    tags = server.get("tags", [])
    categories = server.get("categories", [])

    # Build info panel
    info_text = f"[bold]{display_name}[/]\n\n"
    info_text += f"{description}\n\n"

    if author:
        author_name = author.get("name", "Unknown")
        author_url = author.get("url", "")
        info_text += f"[dim]Author:[/] {author_name}"
        if author_url:
            info_text += f" ({author_url})"
        info_text += "\n"

    if tags:
        info_text += f"[dim]Tags:[/] {', '.join(tags)}\n"

    if categories:
        info_text += f"[dim]Categories:[/] {', '.join(categories)}\n"

    panel = Panel(info_text, title="Server Information", border_style="cyan")
    console.print(panel)

    # Show installation info
    installations = server.get("installations", {})
    if installations:
        console.print("\n[bold]Installation Methods:[/]")
        for key, method in installations.items():
            method_type = method.get("type", "unknown")
            recommended = " [green](recommended)[/]" if method.get("recommended") else ""
            console.print(f"  * {key}: [dim]{method_type}[/]{recommended}")

    console.print(f"\n[dim]Install:[/] [cyan]cpm install {server_name}[/]")
