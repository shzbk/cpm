"""
Search command v2 - Search official MCP registry

Uses new RegistryClient v2 to search across official registry.
Shows reverse-DNS names and helps users find servers.
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core.registry_v2 import RegistryClient

console = Console()


@click.command()
@click.argument("query", required=False)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Limit number of results",
)
@click.option(
    "--namespace",
    help="Filter by namespace (e.g., io.github.user)",
)
@click.option(
    "--sort",
    type=click.Choice(["name", "version", "recently-updated"]),
    default="name",
    help="Sort results",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Refresh registry cache",
)
def search(
    query: str,
    limit: int,
    namespace: str,
    sort: str,
    refresh: bool,
):
    """
    Search the official MCP registry.

    Examples:

        \b
        cpm search                      # Show all servers
        cpm search mysql                # Search for mysql
        cpm search database             # Search by category
        cpm search --namespace io.github.user

        \b
        cpm search --limit 50           # Get more results
        cpm search --refresh            # Update cache
    """

    registry = RegistryClient()

    # Refresh cache if requested
    if refresh:
        console.print("[cyan]Refreshing registry cache...[/]")
        if registry.refresh_cache():
            console.print("[green][OK][/] Cache refreshed\n")
        else:
            console.print("[yellow][WARN][/] Could not refresh, using cached data\n")

    # Search
    try:
        console.print(f"[cyan]Searching registry...[/]", end="")
        console.print("\r", end="")  # Clear

        results = registry.search_servers(query=query, limit=limit * 2)

        # Filter by namespace if specified
        if namespace:
            results = [
                r
                for r in results
                if r.get("server", r).get("name", "").startswith(namespace)
            ]

        # Limit results
        results = results[:limit]

        if not results:
            console.print("[yellow]No servers found[/]")
            if query:
                console.print(f"\n[dim]Try:[/] cpm search (without query)")
            return

        # Show results table
        table = Table(title=f"Registry Results ({len(results)} servers)")
        table.add_column("Name", style="cyan", width=40)
        table.add_column("Description", style="dim", width=50, no_wrap=False)
        table.add_column("Version", style="yellow", width=10)

        for result in results:
            # Handle both raw and wrapped responses
            server = result.get("server", result) if isinstance(result, dict) else result

            name = server.get("name", "")
            description = server.get("description", "")[:47]
            version = server.get("version", "")

            # Make it look nice
            if len(server.get("description", "")) > 47:
                description += "…"

            table.add_row(name, description, version)

        console.print(table)

        # Footer
        console.print(f"\n[dim]Install: [cyan]cpm install <name>[/cyan][/]")
        console.print(f"[dim]Learn more: [cyan]cpm info <name>[/cyan][/]")

        if len(results) == limit:
            console.print(f"[dim](showing {limit} of more results)[/]")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        import traceback

        if "--debug" in __import__("sys").argv:
            traceback.print_exc()
        raise click.Abort()


@click.command()
@click.argument("server_name")
def info(server_name: str):
    """
    Show detailed information about a server.

    Examples:

        \b
        cpm info io.github.user/mysql
        cpm info mysql                    # Auto-resolves simple name
    """

    from cpm.core.resolver import ServerNameResolver

    registry = RegistryClient()
    resolver = ServerNameResolver(registry)

    try:
        console.print(f"[cyan]Looking up:[/] {server_name}")

        # Resolve name if simple
        full_name = resolver.resolve(server_name)

        # Get server
        server = registry.get_server(full_name)

        # Show details
        console.print(f"\n[bold cyan]{server.name}[/bold cyan] v{server.version}\n")

        console.print(f"[yellow]Description:[/]")
        console.print(f"  {server.description}\n")

        if server.title:
            console.print(f"[yellow]Title:[/] {server.title}\n")

        if server.websiteUrl:
            console.print(f"[yellow]Website:[/] {server.websiteUrl}\n")

        # Repository info
        if server.repository:
            console.print(f"[yellow]Repository:[/]")
            console.print(f"  {server.repository.source}: {server.repository.url}")
            if server.repository.subfolder:
                console.print(f"  Subfolder: {server.repository.subfolder}\n")
            else:
                console.print()

        # Packages
        if server.packages:
            console.print(f"[yellow]Installation Methods:[/]")
            for i, pkg in enumerate(server.packages, 1):
                console.print(
                    f"  {i}. {pkg.registryType.upper()}: {pkg.identifier}"
                )
                console.print(f"     Transport: {pkg.transport.type}")
                if pkg.environmentVariables:
                    console.print(f"     Environment variables:")
                    for env_var in pkg.environmentVariables:
                        required = " (required)" if env_var.isRequired else ""
                        console.print(f"       • {env_var.name}{required}")
            console.print()

        # Remotes
        if server.remotes:
            console.print(f"[yellow]Remote Endpoints:[/]")
            for remote in server.remotes:
                console.print(f"  • {remote.type}: {remote.url}\n")

        # Install command
        console.print(f"[green]Install:[/]")
        console.print(f"  [cyan]cpm install {server_name}[/cyan]\n")

    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise click.Abort()
