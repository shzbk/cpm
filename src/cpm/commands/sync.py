"""
Synchronize servers to MCP clients
"""

import click
from rich.console import Console

from cpm.clients.registry import ClientRegistry
from cpm.core.context import ConfigContext

console = Console()


def parse_targets(targets: tuple, config: ConfigContext):
    """
    Parse mix of servers and @groups into server list

    Args:
        targets: Tuple of server names or @group names (empty = all servers)
        config: ConfigContext instance

    Returns:
        Dict of server_name → ServerConfig
    """
    # If no targets specified, sync all servers
    if not targets:
        return config.list_servers()

    servers = {}

    for target in targets:
        if target.startswith("@"):
            # Group reference
            group_name = target[1:]
            try:
                group_servers = config.get_servers_in_group(group_name)
                servers.update(group_servers)
            except KeyError:
                console.print(f"[yellow]Warning: Group not found: {group_name}[/]")
        else:
            # Server reference
            try:
                server = config.get_server(target)
                servers[target] = server
            except KeyError:
                console.print(f"[yellow]Warning: Server not found: {target}[/]")

    return servers


@click.command()
@click.argument("targets", nargs=-1)
@click.option(
    "--to",
    "target_clients",
    help="Target client(s): cursor, claude, windsurf, all, etc.",
)
@click.option("--dry-run", is_flag=True, help="Simulate operation without making changes")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def sync(ctx, targets, target_clients, dry_run, yes):
    """
    Synchronize servers to MCP clients

    TARGETS can be server names, @group names, or omitted to sync all servers.

    Examples:

        \b
        cpm sync                              # Sync ALL servers to ALL clients
        cpm sync --to cursor                  # Sync all to Cursor only
        cpm sync mysql                        # Sync specific server to all
        cpm sync mysql --to cursor            # Sync specific server to Cursor
        cpm sync @database --to cursor        # Sync group to Cursor
        cpm sync mysql brave-search           # Sync multiple servers
    """
    # Get config context
    config = ConfigContext(local=ctx.obj.get("local", False))

    # Parse targets (servers, @groups, or all)
    servers_to_sync = parse_targets(targets, config)

    if not servers_to_sync:
        console.print("[red]Error:[/] No valid servers found")
        raise click.Abort()

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
    if target_clients:
        if target_clients == "all":
            target_list = list(detected_clients.keys())
        else:
            # Parse comma-separated list
            target_list = [c.strip() for c in target_clients.split(",")]

            # Validate clients exist
            invalid = [c for c in target_list if c not in detected_clients]
            if invalid:
                console.print(f"[red]Error:[/] Unknown client(s): {', '.join(invalid)}")
                console.print(f"\n[dim]Detected clients: {', '.join(detected_clients.keys())}[/]")
                raise click.Abort()
    else:
        # Default: sync to ALL detected clients
        target_list = list(detected_clients.keys())

    # Show what will happen
    console.print(f"\n[cyan]Synchronizing {len(servers_to_sync)} server(s) to {len(target_list)} client(s)[/]\n")

    for server_name in servers_to_sync.keys():
        console.print(f"  * {server_name}")

    console.print(f"\n[dim]Target clients:[/]")
    for client_name in target_list:
        client_manager = detected_clients[client_name]
        console.print(f"  * {client_manager.display_name} ({client_name})")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/]")
        return

    # Confirm if not --yes
    if not yes:
        console.print()
        if not click.confirm("Continue?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    # Sync to clients
    console.print()
    added_count = 0
    updated_count = 0
    skipped_count = 0

    for client_name in target_list:
        client_manager = detected_clients[client_name]

        for server_name, server_config in servers_to_sync.items():
            try:
                # Check if server already exists using list_servers
                if server_name in client_manager.list_servers():
                    # Update by removing and re-adding (not all clients support update_server)
                    client_manager.remove_server(server_name)
                    client_manager.add_server(server_config)
                    console.print(f"  [blue]~[/] Updated {server_name} in {client_name}")
                    updated_count += 1
                else:
                    # Add new server
                    client_manager.add_server(server_config)
                    console.print(f"  [green]+[/] Added {server_name} to {client_name}")
                    added_count += 1

            except Exception as e:
                console.print(f"  [red]-[/] Failed to sync {server_name} to {client_name}: {e}")

    console.print(f"\n[green]Done![/] Synced servers to {len(target_list)} client(s)")
    console.print(f"  [green]Added:[/] {added_count}  [blue]Updated:[/] {updated_count}")
    console.print("\n[dim]Restart your MCP clients to apply changes[/]")
