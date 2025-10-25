"""
Info command - Show detailed server information
"""

import click
from rich.console import Console

from cpm.core.registry import RegistryClient
from cpm.core.resolver import ServerNameResolver

console = Console()


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
