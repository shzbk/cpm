"""
Uninstall command - Remove MCP servers
"""

import click
from rich.console import Console

from cpm.core.context import ConfigContext
from cpm.clients.registry import ClientRegistry

console = Console()


@click.command()
@click.argument("server_names", nargs=-1, required=True)
@click.option("--local", is_flag=True, help="Remove from local project (cpm.json)")
@click.option("--purge", is_flag=True, help="Also remove from all MCP clients")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def uninstall(ctx, server_names: tuple, local: bool, purge: bool, yes: bool):
    """
    Uninstall MCP server(s)

    Removes servers from configuration. Use --purge to also remove from all clients.

    Examples:

        \b
        cpm uninstall mysql                           # Remove from global
        cpm uninstall mysql --local                   # Remove from cpm.json
        cpm uninstall mysql --purge                   # Remove + purge from clients
        cpm uninstall mysql brave-search              # Remove multiple servers
    """
    # Get config context
    config = ConfigContext(local=local or ctx.obj.get("local", False))

    # Track results
    removed_count = 0
    failed_count = 0

    for server_name in server_names:
        # Check if server exists
        try:
            server = config.get_server(server_name)
        except KeyError:
            console.print(f"[yellow]Warning: Server '{server_name}' is not installed[/]")
            failed_count += 1
            continue

        # Confirm if not --yes
        if not yes and len(server_names) == 1:
            console.print(f"\n[yellow]Remove '{server_name}'?[/]")
            if purge:
                console.print("[dim]This will also remove it from all MCP clients[/]")

            if not click.confirm("Continue?", default=True):
                console.print("[yellow]Aborted[/]")
                return

        # Remove server
        try:
            config.remove_server(server_name)
            console.print(f"[green]+[/] Uninstalled [cyan]{server_name}[/]")
            removed_count += 1

            # Purge from clients if requested
            if purge:
                try:
                    client_registry = ClientRegistry()
                    detected_clients = client_registry.detect_installed_clients()

                    if detected_clients:
                        console.print(f"[cyan]Removing from clients...[/]")

                        for client_name, client_manager in detected_clients.items():
                            try:
                                if client_manager.has_server(server_name):
                                    client_manager.remove_server(server_name)
                                    console.print(f"  [green]+[/] Removed from {client_name}")
                            except Exception as e:
                                console.print(f"  [red]-[/] Failed to remove from {client_name}: {e}")

                        console.print(f"[dim]Restart your MCP clients to apply changes[/]")

                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to purge from clients: {e}[/]")

        except Exception as e:
            console.print(f"[red]-[/] Failed to uninstall {server_name}: {e}")
            failed_count += 1

    # Summary
    if len(server_names) > 1:
        console.print(f"\n[green]Uninstalled {removed_count}/{len(server_names)} server(s)[/]")
        if failed_count > 0:
            console.print(f"[yellow]{failed_count} failed[/]")
