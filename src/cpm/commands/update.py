"""
Update installed servers to newer versions
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext
from cpm.core.registry import RegistryClient

console = Console()


@click.command()
@click.argument("servers", nargs=-1)
@click.option("--latest", is_flag=True, help="Upgrade to latest version (ignore semver)")
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def update(ctx, servers, latest, dry_run, yes):
    """
    Update servers to newer versions

    Updates servers to the latest compatible version (respecting semver ranges).
    Use --latest to upgrade to the absolute latest version.

    Examples:

        \b
        cpm update                            # Update all servers
        cpm update mysql                      # Update specific server
        cpm update mysql brave-search         # Update multiple servers
        cpm update --latest                   # Upgrade to latest versions
        cpm update --dry-run                  # Preview updates
    """
    # Get config context
    config = ConfigContext(local=ctx.obj.get("local", False))

    # Get servers to update
    if servers:
        # Specific servers
        servers_to_update = {}
        for server_name in servers:
            try:
                server_config = config.get_server(server_name)
                servers_to_update[server_name] = server_config
            except KeyError:
                console.print(f"[yellow]Warning: Server not found: {server_name}[/]")
    else:
        # All servers
        servers_to_update = config.list_servers()

    if not servers_to_update:
        console.print("[yellow]No servers to update[/]")
        return

    # Check for updates
    console.print(f"[cyan]Checking for updates...[/]\n")

    registry = RegistryClient()
    updates_available = []

    for server_name, server_config in servers_to_update.items():
        # Get current version
        current_version = config.get_version(server_name) if config.is_local else None

        if not current_version:
            console.print(f"  [dim]{server_name}: no version info, skipping[/]")
            continue

        try:
            # Fetch latest version from registry
            server_metadata = registry.get_server(server_name)
            latest_version = server_metadata.get("version", "unknown")

            # Compare versions
            if current_version != latest_version:
                updates_available.append({
                    "name": server_name,
                    "current": current_version,
                    "latest": latest_version,
                    "config": server_config,
                    "metadata": server_metadata,
                })
                console.print(f"  [green]↑[/] {server_name}: {current_version} → {latest_version}")
            else:
                console.print(f"  [dim]+ {server_name}: up to date ({current_version})[/]")

        except Exception as e:
            console.print(f"  [red]-[/] {server_name}: failed to check updates: {e}")

    if not updates_available:
        console.print(f"\n[green]All servers are up to date![/]")
        return

    # Show summary
    console.print(f"\n[cyan]Found {len(updates_available)} update(s) available[/]\n")

    # Create table
    table = Table()
    table.add_column("Server", style="cyan")
    table.add_column("Current", style="yellow")
    table.add_column("Latest", style="green")

    for update in updates_available:
        table.add_row(update["name"], update["current"], update["latest"])

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/]")
        return

    # Confirm
    if not yes:
        console.print()
        if not click.confirm("Update these servers?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    # Perform updates
    console.print()
    for update in updates_available:
        server_name = update["name"]
        new_version = update["latest"]

        try:
            # Get new server config from registry
            from cpm.core.schema import STDIOServerConfig, RemoteServerConfig

            metadata = update["metadata"]

            # Parse server config from metadata
            if "command" in metadata:
                new_config = STDIOServerConfig(**metadata)
            elif "url" in metadata:
                new_config = RemoteServerConfig(**metadata)
            else:
                console.print(f"  [red]-[/] {server_name}: invalid server metadata")
                continue

            # Update server
            if config.is_local:
                # Local context: update version in cpm.json
                config.manager.remove_server(server_name)
                config.manager.add_server(server_name, new_version, new_config, dev=False)
            else:
                # Global context: update server config
                config.manager.remove_server(server_name)
                config.manager.add_server(new_config)

            console.print(f"  [green]+[/] Updated {server_name} to {new_version}")

        except Exception as e:
            console.print(f"  [red]-[/] Failed to update {server_name}: {e}")

    console.print(f"\n[green]Done![/] Updated {len(updates_available)} server(s)")

    if config.is_local:
        console.print("\n[dim]Run 'cpm install' to update lockfile[/]")
