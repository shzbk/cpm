"""
Install command v2 - Install servers from MCP Official Registry

Uses new architecture:
- ServerNameResolver: Maps simple names to registry names
- ServerConfigAdapter: Converts registry format to runtime config
- RegistryClient v2: Fetches from official registry
- ServerLockfile: Pins versions with metadata
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core.adapter import ServerConfigAdapter
from cpm.core.context import ConfigContext
from cpm.core.registry_v2 import RegistryClient
from cpm.core.resolver import ServerNameResolver
from cpm.core.schema import ServerLockEntry, ServerLockfile, ServerManifest

console = Console()


@click.command()
@click.argument("server_names", nargs=-1)
@click.option("--local", "-l", is_flag=True, help="Install to local project (server.json)")
@click.option("--global", "-g", "global_flag", is_flag=True, help="Install globally")
@click.option("--save-dev", is_flag=True, help="Install as dev dependency (local only)")
@click.option("--version", help="Specific version to install (default: latest)")
@click.option("--alias", help="Install with different name")
@click.option("--set", "-s", multiple=True, help="Set environment variable (KEY=VALUE)")
@click.option("--force", is_flag=True, help="Force reinstall")
@click.pass_context
def install(
    ctx,
    server_names: tuple,
    local: bool,
    global_flag: bool,
    save_dev: bool,
    version: str,
    alias: str,
    set: tuple,
    force: bool,
):
    """
    Install MCP servers from official registry.

    Fetches from: https://registry.modelcontextprotocol.io

    Examples:

        \b
        # Global installation
        cpm install io.github.user/mysql
        cpm install mysql                    # Auto-resolves simple name

        \b
        # Local project
        cpm install mysql --local
        cpm install mysql --save-dev
        cpm install                          # Install from server.json

        \b
        # Version management
        cpm install mysql@1.0.0
        cpm install mysql --version latest

        \b
        # Configuration
        cpm install mysql --set MYSQL_HOST=localhost
    """

    # Get context
    config = ConfigContext(
        local=local or save_dev or ctx.obj.get("local", False),
        global_force=global_flag or ctx.obj.get("global", False),
    )
    registry = RegistryClient()
    resolver = ServerNameResolver(registry)

    # Parse env overrides
    env_overrides = {}
    if set:
        for item in set:
            key, value = item.split("=", 1)
            env_overrides[key] = value

    # Case 1: No server names - install from manifest
    if not server_names:
        if not config.is_local:
            console.print("[red]Error:[/] No servers specified")
            console.print("\n[dim]Usage:[/] cpm install <server-name>")
            console.print("[dim]Or run in project with server.json[/]")
            raise click.Abort()

        _install_from_manifest(config, registry, resolver)
        return

    # Case 2: Install specific servers
    for server_name in server_names:
        _install_single_server(
            server_name=server_name,
            config=config,
            registry=registry,
            resolver=resolver,
            version=version,
            alias=alias,
            save_dev=save_dev,
            env_overrides=env_overrides,
            force=force,
        )


def _install_from_manifest(config, registry, resolver):
    """Install servers listed in server.json / server-lock.json."""

    console.print("[cyan]Installing from server.json...[/]\n")

    try:
        manifest = config.manager.load_manifest()
        all_servers = {**manifest.servers, **manifest.devServers}

        if not all_servers:
            console.print("[yellow]No servers to install[/]")
            return

        console.print(f"Installing {len(all_servers)} server(s)...\n")

        lockfile = ServerLockfile()
        installed = 0

        for server_name, version_spec in all_servers.items():
            try:
                # Resolve name
                full_name = resolver.resolve(server_name)

                # Get from registry
                server_json = registry.get_server(full_name, version=version_spec)

                # Adapt to runtime config
                runtime_config = ServerConfigAdapter.adapt(server_json)

                # Add to config
                is_dev = server_name in manifest.devServers
                config.add_server(server_name, runtime_config, dev=is_dev)

                # Add to lockfile
                lockfile.servers[server_name] = ServerLockEntry(
                    resolved=full_name,
                    version=server_json.version,
                    registryMetadata=server_json,
                )

                console.print(f"  [green][OK][/] {server_name}@{server_json.version}")
                installed += 1

            except Exception as e:
                console.print(f"  [red][FAIL][/] {server_name}: {e}")

        # Save lockfile
        config.manager.save_lockfile(lockfile)

        console.print(
            f"\n[green]Done![/] Installed {installed}/{len(all_servers)} server(s)"
        )

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise click.Abort()


def _install_single_server(
    server_name: str,
    config,
    registry,
    resolver,
    version,
    alias,
    save_dev,
    env_overrides,
    force,
):
    """Install a single server."""

    try:
        # Resolve name
        full_name = resolver.resolve(server_name)
        console.print(f"\n[cyan]Installing:[/] {full_name}")

        # Get from registry
        server_json = registry.get_server(full_name, version=version or "latest")
        console.print(f"[dim]Version:[/] {server_json.version}")
        console.print(f"[dim]{server_json.description}[/]\n")

        # Check if already installed
        install_name = alias or server_name
        if not force and config.server_exists(install_name):
            console.print(
                f"[yellow]Already installed:[/] {install_name} "
                f"(use --force to reinstall)"
            )
            return

        # Adapt to runtime config
        runtime_config = ServerConfigAdapter.adapt(
            server_json,
            simple_name=install_name,
            env_overrides=env_overrides or {},
        )

        # Add to config
        config.add_server(install_name, runtime_config, dev=save_dev)

        # Update lockfile
        lockfile = config.manager.load_lockfile()
        lockfile.servers[install_name] = ServerLockEntry(
            resolved=full_name,
            version=server_json.version,
            registryMetadata=server_json,
        )
        config.manager.save_lockfile(lockfile)

        # Check missing vars
        missing_vars = ServerConfigAdapter.get_missing_required_vars(runtime_config)

        if missing_vars:
            console.print("[yellow]Configuration Required[/]\n")
            console.print(f"Missing {len(missing_vars)} environment variable(s):\n")
            for var in missing_vars:
                console.print(f"  • {var}")

            console.print(f"\nSet them with:")
            console.print(f"  [cyan]cpm config {install_name}[/]")
        else:
            console.print(
                f"[green][OK][/] Ready to use: [cyan]cpm run {install_name}[/]"
            )

    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        if "No server found" in str(e):
            console.print(f"[dim]Search for it:[/] cpm search {server_name}")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        import traceback

        if "--debug" in __import__("sys").argv:
            traceback.print_exc()
        raise click.Abort()
