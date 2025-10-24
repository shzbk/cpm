"""
Link local server for development
"""

import json
import click
from pathlib import Path
from rich.console import Console

from cpm.core.config import GlobalConfigManager
from cpm.core.schema import STDIOServerConfig, RemoteServerConfig

console = Console()


@click.command()
@click.argument("server", required=False)
@click.option("--name", type=str, help="Override server name")
def link(server, name):
    """
    Link local server for development

    Makes a local server available globally for testing and development,
    similar to 'npm link'.

    Examples:

        \b
        cd my-server && cpm link              # Link current directory
        cpm link ./path/to/server             # Link specific directory
        cpm link my-server --name custom-name # Link with custom name
    """
    # Determine server path
    if server:
        server_path = Path(server).resolve()
    else:
        server_path = Path.cwd()

    if not server_path.exists():
        console.print(f"[red]Error:[/] Directory not found: {server_path}")
        raise click.Abort()

    if not server_path.is_dir():
        console.print(f"[red]Error:[/] Not a directory: {server_path}")
        raise click.Abort()

    # Look for server manifest
    manifest_file = server_path / "server.json"
    package_json = server_path / "package.json"

    if manifest_file.exists():
        # MCP server manifest
        try:
            with open(manifest_file, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            console.print(f"[red]Error:[/] Failed to read server.json: {e}")
            raise click.Abort()

    elif package_json.exists():
        # npm package with MCP server
        try:
            with open(package_json, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            console.print(f"[red]Error:[/] Failed to read package.json: {e}")
            raise click.Abort()

    else:
        console.print(f"[red]Error:[/] No server.json or package.json found in {server_path}")
        console.print("\n[dim]A valid MCP server must have a server.json or package.json[/]")
        raise click.Abort()

    # Extract server name
    server_name = name or manifest.get("name")

    if not server_name:
        console.print("[red]Error:[/] Could not determine server name")
        console.print("[dim]Use --name to specify a name[/]")
        raise click.Abort()

    # Create server config
    try:
        # Check if it has a command field
        if "command" in manifest:
            server_config = STDIOServerConfig(
                name=server_name,
                command=manifest["command"],
                args=manifest.get("args", []),
                env=manifest.get("env", {}),
            )
        elif "url" in manifest:
            server_config = RemoteServerConfig(
                name=server_name,
                url=manifest["url"],
                headers=manifest.get("headers", {}),
            )
        else:
            # Default: assume it's a node package
            server_config = STDIOServerConfig(
                name=server_name,
                command="node",
                args=[str(server_path / "index.js")],
                env={},
            )

        # Mark as linked (add metadata)
        server_config.version = "linked"

    except Exception as e:
        console.print(f"[red]Error:[/] Invalid server configuration: {e}")
        raise click.Abort()

    # Add to global config
    try:
        config_manager = GlobalConfigManager()

        # Check if already exists
        try:
            existing = config_manager.get_server(server_name)
            console.print(f"[yellow]Warning:[/] Server '{server_name}' already exists")

            if not click.confirm("Overwrite with linked version?", default=True):
                console.print("[yellow]Aborted[/]")
                return
        except KeyError:
            pass

        # Add server
        config_manager.add_server(server_config)

        console.print(f"[green]+[/] Linked {server_name}")
        console.print(f"  [dim]Path: {server_path}[/]")
        console.print(f"\n[dim]Use 'cpm add {server_name}' to add to clients[/]")
        console.print(f"[dim]Use 'cpm unlink {server_name}' to remove link[/]")

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to link server: {e}")
        raise click.Abort()
