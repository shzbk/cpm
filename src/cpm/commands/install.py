"""
Install command - Add MCP servers from registry
"""

import click
from rich.console import Console

from cpm.core import GlobalConfigManager, RegistryClient, STDIOServerConfig, RemoteServerConfig
from cpm.core.context import ConfigContext
from cpm.utils.config_validator import ConfigValidator

console = Console()


@click.command()
@click.argument("server_names", nargs=-1)
@click.option("--local", "-l", is_flag=True, help="Install to local project (server.json)")
@click.option("--global", "-g", "global_flag", is_flag=True, help="Force global installation")
@click.option("--save-dev", is_flag=True, help="Install as dev dependency (local only)")
@click.option("--version", help="Specific version to install")
@click.option("--frozen-lockfile", is_flag=True, help="Use exact versions from lockfile")
@click.option("--force", is_flag=True, help="Force reinstall if already exists")
@click.option("--alias", help="Install with a different name")
@click.option("--set", "-s", multiple=True, help="Set environment variable (KEY=VALUE)")
@click.pass_context
def install(ctx, server_names: tuple, local: bool, global_flag: bool, save_dev: bool, version: str, frozen_lockfile: bool, force: bool, alias: str, set: tuple):
    """
    Install MCP server(s) from the registry

    Auto-detects context: uses server.json if present, otherwise global.
    If no server names provided, installs from server.json (like npm install).

    Examples:

        \b
        # Global installation (no server.json)
        cpm install brave-search                          # Install globally
        cpm install brave-search mysql                    # Install multiple servers

        \b
        # Local project (has server.json - auto-detected)
        cpm install mysql                                 # Auto-adds to server.json
        cpm install mysql --global                        # Force global (ignore server.json)

        \b
        # Explicit local
        cpm install mysql --local                         # Force local (needs server.json)
        cpm install mysql --save-dev                      # Add to devServers
        cpm install                                       # Install from server.json
    """
    # Get config context
    global_ctx_flag = ctx.obj.get("global", False) or global_flag
    config = ConfigContext(
        local=local or save_dev or ctx.obj.get("local", False),
        global_force=global_ctx_flag
    )
    registry = RegistryClient()

    # Case 1: No server names - install from cpm.json
    if not server_names:
        if not config.is_local:
            console.print("[red]Error:[/] No servers specified")
            console.print("\n[dim]Usage:[/] cpm install <server>")
            console.print("[dim]Or run in project with cpm.json[/]")
            raise click.Abort()

        # Install from cpm.json
        console.print("[cyan]Installing from cpm.json...[/]\n")

        try:
            manifest = config.manager.load_manifest()
            all_servers = {**manifest.servers, **manifest.devServers}

            if not all_servers:
                console.print("[yellow]No servers to install[/]")
                return

            console.print(f"Installing {len(all_servers)} server(s)...\n")

            for server_name, server_version in all_servers.items():
                try:
                    # Fetch from registry
                    server_meta = registry.get_server(server_name)
                    server_config = _create_server_config(server_name, server_meta, alias=None, env_overrides={})

                    # Add to local config
                    is_dev = server_name in manifest.devServers
                    config.add_server(server_name, server_config, version=server_version, dev=is_dev)

                    console.print(f"  [green]+[/] Installed {server_name}")

                except Exception as e:
                    console.print(f"  [red]-[/] Failed to install {server_name}: {e}")

            console.print(f"\n[green]Done![/] Installed {len(all_servers)} server(s)")

        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            raise click.Abort()

        return

    # Case 2: Install specific server(s)
    for server_name in server_names:
        _install_single_server(
            server_name=server_name,
            config=config,
            registry=registry,
            version=version,
            save_dev=save_dev,
            force=force,
            alias=alias,
            env_overrides=dict(pair.split("=", 1) for pair in set) if set else {},
        )


def _create_server_config(server_name: str, server_meta: dict, alias: str = None, env_overrides: dict = None):
    """Create server config from registry metadata"""
    # Get installation info
    installations = server_meta.get("installations", {})
    if not installations:
        raise ValueError("No installation information available")

    # Use first/recommended installation method
    install_method = None
    for key, method in installations.items():
        if method.get("recommended", False):
            install_method = method
            break

    if not install_method:
        install_method = list(installations.values())[0]

    # Extract command and args
    command = install_method.get("command", "")
    args = install_method.get("args", [])
    env_vars = install_method.get("env", {})

    # Apply env overrides
    if env_overrides:
        for key, value in env_overrides.items():
            # Case-insensitive match
            matched = False
            for env_key in list(env_vars.keys()):
                if env_key.upper() == key.upper():
                    env_vars[env_key] = value
                    matched = True
                    break

            if not matched:
                raise ValueError(f"Variable '{key}' not found in {server_name}")

    # Check if it's a remote server
    if "url" in install_method:
        return RemoteServerConfig(
            name=alias or server_name,
            url=install_method["url"],
            headers=install_method.get("headers", {}),
        )
    else:
        return STDIOServerConfig(
            name=alias or server_name,
            command=command,
            args=args,
            env=env_vars,
        )


def _install_single_server(server_name: str, config: ConfigContext, registry: RegistryClient, version: str, save_dev: bool, force: bool, alias: str, env_overrides: dict):
    """Install a single server"""
    # Get server from registry
    try:
        server_meta = registry.get_server(server_name)
    except Exception:
        console.print(f"[red]Error:[/] Server '{server_name}' not found in registry")
        console.print(f"\n[dim]Try:[/] cpm search {server_name}")
        return

    # Check if server was found
    if server_meta is None:
        console.print(f"[red]Error:[/] Server '{server_name}' not found in registry")
        console.print(f"\n[dim]Try:[/] cpm search {server_name}")
        return

    # Display server info
    display_name = server_meta.get("display_name", server_name)
    description = server_meta.get("description", "No description available")

    console.print(f"\n[bold]{display_name}[/]")
    console.print(f"[dim]{description}[/]\n")

    # Check if already installed
    install_name = alias or server_name
    if not force and config.server_exists(install_name):
        console.print(f"[yellow]Server '{install_name}' is already installed[/]")
        console.print(f"[dim]Use --force to reinstall:[/] cpm install {server_name} --force")
        return

    # Create server configuration
    try:
        server_config = _create_server_config(server_name, server_meta, alias, env_overrides)
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        return

    # Add to config
    try:
        if config.is_local:
            # Local context
            install_version = version or server_meta.get("version", "latest")
            config.add_server(install_name, server_config, version=install_version, dev=save_dev)
        else:
            # Global context
            config.add_server(install_name, server_config)

        console.print(f"[green]+[/] Installed [cyan]{display_name}[/]")

        # Check if configuration is needed using validator
        missing_vars = ConfigValidator.get_missing_vars(server_config)

        if missing_vars:
            console.print("\n[yellow]Configuration Required[/]")
            console.print(f"\nMissing {len(missing_vars)} environment variable(s):")
            for var in missing_vars:
                console.print(f"  - {var}")

            if len(missing_vars) == 1:
                console.print(f"\nSet it with:")
                console.print(f"  cpm config set {install_name} {missing_vars[0]}=<value>")
            else:
                console.print(f"\nSet them with:")
                console.print(f"  cpm config set {install_name} \\")
                for i, var in enumerate(missing_vars):
                    if i < len(missing_vars) - 1:
                        console.print(f"    {var}=<value> \\")
                    else:
                        console.print(f"    {var}=<value>")

            console.print(f"\nOr interactive:")
            console.print(f"  cpm config {install_name}")
        else:
            console.print(f"[green]Ready to use:[/] cpm run {install_name}")

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to install: {e}")
