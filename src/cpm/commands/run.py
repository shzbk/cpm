"""
Run command - Execute MCP servers

Matches specification from COMMANDS.md:
- Function: run(target, http, port, host, local, ...)
- Parses target (server or @group)
- Starts server(s) via FastMCP
- Supports stdio/HTTP/SSE modes
"""

import asyncio
import sys

import click
from rich.console import Console

from cpm.core.context import ConfigContext
from cpm.utils.config_validator import ConfigValidator

console = Console()


def parse_target(target: str, config: ConfigContext):
    """
    Parse target (server or @group)

    Args:
        target: Server name or @group name
        config: ConfigContext instance

    Returns:
        Tuple of (type, servers_dict) where type is 'server' or 'group'
    """
    if target.startswith("@"):
        # Group reference
        group_name = target[1:]
        try:
            servers = config.get_servers_in_group(group_name)
            return ('group', servers)
        except KeyError:
            console.print(f"[red]Error:[/] Group not found: {group_name}")
            console.print(f"\n[dim]List groups:[/] cpm group ls")
            raise click.Abort()
    else:
        # Server reference
        try:
            server = config.get_server(target)
            return ('server', {target: server})
        except KeyError:
            console.print(f"[red]Error:[/] Server not found: {target}")
            console.print(f"\n[dim]Install it:[/] cpm install {target}")
            raise click.Abort()


@click.command()
@click.argument("target")
@click.option("--http", is_flag=True, help="Run in HTTP mode")
@click.option("--sse", is_flag=True, help="Run in SSE mode")
@click.option("--port", type=int, default=6276, help="Port for HTTP/SSE mode")
@click.option("--host", default="127.0.0.1", help="Host for HTTP/SSE mode")
@click.option("--local", is_flag=True, help="Use local config")
@click.pass_context
def run(ctx, target: str, http: bool, sse: bool, port: int, host: str, local: bool):
    """
    Execute MCP server(s) in stdio (default), HTTP, or SSE mode

    TARGET can be a server name or @group name.

    Examples:

        \b
        # STDIO Mode (default)
        cpm run mysql                               # Run single server
        cpm run @database                           # Run all servers in group

        \b
        # HTTP Mode
        cpm run mysql --http                        # HTTP server
        cpm run mysql --http --port 9000            # Custom port
        cpm run mysql --http --host 0.0.0.0         # Expose on network
        cpm run @database --http                    # Run group as HTTP

        \b
        # SSE Mode
        cpm run mysql --sse                         # SSE server

        \b
        # Local context
        cpm run mysql --local                       # Run from local config
        cpm run @database --local --http           # Run local group
    """
    # Get config context
    config = ConfigContext(local=local or ctx.obj.get("local", False))

    # Parse target (server or @group)
    target_type, servers = parse_target(target, config)

    if not servers:
        console.print("[red]Error:[/] No servers found")
        raise click.Abort()

    # Validate options
    if http and sse:
        console.print("[red]Error:[/] Cannot use both --http and --sse")
        raise click.Abort()

    # Check configuration for all servers using validator
    unconfigured_servers = []
    for server_name, server_config in servers.items():
        missing_vars = ConfigValidator.get_missing_vars(server_config)
        if missing_vars:
            unconfigured_servers.append((server_name, missing_vars))

    if unconfigured_servers:
        console.print(f"[red]Error:[/] Cannot run - {len(unconfigured_servers)} server(s) not configured")
        console.print()

        for server_name, missing_vars in unconfigured_servers:
            console.print(f"[yellow]{server_name}:[/] Missing {len(missing_vars)} environment variable(s)")
            for var in missing_vars:
                console.print(f"  - {var}")
            console.print()

        console.print("[dim]Configure with:[/]")
        for server_name, _ in unconfigured_servers:
            console.print(f"  cpm config {server_name}")

        raise click.Abort()

    # Import runtime executor
    try:
        from cpm.runtime.executor import ServerExecutor

        executor = ServerExecutor()

        # Determine mode
        mode = "sse" if sse else "http" if http else "stdio"

        # Display what we're running
        if target_type == 'group':
            console.print(f"[cyan]Running group {target} ({len(servers)} server(s)) in {mode} mode...[/]\n")
            for server_name in servers.keys():
                console.print(f"  * {server_name}")
            console.print()
        else:
            console.print(f"[cyan]Starting {target} in {mode} mode...[/]")

        # Run server(s)
        if len(servers) == 1:
            # Single server
            server = list(servers.values())[0]

            if http or sse:
                asyncio.run(executor.run_http(server, port=port, host=host, sse=sse))
            else:
                console.print("[dim]Server is running and waiting for MCP client connections via stdio.[/]")
                console.print("[dim]This is meant to be used by MCP clients (Claude Desktop, Cursor, etc.)[/]")
                console.print("[dim]Press Ctrl+C to stop the server.[/]\n")
                asyncio.run(executor.run_stdio(server))

        else:
            # Multiple servers (group) - aggregate them
            if http or sse:
                console.print(f"[cyan]Aggregating {len(servers)} servers on {host}:{port}[/]")
                asyncio.run(executor.run_aggregated_http(
                    list(servers.values()),
                    port=port,
                    host=host,
                    sse=sse
                ))
            else:
                console.print(f"[cyan]Aggregating {len(servers)} servers via stdio[/]")
                console.print("[dim]Server is running and waiting for MCP client connections via stdio.[/]")
                console.print("[dim]Press Ctrl+C to stop the servers.[/]\n")
                asyncio.run(executor.run_aggregated_stdio(list(servers.values())))

    except ImportError as e:
        console.print("[red]Error:[/] Failed to import FastMCP runtime")
        console.print(f"[dim]Details:[/] {str(e)}")
        console.print("\n[dim]Try reinstalling CPM with:[/]")
        console.print("[cyan]  pip install --upgrade cpm[/]")
        console.print("\n[dim]Or install FastMCP manually:[/]")
        console.print("[cyan]  pip install --upgrade fastmcp[/]")
        raise click.Abort()

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/]")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        import traceback
        if "--debug" in sys.argv or "--verbose" in sys.argv:
            console.print("\n[dim]Traceback:[/]")
            traceback.print_exc()
        raise click.Abort()
