"""
Manage MCP clients
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.clients.registry import ClientRegistry

console = Console()


@click.group()
def clients():
    """
    Manage MCP clients

    Examples:

        \b
        cpm clients ls                        # List supported clients
        cpm clients detect                    # Detect installed clients
        cpm clients show cursor               # Show client details
    """
    pass


@clients.command("ls")
def clients_ls():
    """
    List all supported MCP clients

    Examples:

        \b
        cpm clients ls                        # List supported clients
    """
    client_registry = ClientRegistry()

    # Get all supported clients (returns a list of client IDs)
    supported = client_registry.get_supported_clients()

    if not supported:
        console.print("[yellow]No supported clients found[/]")
        return

    # Create table
    table = Table(title="Supported MCP Clients")
    table.add_column("Client ID", style="cyan")
    table.add_column("Status", style="yellow")

    # Detect which ones are installed
    detected = client_registry.detect_installed_clients()

    for client_id in supported:
        status = "[green]Installed[/]" if client_id in detected else "[dim]Not Installed[/]"
        table.add_row(client_id, status)

    console.print(table)
    console.print(f"\n[dim]Total: {len(supported)} supported clients, {len(detected)} installed[/]")


@clients.command("detect")
def clients_detect():
    """
    Detect installed MCP clients

    Examples:

        \b
        cpm clients detect                    # Detect installed clients
    """
    client_registry = ClientRegistry()
    detected_clients = client_registry.detect_installed_clients()

    if not detected_clients:
        console.print("[yellow]No MCP clients detected[/]")
        console.print("\n[dim]Supported clients: Claude Desktop, Cursor, Windsurf, VSCode, Cline[/]")
        return

    # Filter to only installed clients (where value is True)
    installed = [name for name, is_installed in detected_clients.items() if is_installed]

    if not installed:
        console.print("[yellow]No MCP clients detected[/]")
        console.print("\n[dim]Supported clients: Claude Desktop, Cursor, Windsurf, VSCode, Cline[/]")
        return

    console.print(f"[green]Detected {len(installed)} installed client(s):[/]\n")

    for client_name in installed:
        # Get client manager for this client
        client_manager = client_registry.get_client_manager(client_name)
        if not client_manager:
            continue

        console.print(f"  [cyan]*[/] {client_manager.display_name} ({client_name})")
        console.print(f"    [dim]Config: {client_manager.config_path}[/]")

        # Try to get server count
        try:
            servers = client_manager.list_servers()
            server_count = len(servers)
            console.print(f"    [dim]Servers: {server_count}[/]")
        except:
            pass

        console.print()


@clients.command("show")
@click.argument("client")
def clients_show(client):
    """
    Show details for a specific client

    Examples:

        \b
        cpm clients show cursor               # Show Cursor details
        cpm clients show claude               # Show Claude Desktop details
    """
    client_registry = ClientRegistry()
    detected_clients = client_registry.detect_installed_clients()

    # Filter to only installed clients
    installed = {name: True for name, is_installed in detected_clients.items() if is_installed}

    if client not in installed:
        console.print(f"[red]Error:[/] Client not found: {client}")
        console.print(f"\n[dim]Detected clients: {', '.join(installed.keys())}[/]")
        raise click.Abort()

    client_manager = client_registry.get_client_manager(client)

    # Show client info
    console.print(f"\n[cyan]{client_manager.display_name}[/]\n")
    console.print(f"[dim]ID:[/] {client}")
    console.print(f"[dim]Config Path:[/] {client_manager.config_path}")

    # Try to show config format
    try:
        if hasattr(client_manager, "format"):
            console.print(f"[dim]Format:[/] {client_manager.format}")
    except:
        pass

    # List servers
    try:
        servers = client_manager.list_servers()

        if servers:
            # Handle both list and dict returns
            if isinstance(servers, list):
                server_count = len(servers)
                console.print(f"\n[green]Installed Servers ({server_count}):[/]\n")
                for server_name in servers:
                    console.print(f"  [cyan]*[/] {server_name}")
            else:
                console.print(f"\n[green]Installed Servers ({len(servers)}):[/]\n")

                # Create table
                table = Table(show_header=True)
                table.add_column("Server", style="cyan")
                table.add_column("Command", style="dim")

                for server_name, server_config in servers.items():
                    # Get command if available
                    command = ""
                    if hasattr(server_config, "command"):
                        command = server_config.command
                    elif hasattr(server_config, "url"):
                        command = server_config.url

                    table.add_row(server_name, command[:50] + "..." if len(command) > 50 else command)

                console.print(table)
        else:
            console.print("\n[yellow]No servers installed[/]")

    except Exception as e:
        console.print(f"\n[red]Error reading servers:[/] {e}")

    console.print()
