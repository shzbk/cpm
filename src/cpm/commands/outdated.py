"""
Check for outdated servers
"""

import json
import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext
from cpm.core.registry import RegistryClient

console = Console()


@click.command()
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def outdated(ctx, json_output):
    """
    Check for outdated servers

    Shows which servers have newer versions available in the registry.

    Examples:

        \b
        cpm outdated                          # Check for outdated servers
        cpm outdated --json                   # JSON output
    """
    # Get config context
    config = ConfigContext(local=ctx.obj.get("local", False))

    # Get all servers
    servers = config.list_servers()

    if not servers:
        if not json_output:
            console.print("[yellow]No servers installed[/]")
        else:
            print(json.dumps({"outdated": []}, indent=2))
        return

    # Check for updates
    if not json_output:
        console.print(f"[cyan]Checking {len(servers)} server(s) for updates...[/]\n")

    registry = RegistryClient()
    outdated_servers = []

    for server_name, server_config in servers.items():
        # Get current version
        current_version = config.get_version(server_name) if config.is_local else None

        if not current_version:
            # No version info, skip
            continue

        try:
            # Fetch latest version from registry
            server_metadata = registry.get_server(server_name)
            latest_version = server_metadata.get("version", "unknown")

            # Compare versions
            if current_version != latest_version:
                outdated_servers.append({
                    "name": server_name,
                    "current": current_version,
                    "latest": latest_version,
                    "type": server_metadata.get("type", "unknown"),
                })

        except Exception as e:
            if not json_output:
                console.print(f"[red]-[/] {server_name}: failed to check: {e}")

    # Output results
    if json_output:
        # JSON output
        output = {
            "outdated": outdated_servers,
            "total": len(servers),
            "outdated_count": len(outdated_servers),
        }
        print(json.dumps(output, indent=2))

    else:
        # Human-readable output
        if not outdated_servers:
            console.print("[green]All servers are up to date![/]")
            return

        console.print(f"[yellow]Found {len(outdated_servers)} outdated server(s):[/]\n")

        # Create table
        table = Table()
        table.add_column("Server", style="cyan")
        table.add_column("Current", style="yellow")
        table.add_column("Latest", style="green")
        table.add_column("Type", style="dim")

        for server in outdated_servers:
            table.add_row(
                server["name"],
                server["current"],
                server["latest"],
                server["type"],
            )

        console.print(table)

        console.print(f"\n[dim]Run 'cpm update' to update all servers[/]")
        console.print(f"[dim]Run 'cpm update <server>' to update specific server[/]")
