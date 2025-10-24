"""
Reset/clear MCP client configurations
"""

import click
from rich.console import Console

from cpm.clients.registry import ClientRegistry

console = Console()


@click.command()
@click.option(
    "--from",
    "from_clients",
    help="Target client(s): cursor, claude, windsurf, all, etc.",
)
@click.option("--dry-run", is_flag=True, help="Simulate operation without making changes")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
def reset(from_clients, dry_run, yes):
    """
    Clear MCP client configurations

    WARNING: This will remove ALL servers from the specified client(s).

    Examples:

        \b
        cpm reset --from cursor               # Clear Cursor config
        cpm reset --from all                  # Clear ALL clients
        cpm reset --from cursor,claude        # Clear multiple clients
    """
    # Detect installed clients
    client_registry = ClientRegistry()
    installed_status = client_registry.detect_installed_clients()

    # Filter to get only installed clients and create manager instances
    detected_clients = {
        name: client_registry.get_client_manager(name)
        for name, is_installed in installed_status.items()
        if is_installed
    }

    if not detected_clients:
        console.print("[red]Error:[/] No MCP clients detected")
        console.print("\n[dim]Supported clients: Claude Desktop, Cursor, Windsurf, VSCode, Cline[/]")
        raise click.Abort()

    # Determine target clients
    if from_clients:
        if from_clients == "all":
            target_list = list(detected_clients.keys())
        else:
            # Parse comma-separated list
            target_list = [c.strip() for c in from_clients.split(",")]

            # Validate clients exist
            invalid = [c for c in target_list if c not in detected_clients]
            if invalid:
                console.print(f"[red]Error:[/] Unknown client(s): {', '.join(invalid)}")
                console.print(f"\n[dim]Detected clients: {', '.join(detected_clients.keys())}[/]")
                raise click.Abort()
    else:
        # No --from specified, require explicit confirmation
        console.print("[red]Error:[/] You must specify which client(s) to reset")
        console.print("\n[dim]Usage:[/] cpm reset --from <client>")
        console.print(f"[dim]Detected clients: {', '.join(detected_clients.keys())}[/]")
        raise click.Abort()

    # Show what will happen
    console.print(f"\n[red]WARNING: This will remove ALL servers from {len(target_list)} client(s)[/]\n")

    console.print("[dim]Target clients:[/]")
    for client_name in target_list:
        client_manager = detected_clients[client_name]

        # Try to get server count
        try:
            servers = client_manager.list_servers()
            server_count = len(servers)
            console.print(f"  * {client_manager.display_name} ({client_name}) - {server_count} server(s)")
        except:
            console.print(f"  * {client_manager.display_name} ({client_name})")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/]")
        return

    # Confirm if not --yes (always require confirmation for reset)
    if not yes:
        console.print()
        console.print("[yellow]This action cannot be undone![/]")
        if not click.confirm("Are you sure you want to continue?", default=False):
            console.print("[yellow]Aborted[/]")
            return

    # Reset clients
    console.print()
    for client_name in target_list:
        client_manager = detected_clients[client_name]

        try:
            # Get list of servers to remove
            servers = client_manager.list_servers()

            if not servers:
                console.print(f"  [dim]{client_name} already empty, skipping[/]")
                continue

            # Remove all servers
            for server_name in servers:
                try:
                    client_manager.remove_server(server_name)
                except Exception as e:
                    console.print(f"  [red]x[/] Failed to remove {server_name} from {client_name}: {e}")

            console.print(f"  [green]+[/] Cleared {client_name} ({len(servers)} server(s) removed)")

        except Exception as e:
            console.print(f"  [red]x[/] Failed to reset {client_name}: {e}")

    console.print(f"\n[green]Done![/] Reset {len(target_list)} client(s)")
    console.print("\n[dim]Restart your MCP clients to apply changes[/]")
