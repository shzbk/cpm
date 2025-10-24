"""
List command - Show installed servers
"""

import json as json_lib
import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext
from cpm.clients.registry import ClientRegistry
from cpm.utils.config_validator import ConfigValidator

console = Console()


def format_group_display(group_name: str) -> str:
    """Format group name with @ prefix"""
    if not group_name.startswith("@"):
        return f"@{group_name}"
    return group_name


@click.command(name="ls")
@click.option("--local", is_flag=True, help="List from local project (cpm.json)")
@click.option("--all", "show_all", is_flag=True, help="Show both global and local")
@click.option("--long", is_flag=True, help="Detailed view with commands")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--tree", is_flag=True, help="Show group hierarchy")
@click.option("--clients", is_flag=True, help="Show client assignments")
@click.option("--groups", is_flag=True, help="Group by groups")
@click.option("--group", help="Filter by specific group")
@click.pass_context
def list_servers(ctx, local: bool, show_all: bool, long: bool, json_output: bool, tree: bool, clients: bool, groups: bool, group: str):
    """
    List installed servers

    Shows servers from global or local context. Can display detailed information,
    group hierarchies, and client assignments.

    Examples:

        \b
        cpm ls                                    # List global servers
        cpm ls --local                            # List local servers
        cpm ls --all                              # Both global + local
        cpm ls --long                             # Detailed view
        cpm ls --json                             # JSON output
        cpm ls --tree                             # Show group hierarchy
        cpm ls --clients                          # Show client assignments
        cpm ls --group @database                  # Filter by group
        cpm ls --groups                           # Group by groups
    """
    # Get config context(s)
    if show_all:
        # Show both global and local
        global_config = ConfigContext(local=False)
        local_config = ConfigContext(local=True) if ConfigContext(local=True).manager.config_file.exists() else None

        _list_combined(global_config, local_config, long, json_output)
        return

    # Single context
    config = ConfigContext(local=local or ctx.obj.get("local", False))

    # Handle --group filter
    if group:
        # Accept both with and without @ for convenience, but show normalized
        group_name = group[1:] if group.startswith("@") else group
        try:
            _list_group_servers(group_name, config, long, json_output)
        except KeyError:
            display_name = format_group_display(group_name)
            console.print(f"[red]Error:[/] Group '{display_name}' not found")
            console.print(f"\n[dim]List groups:[/] cpm group ls")
            raise click.Abort()
        return

    # Handle --clients
    if clients:
        _list_with_clients(config)
        return

    # Get servers
    servers = config.list_servers()

    if not servers:
        if not json_output:
            console.print("[yellow]No servers installed[/]")
            console.print("\n[dim]Install one:[/] cpm install <server-name>")
        else:
            print(json_lib.dumps({"servers": []}, indent=2))
        return

    # Display based on flags
    if json_output:
        _list_json(servers, config)
    elif tree:
        _list_tree(config)
    elif groups:
        _list_by_groups(config, long)
    else:
        _list_simple(servers, config, long)


def _list_simple(servers, config, long: bool):
    """Display servers in a simple table"""
    table = Table(title=f"Installed Servers ({config.context})")

    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")

    if long:
        table.add_column("Command/URL", style="green", max_width=50)

    if config.is_local:
        table.add_column("Version", style="yellow")

    table.add_column("Config", style="dim")
    table.add_column("Groups", style="blue")

    for name, server in servers.items():
        server_type = "stdio" if hasattr(server, "command") else "remote"
        groups_list = getattr(server, "groups", []) if hasattr(server, "groups") and server.groups else []
        groups_str = ", ".join(format_group_display(g) for g in groups_list) if groups_list else "-"

        # Get config status
        missing = ConfigValidator.get_missing_vars(server)
        if not missing:
            config_status = "[green]READY[/]"
        elif len(missing) == 1:
            config_status = "[yellow]INCOMPLETE[/] (1 missing)"
        else:
            config_status = "[yellow]INCOMPLETE[/] ({} missing)".format(len(missing))

        row = [name, server_type]

        if long:
            if hasattr(server, "command"):
                cmd_str = f"{server.command} {' '.join(server.args[:2])}"
                if len(server.args) > 2:
                    cmd_str += "..."
                row.append(cmd_str)
            elif hasattr(server, "url"):
                row.append(server.url)
            else:
                row.append("-")

        if config.is_local:
            version = config.get_version(name) or "unknown"
            row.append(version)

        row.append(config_status)
        row.append(groups_str)

        table.add_row(*row)

    console.print(table)
    console.print(f"\n[dim]Total: {len(servers)} servers[/]")
    console.print("[dim]Hint: cpm config <server> to configure[/]")


def _list_json(servers, config):
    """Output servers as JSON"""
    output = {
        "context": config.context,
        "servers": {}
    }

    for name, server in servers.items():
        server_data = server.model_dump()

        if config.is_local:
            server_data["version"] = config.get_version(name)

        output["servers"][name] = server_data

    print(json_lib.dumps(output, indent=2))


def _list_group_servers(group_name: str, config: ConfigContext, long: bool, json_output: bool):
    """Display servers in a specific group"""
    servers = config.get_servers_in_group(group_name)

    if json_output:
        output = {
            "group": group_name,
            "servers": {name: server.model_dump() for name, server in servers.items()}
        }
        print(json_lib.dumps(output, indent=2))
        return

    console.print(f"\n[bold cyan]Group: {group_name}[/]")

    if not servers:
        console.print("\n[yellow]No servers in this group[/]")
        console.print(f"\n[dim]Add servers:[/] cpm group add {group_name} <server-name>")
        return

    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")

    if long:
        table.add_column("Command/URL", style="green", max_width=50)

    for server_name, server in servers.items():
        server_type = "stdio" if hasattr(server, "command") else "remote"

        row = [server_name, server_type]

        if long:
            if hasattr(server, "command"):
                cmd_str = f"{server.command} {' '.join(server.args[:2])}"
                if len(server.args) > 2:
                    cmd_str += "..."
                row.append(cmd_str)
            elif hasattr(server, "url"):
                row.append(server.url)
            else:
                row.append("-")

        table.add_row(*row)

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total: {len(servers)} servers in {group_name}[/]")


def _list_by_groups(config: ConfigContext, long: bool):
    """Display servers grouped by groups"""
    all_groups = config.list_groups()

    if not all_groups:
        console.print("[yellow]No groups created[/]")
        console.print("\n[dim]Create one:[/] cpm group create <name>")
        return

    for group_name, group_data in all_groups.items():
        servers = config.get_servers_in_group(group_name)

        console.print(f"\n[bold cyan]{format_group_display(group_name)}[/]")

        # Handle description based on structure
        if isinstance(group_data, dict) and "description" in group_data:
            console.print(f"[dim]{group_data['description']}[/]")

        if servers:
            for server_name, server in servers.items():
                server_type = "stdio" if hasattr(server, "command") else "remote"

                if long:
                    console.print(f"  * {server_name} [{server_type}]")
                else:
                    console.print(f"  * {server_name}")
        else:
            console.print("  [dim](empty)[/]")


def _list_tree(config: ConfigContext):
    """Display servers in tree format with groups"""
    all_groups = config.list_groups()
    all_servers = config.list_servers()

    # Servers in groups
    servers_in_groups = set()
    for group_name in all_groups.keys():
        try:
            group_servers = config.get_servers_in_group(group_name)
            servers_in_groups.update(group_servers.keys())
        except:
            pass

    # Ungrouped servers
    ungrouped = {name: server for name, server in all_servers.items() if name not in servers_in_groups}

    console.print(f"\n[cyan]Server Tree ({config.context})[/]\n")

    # Show groups
    if all_groups:
        for group_name in all_groups.keys():
            try:
                servers = config.get_servers_in_group(group_name)
                console.print(f"[bold]@{group_name}[/]")

                if servers:
                    for server_name in servers.keys():
                        console.print(f"  * {server_name}")
                else:
                    console.print("  [dim](empty)[/]")

                console.print()
            except:
                pass

    # Show ungrouped
    if ungrouped:
        console.print("[dim](ungrouped)[/]")
        for server_name in ungrouped.keys():
            console.print(f"  * {server_name}")
        console.print()

    console.print(f"[dim]Total: {len(all_servers)} servers, {len(all_groups)} groups[/]")


def _list_with_clients(config: ConfigContext):
    """Display servers with client assignments"""
    servers = config.list_servers()

    if not servers:
        console.print("[yellow]No servers installed[/]")
        return

    # Detect clients
    client_registry = ClientRegistry()
    installed_status = client_registry.detect_installed_clients()

    # Filter to get only installed clients and create manager instances
    detected_clients = {
        name: client_registry.get_client_manager(name)
        for name, is_installed in installed_status.items()
        if is_installed
    }

    if not detected_clients:
        console.print("[yellow]No MCP clients detected[/]")
        console.print("\n[dim]Detected clients: None[/]")
        return

    console.print(f"\n[cyan]Servers and Client Assignments[/]\n")

    for server_name in servers.keys():
        console.print(f"[bold]{server_name}[/]")

        # Check which clients have this server
        assigned_clients = []
        for client_name, client_manager in detected_clients.items():
            try:
                # Use list_servers() instead of non-existent has_server()
                if server_name in client_manager.list_servers():
                    assigned_clients.append(client_name)
            except:
                pass

        if assigned_clients:
            for client_name in assigned_clients:
                console.print(f"  [green]+[/] {client_name}")
        else:
            console.print("  [dim]Not assigned to any clients[/]")

        console.print()


def _list_combined(global_config: ConfigContext, local_config: ConfigContext, long: bool, json_output: bool):
    """Display both global and local servers"""
    global_servers = global_config.list_servers()
    local_servers = local_config.list_servers() if local_config else {}

    if json_output:
        output = {
            "global": {name: server.model_dump() for name, server in global_servers.items()},
            "local": {name: server.model_dump() for name, server in local_servers.items()},
        }
        print(json_lib.dumps(output, indent=2))
        return

    # Global servers
    if global_servers:
        console.print("\n[cyan]Global Servers[/]")
        _list_simple(global_servers, global_config, long)
    else:
        console.print("\n[cyan]Global Servers[/]")
        console.print("[dim]No global servers installed[/]")

    # Local servers
    console.print()
    if local_config and local_servers:
        console.print("[cyan]Local Servers[/]")
        _list_simple(local_servers, local_config, long)
    else:
        console.print("[cyan]Local Servers[/]")
        console.print("[dim]No local project or no servers installed[/]")
