"""
Group commands - Manage server groups

Matches specification from COMMANDS.md:
- Subcommands: create, delete, rename, add, remove, ls, show
- Supports --local for project-specific groups
- Uses ConfigContext for unified global/local handling
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext

console = Console()


def normalize_group_name(name: str) -> str:
    """
    Normalize group name by stripping @ prefix if present.

    @ prefix is for semantic clarity (e.g., @database)
    But internally we store without @

    Args:
        name: Group name (with or without @)

    Returns:
        Group name without @ prefix
    """
    if name.startswith("@"):
        return name[1:]
    return name


def format_group_display(name: str) -> str:
    """
    Format group name for display with @ prefix.

    Args:
        name: Group name (without @)

    Returns:
        Group name with @ prefix for display
    """
    if not name.startswith("@"):
        return f"@{name}"
    return name


@click.group()
@click.option("--local", is_flag=True, help="Manage local project groups")
@click.pass_context
def group(ctx, local):
    """
    Manage server groups

    Organize servers into reusable groups for different workflows.
    Groups can be global (shared across all projects) or local (project-specific).

    Examples:

        \b
        # Global groups
        cpm group create database
        cpm group add database mysql postgres

        \b
        # Local groups
        cpm group create api-tools --local
        cpm group add api-tools rest-api --local
    """
    # Store local flag in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["local"] = local


@group.command("create")
@click.argument("name")
@click.option("--description", "-d", help="Group description")
@click.pass_context
def create_group(ctx, name: str, description: str):
    """
    Create a new server group

    Examples:

        \b
        cpm group create @web-dev
        cpm group create @web-dev -d "Web development tools"
        cpm group create @database --local
    """
    # Require @ prefix
    if not name.startswith("@"):
        console.print(f"[red]Error:[/] Group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize name (strip @ if present)
    group_name = normalize_group_name(name)
    display_name = format_group_display(group_name)

    if config.group_exists(group_name):
        console.print(f"[yellow]Group {display_name} already exists[/]")
        return

    try:
        config.create_group(group_name, description=description)
        console.print(f"[green]+[/] Created group [cyan]{display_name}[/]")
        console.print(f"\n[dim]Add servers:[/] cpm group add {display_name} <server-name>")
    except Exception as e:
        console.print(f"[red]Error:[/] Failed to create group: {e}")
        raise click.Abort()


@group.command("delete")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_group(ctx, name: str, yes: bool):
    """
    Delete a server group

    This removes the group but keeps all servers installed.

    Examples:

        \b
        cpm group delete @web-dev
        cpm group delete @database-tools --local
        cpm group delete @old-group -y
    """
    # Require @ prefix
    if not name.startswith("@"):
        console.print(f"[red]Error:[/] Group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize name
    group_name = normalize_group_name(name)
    display_name = format_group_display(group_name)

    if not config.group_exists(group_name):
        console.print(f"[yellow]Group {display_name} not found[/]")
        console.print(f"\n[dim]List groups:[/] cpm group ls")
        return

    # Confirm deletion
    if not yes:
        servers = config.get_servers_in_group(group_name)
        console.print(f"\n[yellow]Delete group {display_name}?[/]")
        if servers:
            console.print(f"[dim]This group contains {len(servers)} server(s)[/]")
        console.print("[dim]Servers will remain installed[/]")

        if not click.confirm("Continue?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    try:
        config.delete_group(group_name)
        console.print(f"[green]+[/] Deleted group [cyan]{display_name}[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] Failed to delete group: {e}")
        raise click.Abort()


@group.command("rename")
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def rename_group(ctx, old_name: str, new_name: str):
    """
    Rename a server group

    Examples:

        \b
        cpm group rename @web-dev @frontend
        cpm group rename @old-name @new-name --local
    """
    # Require @ prefix for both names
    if not old_name.startswith("@"):
        console.print(f"[red]Error:[/] Old group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {old_name}[/]")
        raise click.Abort()

    if not new_name.startswith("@"):
        console.print(f"[red]Error:[/] New group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {new_name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize names
    old_group_name = normalize_group_name(old_name)
    new_group_name = normalize_group_name(new_name)
    old_display = format_group_display(old_group_name)
    new_display = format_group_display(new_group_name)

    # Check if old group exists
    if not config.group_exists(old_group_name):
        console.print(f"[red]Error:[/] Group {old_display} not found")
        console.print(f"\n[dim]List groups:[/] cpm group ls")
        raise click.Abort()

    # Check if new name already exists
    if config.group_exists(new_group_name):
        console.print(f"[red]Error:[/] Group {new_display} already exists")
        raise click.Abort()

    try:
        config.rename_group(old_group_name, new_group_name)
        console.print(f"[green]+[/] Renamed group [cyan]{old_display}[/] -> [cyan]{new_display}[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] Failed to rename group: {e}")
        raise click.Abort()


@group.command("add")
@click.argument("group_name")
@click.argument("server_names", nargs=-1, required=True)
@click.pass_context
def add_servers(ctx, group_name: str, server_names: tuple):
    """
    Add server(s) to a group

    Examples:

        \b
        cpm group add @web-dev brave-search
        cpm group add @database mysql postgres sqlite
        cpm group add @api-tools rest-api --local
    """
    # Require @ prefix
    if not group_name.startswith("@"):
        console.print(f"[red]Error:[/] Group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {group_name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize group name
    normalized_group = normalize_group_name(group_name)
    display_group = format_group_display(normalized_group)

    # Auto-create group if it doesn't exist
    if not config.group_exists(normalized_group):
        console.print(f"[dim]Creating group {display_group}...[/]")
        config.create_group(normalized_group)

    added_count = 0
    failed_count = 0

    for server_name in server_names:
        # Check if server exists
        try:
            server = config.get_server(server_name)
        except KeyError:
            console.print(f"[yellow]Warning: Server '{server_name}' is not installed[/]")
            console.print(f"[dim]Install it:[/] cpm install {server_name}")
            failed_count += 1
            continue

        # Check if server is already in group
        if hasattr(server, "groups") and server.groups and normalized_group in server.groups:
            console.print(f"[yellow]'{server_name}' is already in group {display_group}[/]")
            continue

        try:
            config.add_server_to_group(server_name, normalized_group)
            console.print(f"[green]+[/] Added [cyan]{server_name}[/] to [cyan]{display_group}[/]")
            added_count += 1
        except Exception as e:
            console.print(f"[red]-[/] Failed to add {server_name}: {e}")
            failed_count += 1

    # Summary
    if len(server_names) > 1:
        console.print(f"\n[green]Added {added_count}/{len(server_names)} server(s)[/]")
        if failed_count > 0:
            console.print(f"[yellow]{failed_count} failed[/]")


@group.command("remove")
@click.argument("group_name")
@click.argument("server_names", nargs=-1, required=True)
@click.pass_context
def remove_servers(ctx, group_name: str, server_names: tuple):
    """
    Remove server(s) from a group

    The servers remain installed, just removed from the group.

    Examples:

        \b
        cpm group remove @web-dev brave-search
        cpm group remove @database mysql postgres
        cpm group remove @api-tools rest-api --local
    """
    # Require @ prefix
    if not group_name.startswith("@"):
        console.print(f"[red]Error:[/] Group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {group_name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize group name
    normalized_group = normalize_group_name(group_name)
    display_group = format_group_display(normalized_group)

    # Check if group exists
    if not config.group_exists(normalized_group):
        console.print(f"[red]Error:[/] Group {display_group} not found")
        console.print(f"\n[dim]List groups:[/] cpm group ls")
        raise click.Abort()

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

        # Check if server is in group
        if not hasattr(server, "groups") or not server.groups or normalized_group not in server.groups:
            console.print(f"[yellow]'{server_name}' is not in group {display_group}[/]")
            continue

        try:
            config.remove_server_from_group(server_name, normalized_group)
            console.print(f"[green]+[/] Removed [cyan]{server_name}[/] from [cyan]{display_group}[/]")
            removed_count += 1
        except Exception as e:
            console.print(f"[red]-[/] Failed to remove {server_name}: {e}")
            failed_count += 1

    # Summary
    if len(server_names) > 1:
        console.print(f"\n[green]Removed {removed_count}/{len(server_names)} server(s)[/]")
        if failed_count > 0:
            console.print(f"[yellow]{failed_count} failed[/]")


@group.command("ls")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def list_groups(ctx, json_output: bool):
    """
    List all server groups

    Examples:

        \b
        cpm group ls
        cpm group ls --local
        cpm group ls --json
    """
    config = ConfigContext(local=ctx.obj.get("local", False))
    groups = config.list_groups()

    if not groups:
        if not json_output:
            console.print("[yellow]No groups created[/]")
            console.print("\n[dim]Create one:[/] cpm group create <name>")
        else:
            import json
            print(json.dumps({"groups": []}, indent=2))
        return

    if json_output:
        import json
        output = {"groups": {}}
        for name, metadata in groups.items():
            servers = config.get_servers_in_group(name)
            output["groups"][name] = {
                "description": metadata.get("description") if isinstance(metadata, dict) else getattr(metadata, "description", None),
                "servers": list(servers.keys())
            }
        print(json.dumps(output, indent=2))
        return

    table = Table(title=f"Server Groups ({config.context})")
    table.add_column("Name", style="cyan")
    table.add_column("Servers", style="dim")
    table.add_column("Description", style="dim")

    for name, metadata in groups.items():
        servers = config.get_servers_in_group(name)
        server_count = f"{len(servers)} server{'s' if len(servers) != 1 else ''}"

        # Handle description based on structure
        if isinstance(metadata, dict):
            description = metadata.get("description", "-")
        else:
            description = getattr(metadata, "description", "-") or "-"

        table.add_row(name, server_count, description)

    console.print(table)
    console.print(f"\n[dim]Total: {len(groups)} group{'s' if len(groups) != 1 else ''}[/]")


@group.command("show")
@click.argument("name")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def show_group(ctx, name: str, json_output: bool):
    """
    Show detailed information about a group

    Examples:

        \b
        cpm group show @web-dev
        cpm group show @database --local
        cpm group show @api-tools --json
    """
    # Require @ prefix
    if not name.startswith("@"):
        console.print(f"[red]Error:[/] Group name must start with @ (e.g., @web-dev)")
        console.print(f"[dim]Got: {name}[/]")
        raise click.Abort()

    config = ConfigContext(local=ctx.obj.get("local", False))

    # Normalize name
    normalized_name = normalize_group_name(name)
    display_name = format_group_display(normalized_name)

    if not config.group_exists(normalized_name):
        console.print(f"[red]Error:[/] Group '{display_name}' not found")
        console.print(f"\n[dim]List groups:[/] cpm group ls")
        raise click.Abort()

    try:
        metadata = config.get_group(normalized_name)
        servers = config.get_servers_in_group(normalized_name)
    except Exception as e:
        console.print(f"[red]Error:[/] Failed to get group info: {e}")
        raise click.Abort()

    if json_output:
        import json

        # Handle description based on structure
        if isinstance(metadata, dict):
            description = metadata.get("description")
        else:
            description = getattr(metadata, "description", None)

        output = {
            "name": normalized_name,
            "description": description,
            "servers": {}
        }

        for server_name, server in servers.items():
            server_type = "stdio" if hasattr(server, "command") else "remote"
            output["servers"][server_name] = {
                "type": server_type,
                "config": server.model_dump()
            }

        print(json.dumps(output, indent=2))
        return

    console.print(f"\n[bold cyan]{display_name}[/]")

    # Handle description based on structure
    if isinstance(metadata, dict):
        description = metadata.get("description")
    else:
        description = getattr(metadata, "description", None)

    if description:
        console.print(f"[dim]{description}[/]")

    console.print(f"\n[bold]Servers ({len(servers)}):[/]")
    if servers:
        for server_name, server in servers.items():
            server_type = "stdio" if hasattr(server, "command") else "remote"
            console.print(f"  * [cyan]{server_name}[/] [dim]({server_type})[/]")
    else:
        console.print("  [dim](no servers)[/]")

    console.print(f"\n[dim]Add servers:[/] cpm group add {display_name} <server-name>")
