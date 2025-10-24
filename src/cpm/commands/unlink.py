"""
Unlink local server
"""

import click
from rich.console import Console

from cpm.core.config import GlobalConfigManager
from cpm.core.registry import RegistryClient

console = Console()


@click.command()
@click.argument("server")
@click.option("--restore", is_flag=True, help="Restore registry version after unlinking")
def unlink(server, restore):
    """
    Unlink local server

    Removes a linked local server from global configuration.
    Optionally restores the registry version.

    Examples:

        \b
        cpm unlink my-server                  # Unlink server
        cpm unlink my-server --restore        # Unlink and restore registry version
    """
    config_manager = GlobalConfigManager()

    # Check if server exists
    try:
        server_config = config_manager.get_server(server)
    except KeyError:
        console.print(f"[red]Error:[/] Server not found: {server}")
        raise click.Abort()

    # Check if it's a linked server
    if hasattr(server_config, "version") and server_config.version == "linked":
        console.print(f"[cyan]Unlinking {server}...[/]\n")
    else:
        console.print(f"[yellow]Warning:[/] {server} is not a linked server")
        if not click.confirm("Remove anyway?", default=False):
            console.print("[yellow]Aborted[/]")
            return

    # Remove server
    try:
        config_manager.remove_server(server)
        console.print(f"[green]+[/] Unlinked {server}")

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to unlink server: {e}")
        raise click.Abort()

    # Restore registry version if requested
    if restore:
        console.print(f"\n[cyan]Restoring registry version...[/]\n")

        try:
            registry = RegistryClient()
            server_metadata = registry.get_server(server)

            # Parse server config from metadata
            from cpm.core.schema import STDIOServerConfig, RemoteServerConfig

            if "command" in server_metadata:
                new_config = STDIOServerConfig(**server_metadata)
            elif "url" in server_metadata:
                new_config = RemoteServerConfig(**server_metadata)
            else:
                console.print(f"[red]Error:[/] Invalid server metadata from registry")
                return

            # Add server from registry
            config_manager.add_server(new_config)
            console.print(f"[green]+[/] Restored {server} from registry")

        except Exception as e:
            console.print(f"[red]Error:[/] Failed to restore from registry: {e}")
            console.print(f"\n[dim]You can manually install with: cpm install {server}[/]")
