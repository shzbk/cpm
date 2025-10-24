"""
Add servers to MCP clients or groups
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
    "--to",
    "target_destination",
    help="Target: client name (cursor, claude-desktop, etc.), @group-name, or 'all'",
)
@click.option("--dry-run", is_flag=True, help="Simulate operation without making changes")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def add(ctx, targets, target_destination, dry_run, yes):
    """
    Add server(s) to MCP clients or groups

    TARGETS can be server names or @group names.
    --to can be client names (cursor, claude-desktop), @group names, or 'all'.

    Examples:

        \b
        # Add to clients
        cpm add mysql                           # Add to ALL detected clients
        cpm add mysql --to cursor               # Add to Cursor only
        cpm add mysql brave-search              # Add multiple servers
        cpm add @web-dev --to cursor            # Add entire group to Cursor
        cpm add mysql --to cursor,claude-desktop # Add to multiple clients

        \b
        # Add to groups
        cpm add mysql --to @database            # Add mysql to @database group
        cpm add mysql brave-search --to @tools  # Add multiple servers to group
        cpm add @api-tools --to @web-servers    # Add all servers from @api-tools to @web-servers
    """
    # Get config context
    config = ConfigContext(local=ctx.obj.get("local", False))

    # Parse targets (servers and @groups)
    servers_to_add = parse_targets(targets, config)

    if not servers_to_add:
        console.print("[red]Error:[/] No valid servers found")
        raise click.Abort()

    # Check if --to is a group or client(s)
    if target_destination:
        if target_destination.startswith("@"):
            # Group operation
            _add_to_group(servers_to_add, target_destination, config, dry_run, yes)
        else:
            # Client operation
            _add_to_clients(servers_to_add, target_destination, config, dry_run, yes)
    else:
        # Default: add to ALL detected clients
        _add_to_clients(servers_to_add, "all", config, dry_run, yes)


def _add_to_group(servers_to_add, group_spec, config, dry_run, yes):
    """Add servers to a group"""
    group_name = normalize_group_name(group_spec)
    display_group = format_group_display(group_name)

    # Check if group exists, create if it doesn't
    if not config.group_exists(group_name):
        console.print(f"[dim]Creating group {display_group}...[/]")
        config.create_group(group_name)

    # Show what will happen
    console.print(f"\n[cyan]Adding {len(servers_to_add)} server(s) to {display_group}[/]\n")

    for server_name in servers_to_add.keys():
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

    # Add to group
    console.print()
    added_count = 0
    failed_count = 0

    for server_name in servers_to_add.keys():
        try:
            # Check if already in group
            if hasattr(servers_to_add[server_name], "groups") and servers_to_add[server_name].groups and group_name in servers_to_add[server_name].groups:
                console.print(f"  [dim]{server_name} already in {display_group}, skipping[/]")
                continue

            # Add to group
            config.add_server_to_group(server_name, group_name)
            console.print(f"  [green]+[/] Added {server_name} to {display_group}")
            added_count += 1

        except Exception as e:
            console.print(f"  [red]-[/] Failed to add {server_name}: {e}")
            failed_count += 1

    console.print(f"\n[green]Done![/] Added {added_count} server(s) to {display_group}")
    if failed_count > 0:
        console.print(f"[yellow]{failed_count} failed[/]")


def _add_to_clients(servers_to_add, target_spec, config, dry_run, yes):
    """Add servers to clients"""
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
    console.print(f"\n[cyan]Adding {len(servers_to_add)} server(s) to {len(target_list)} client(s)[/]\n")

    for server_name in servers_to_add.keys():
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

    # Add to clients
    console.print()
    for client_name in target_list:
        client_manager = detected_clients[client_name]

        for server_name, server_config in servers_to_add.items():
            try:
                # Check if already exists using get_server
                if server_name in client_manager.list_servers():
                    console.print(f"  [dim]{server_name} already in {client_name}, skipping[/]")
                    continue

                # Add server
                client_manager.add_server(server_config)
                console.print(f"  [green]+[/] Added {server_name} to {client_name}")

            except Exception as e:
                console.print(f"  [red]-[/] Failed to add {server_name} to {client_name}: {e}")

    console.print(f"\n[green]Done![/] Added servers to {len(target_list)} client(s)")
    console.print("\n[dim]Restart your MCP clients to apply changes[/]")
