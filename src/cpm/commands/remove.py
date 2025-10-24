"""
Remove servers from MCP clients or groups
"""

import click
from rich.console import Console

from cpm.clients.registry import ClientRegistry
from cpm.core.context import ConfigContext

console = Console()


def normalize_group_name(name: str) -> str:
    """Normalize group name by stripping @ prefix if present"""
    if name.startswith("@"):
        return name[1:]
    return name


def format_group_display(name: str) -> str:
    """Format group name for display with @ prefix"""
    if not name.startswith("@"):
        return f"@{name}"
    return name


def parse_targets(targets: tuple, config: ConfigContext):
    """
    Parse mix of servers and @groups into server list

    Args:
        targets: Tuple of server names or @group names
        config: ConfigContext instance

    Returns:
        Dict of server_name → ServerConfig
    """
    servers = {}

    for target in targets:
        if target.startswith("@"):
            # Group reference
            group_name = normalize_group_name(target)
            try:
                group_servers = config.get_servers_in_group(group_name)
                servers.update(group_servers)
            except KeyError:
                console.print(f"[yellow]Warning: Group not found: {target}[/]")
        else:
            # Server reference
            try:
                server = config.get_server(target)
                servers[target] = server
            except KeyError:
                console.print(f"[yellow]Warning: Server not found: {target}[/]")

    return servers


@click.command()
@click.argument("targets", nargs=-1, required=True)
@click.option(
    "--from",
    "target_destination",
    help="Target: client name (cursor, claude-desktop, etc.), @group-name, or 'all'",
)
@click.option("--dry-run", is_flag=True, help="Simulate operation without making changes")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def remove(ctx, targets, target_destination, dry_run, yes):
    """
    Remove server(s) from MCP clients or groups

    TARGETS can be server names or @group names.
    --from can be client names (cursor, claude-desktop), @group names, or 'all'.

    Examples:

        \b
        # Remove from clients
        cpm remove mysql                           # Remove from ALL detected clients
        cpm remove mysql --from cursor             # Remove from Cursor only
        cpm remove mysql brave-search              # Remove multiple servers
        cpm remove @web-dev --from cursor          # Remove entire group from Cursor
        cpm remove mysql --from cursor,claude-desktop # Remove from multiple clients

        \b
        # Remove from groups
        cpm remove mysql --from @database          # Remove mysql from @database group
        cpm remove mysql brave-search --from @tools # Remove multiple servers from group
        cpm remove @api-tools --from @web-servers  # Remove all servers from @api-tools from @web-servers
    """
    # Get config context
    config = ConfigContext(local=ctx.obj.get("local", False))

    # Parse targets (servers and @groups)
    servers_to_remove = parse_targets(targets, config)

    if not servers_to_remove:
        console.print("[red]Error:[/] No valid servers found")
        raise click.Abort()

    # Check if --from is a group or client(s)
    if target_destination:
        if target_destination.startswith("@"):
            # Group operation
            _remove_from_group(servers_to_remove, target_destination, config, dry_run, yes)
        else:
            # Client operation
            _remove_from_clients(servers_to_remove, target_destination, config, dry_run, yes)
    else:
        # Default: remove from ALL detected clients
        _remove_from_clients(servers_to_remove, "all", config, dry_run, yes)


def _remove_from_group(servers_to_remove, group_spec, config, dry_run, yes):
    """Remove servers from a group"""
    group_name = normalize_group_name(group_spec)
    display_group = format_group_display(group_name)

    # Check if group exists
    if not config.group_exists(group_name):
        console.print(f"[red]Error:[/] Group {display_group} not found")
        console.print(f"\n[dim]List groups:[/] cpm group ls")
        raise click.Abort()

    # Show what will happen
    console.print(f"\n[cyan]Removing {len(servers_to_remove)} server(s) from {display_group}[/]\n")

    for server_name in servers_to_remove.keys():
        console.print(f"  * {server_name}")

    console.print(f"\n[dim]Target group:[/] {display_group}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/]")
        return

    # Confirm if not --yes
    if not yes:
        console.print()
        if not click.confirm("Continue?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    # Remove from group
    console.print()
    removed_count = 0
    failed_count = 0

    for server_name in servers_to_remove.keys():
        try:
            # Try to remove from group
            config.remove_server_from_group(server_name, group_name)
            console.print(f"  [green]+[/] Removed {server_name} from {display_group}")
            removed_count += 1

        except Exception as e:
            console.print(f"  [red]-[/] Failed to remove {server_name}: {e}")
            failed_count += 1

    console.print(f"\n[green]Done![/] Removed {removed_count} server(s) from {display_group}")
    if failed_count > 0:
        console.print(f"[yellow]{failed_count} failed[/]")


def _remove_from_clients(servers_to_remove, target_spec, config, dry_run, yes):
    """Remove servers from clients"""
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
    if target_spec == "all":
        target_list = list(detected_clients.keys())
    else:
        # Parse comma-separated list
        target_list = [c.strip() for c in target_spec.split(",")]

        # Validate clients exist
        invalid = [c for c in target_list if c not in detected_clients]
        if invalid:
            console.print(f"[red]Error:[/] Unknown client(s): {', '.join(invalid)}")
            console.print(f"\n[dim]Detected clients: {', '.join(detected_clients.keys())}[/]")
            raise click.Abort()

    # Show what will happen
    console.print(f"\n[cyan]Removing {len(servers_to_remove)} server(s) from {len(target_list)} client(s)[/]\n")

    for server_name in servers_to_remove.keys():
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

    # Remove from clients
    console.print()
    removed_count = 0
    for client_name in target_list:
        client_manager = detected_clients[client_name]

        for server_name in servers_to_remove.keys():
            try:
                # Check if server exists in client using list_servers
                if server_name not in client_manager.list_servers():
                    console.print(f"  [dim]{server_name} not in {client_name}, skipping[/]")
                    continue

                # Remove server
                client_manager.remove_server(server_name)
                console.print(f"  [green]+[/] Removed {server_name} from {client_name}")
                removed_count += 1

            except Exception as e:
                console.print(f"  [red]-[/] Failed to remove {server_name} from {client_name}: {e}")

    if removed_count > 0:
        console.print(f"\n[green]Done![/] Removed servers from {len(target_list)} client(s)")
        console.print("\n[dim]Restart your MCP clients to apply changes[/]")
    else:
        console.print("\n[yellow]No servers were removed[/]")
