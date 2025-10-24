"""
Config command - Configure MCP server environment variables

Redesigned to match npm config command style:
- cpm config set <server> KEY=VALUE [KEY=VALUE ...]
- cpm config get <server> [KEY ...]
- cpm config delete <server> KEY [KEY ...]
- cpm config list [<server>] [--json]
- cpm config edit <server>

Options work across all subcommands:
- -g, --global        Use global config
- -l, --local         Use local config
- --json              JSON output format
- --long              Show full values (don't mask sensitive data)
- --editor <editor>   Specify editor for edit command
"""

import os
import subprocess
import sys
import tempfile

import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext
from cpm.core.registry import RegistryClient

console = Console()


@click.group()
@click.option("-g", "--global", "use_global", is_flag=True, help="Use global config")
@click.option("-l", "--local", "use_local", is_flag=True, help="Use local config")
@click.option("--editor", help="Specify editor to use")
@click.option("--json", "output_json", is_flag=True, help="JSON output format")
@click.option("--long", "show_long", is_flag=True, help="Show full values (don't mask)")
@click.pass_context
def config(ctx, use_global, use_local, editor, output_json, show_long):
    """
    Manage CPM server configuration

    Subcommands:
      set      Set environment variables
      get      Get environment variable values
      delete   Delete environment variables
      list     List all configurations
      edit     Open configuration in editor

    Examples:

        cpm config set mysql MYSQL_HOST=localhost MYSQL_USER=root
        cpm config get mysql MYSQL_HOST
        cpm config delete mysql MYSQL_PASSWORD
        cpm config list mysql
        cpm config edit mysql
    """
    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["use_global"] = use_global
    ctx.obj["use_local"] = use_local
    ctx.obj["editor"] = editor
    ctx.obj["output_json"] = output_json
    ctx.obj["show_long"] = show_long


# ============================================================================
# SUBCOMMAND: config set
# ============================================================================

@config.command(name="set")
@click.argument("server")
@click.argument("key_values", nargs=-1, required=True)
@click.pass_context
def config_set(ctx, server, key_values):
    """
    Set environment variables for a server

    Examples:
        cpm config set mysql MYSQL_HOST=localhost MYSQL_USER=root
        cpm config set mysql -l MYSQL_HOST=db.local  (local config)
    """
    config_ctx = _get_config_context(ctx)
    _set_variables(server, key_values, config_ctx, ctx)


# ============================================================================
# SUBCOMMAND: config get
# ============================================================================

@config.command(name="get")
@click.argument("server")
@click.argument("keys", nargs=-1)
@click.pass_context
def config_get(ctx, server, keys):
    """
    Get environment variable values for a server

    Examples:
        cpm config get mysql                    # Show all variables
        cpm config get mysql MYSQL_HOST         # Show specific variable
        cpm config get mysql MYSQL_HOST MYSQL_USER MYSQL_PORT
    """
    config_ctx = _get_config_context(ctx)
    _get_variables(server, keys, config_ctx, ctx)


# ============================================================================
# SUBCOMMAND: config delete
# ============================================================================

@config.command(name="delete")
@click.argument("server")
@click.argument("keys", nargs=-1, required=True)
@click.pass_context
def config_delete(ctx, server, keys):
    """
    Delete environment variables from a server

    Examples:
        cpm config delete mysql MYSQL_PASSWORD
        cpm config delete mysql MYSQL_PASSWORD MYSQL_PORT
    """
    config_ctx = _get_config_context(ctx)
    _delete_variables(server, keys, config_ctx, ctx)


# ============================================================================
# SUBCOMMAND: config list
# ============================================================================

@config.command(name="list")
@click.argument("server", required=False)
@click.pass_context
def config_list(ctx, server):
    """
    List all server configurations

    Examples:
        cpm config list              # List all servers with config status
        cpm config list mysql        # Show mysql configuration
        cpm config list mysql --json # JSON format
    """
    config_ctx = _get_config_context(ctx)
    _list_configs(server, config_ctx, ctx)


# ============================================================================
# SUBCOMMAND: config edit
# ============================================================================

@config.command(name="edit")
@click.argument("server")
@click.pass_context
def config_edit(ctx, server):
    """
    Edit server configuration in text editor

    Examples:
        cpm config edit mysql
        cpm config edit mysql --editor nano
    """
    config_ctx = _get_config_context(ctx)
    _edit_config(server, config_ctx, ctx)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_config_context(ctx):
    """Get ConfigContext based on options"""
    use_global = ctx.obj.get("use_global", False)
    use_local = ctx.obj.get("use_local", False)

    # Determine context
    if use_global:
        local = False
    elif use_local:
        local = True
    else:
        # Auto-detect: try to check if local config exists without raising error
        try:
            temp_ctx = ConfigContext(local=True)
            local = True
        except FileNotFoundError:
            # No local config, use global
            local = False

    return ConfigContext(local=local)


def _set_variables(server: str, key_values: tuple, config_ctx: ConfigContext, ctx):
    """Set environment variables"""
    try:
        server_config = config_ctx.get_server(server)
    except KeyError:
        console.print(f"[red]Error:[/] Server '{server}' not found")
        raise click.Abort()

    if not hasattr(server_config, "env"):
        console.print(f"[yellow]Server '{server}' has no environment variables[/]")
        return

    env_vars = server_config.env.copy()
    updated_count = 0

    for var_pair in key_values:
        if "=" not in var_pair:
            console.print(f"[red]Error:[/] Invalid format '{var_pair}'. Use KEY=VALUE")
            raise click.Abort()

        key, value = var_pair.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Case-insensitive match
        matched = False
        for env_key in list(env_vars.keys()):
            if env_key.upper() == key.upper():
                env_vars[env_key] = value
                matched = True
                updated_count += 1
                console.print(f"[green]+[/] {env_key} = {value if 'password' not in env_key.lower() else '****'}")
                break

        if not matched:
            console.print(f"[red]-[/] Variable '{key}' not found")
            console.print(f"[dim]Available:[/] {', '.join(env_vars.keys())}")
            raise click.Abort()

    if updated_count > 0:
        config_ctx.update_server_config(server, env_vars)
        console.print(f"\n[green]+ Updated {updated_count} variable(s)[/]")


def _get_variables(server: str, keys: tuple, config_ctx: ConfigContext, ctx):
    """Get environment variable values"""
    try:
        server_config = config_ctx.get_server(server)
    except KeyError:
        console.print(f"[red]Error:[/] Server '{server}' not found")
        raise click.Abort()

    if not hasattr(server_config, "env") or not server_config.env:
        console.print(f"[yellow]Server '{server}' has no environment variables[/]")
        return

    env_vars = server_config.env
    show_long = ctx.obj.get("show_long", False)
    output_json = ctx.obj.get("output_json", False)

    # If specific keys requested, filter
    if keys:
        filtered_vars = {}
        for key in keys:
            matched = False
            for env_key, value in env_vars.items():
                if env_key.upper() == key.upper():
                    filtered_vars[env_key] = value
                    matched = True
                    break
            if not matched:
                console.print(f"[yellow]! Key '{key}' not found[/]")
        env_vars = filtered_vars

    if output_json:
        import json
        print(json.dumps(env_vars, indent=2))
    else:
        table = Table(title=f"{server} Configuration")
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="dim")

        for var_name, value in env_vars.items():
            if show_long or (not isinstance(value, str) or not value.startswith("${")):
                if any(k in var_name.lower() for k in ["password", "secret", "token", "key"]) and not show_long:
                    display_value = "****"
                else:
                    display_value = value
            else:
                display_value = "[red]not configured[/]"
            table.add_row(var_name, display_value)

        console.print(table)


def _delete_variables(server: str, keys: tuple, config_ctx: ConfigContext, ctx):
    """Delete environment variables"""
    try:
        server_config = config_ctx.get_server(server)
    except KeyError:
        console.print(f"[red]Error:[/] Server '{server}' not found")
        raise click.Abort()

    if not hasattr(server_config, "env"):
        console.print(f"[yellow]Server '{server}' has no environment variables[/]")
        return

    env_vars = server_config.env.copy()
    deleted_count = 0

    for key in keys:
        matched = False
        for env_key in list(env_vars.keys()):
            if env_key.upper() == key.upper():
                del env_vars[env_key]
                deleted_count += 1
                console.print(f"[green]+[/] Deleted {env_key}")
                matched = True
                break

        if not matched:
            console.print(f"[red]-[/] Variable '{key}' not found")

    if deleted_count > 0:
        config_ctx.update_server_config(server, env_vars)
        console.print(f"\n[green]+ Deleted {deleted_count} variable(s)[/]")


def _list_configs(server: str, config_ctx: ConfigContext, ctx):
    """List server configurations"""
    output_json = ctx.obj.get("output_json", False)

    if server:
        # Show single server config
        try:
            server_config = config_ctx.get_server(server)
        except KeyError:
            console.print(f"[red]Error:[/] Server '{server}' not found")
            raise click.Abort()

        if hasattr(server_config, "env") and server_config.env:
            _get_variables(server, (), config_ctx, ctx)
        else:
            console.print(f"[yellow]Server '{server}' has no environment variables[/]")
    else:
        # List all servers with config status
        servers = config_ctx.list_servers()
        if output_json:
            import json
            config_summary = {}
            for srv_name, srv_config in servers.items():
                if hasattr(srv_config, "env"):
                    configured = sum(1 for v in srv_config.env.values() if not (isinstance(v, str) and v.startswith("${")))
                    total = len(srv_config.env)
                    config_summary[srv_name] = {"configured": configured, "total": total}
            print(json.dumps(config_summary, indent=2))
        else:
            table = Table(title="Server Configurations")
            table.add_column("Server", style="cyan")
            table.add_column("Config Status", style="dim")

            for srv_name, srv_config in servers.items():
                if hasattr(srv_config, "env") and srv_config.env:
                    configured = sum(1 for v in srv_config.env.values() if not (isinstance(v, str) and v.startswith("${")))
                    total = len(srv_config.env)
                    status = f"{configured}/{total} configured"
                    table.add_row(srv_name, status)
                else:
                    table.add_row(srv_name, "[dim]no variables[/]")

            console.print(table)


def _edit_config(server: str, config_ctx: ConfigContext, ctx):
    """Edit configuration in editor"""
    try:
        server_config = config_ctx.get_server(server)
    except KeyError:
        console.print(f"[red]Error:[/] Server '{server}' not found")
        raise click.Abort()

    if not hasattr(server_config, "env"):
        console.print(f"[yellow]Server '{server}' has no environment variables[/]")
        return

    env_vars = server_config.env

    # Build config content
    lines = [
        f"# Configuration for {server}",
        f"# Edit values below and save",
        f"# Lines starting with # are comments",
        "",
    ]

    for var_name, value in env_vars.items():
        if isinstance(value, str) and value.startswith("${"):
            lines.append(f"# REQUIRED: {var_name}")
        else:
            lines.append(f"# {var_name}")
        lines.append(f"{var_name}={value}")
        lines.append("")

    content = "\n".join(lines)

    # Get editor
    editor_cmd = ctx.obj.get("editor") or os.environ.get("EDITOR") or os.environ.get("VISUAL")

    if not editor_cmd:
        for cmd in ["code", "nano", "vim", "vi", "notepad"]:
            if _command_exists(cmd):
                editor_cmd = cmd
                break

    if not editor_cmd:
        console.print("[red]Error:[/] No editor found")
        raise click.Abort()

    # Create temp file and edit
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    try:
        subprocess.run([editor_cmd, temp_path], check=False)

        if not os.path.exists(temp_path):
            console.print("[yellow]Cancelled[/]")
            return

        with open(temp_path, "r", encoding="utf-8") as f:
            modified_content = f.read()

        new_env = {}
        for line in modified_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                if key.strip() and value.strip():
                    new_env[key.strip()] = value.strip()

        if new_env != env_vars:
            config_ctx.update_server_config(server, new_env)
            console.print("[green]+ Configuration saved[/]")
        else:
            console.print("[yellow]No changes[/]")

    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


def _handle_view(server: str, env_vars: dict):
    """Show current configuration"""
    table = Table(title=f"{server} Configuration")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Value", style="dim")

    for var_name, value in env_vars.items():
        if value.startswith("${") and value.endswith("}"):
            status = "[red]Not configured[/]"
            display_value = "[dim]-[/]"
        else:
            status = "[green]Configured[/]"
            # Mask sensitive values
            if any(keyword in var_name.lower() for keyword in ["password", "secret", "token", "key"]):
                display_value = "[yellow]********[/]"
            else:
                # Truncate long values
                display_value = value[:50] + ("..." if len(value) > 50 else "")

        table.add_row(var_name, status, display_value)

    console.print(table)


def _handle_set(server: str, server_config, config_ctx: ConfigContext, key_values: tuple):
    """Set environment variables programmatically"""
    if not key_values:
        console.print("[red]Error:[/] No variables specified")
        console.print("\n[dim]Usage:[/] cpm config mysql --set HOST=localhost PORT=3306")
        console.print("[dim]Or:[/] cpm config mysql HOST=localhost PORT=3306")
        raise click.Abort()

    env_vars = server_config.env.copy()
    updated_count = 0

    for var_pair in key_values:
        if "=" not in var_pair:
            console.print(f"[red]Error:[/] Invalid format '{var_pair}'. Use KEY=VALUE")
            console.print(f"\n[dim]Example:[/] cpm config {server} HOST=localhost")
            raise click.Abort()

        key, value = var_pair.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Case-insensitive exact match
        matched = False
        for env_key in list(env_vars.keys()):
            if env_key.upper() == key.upper():
                env_vars[env_key] = value
                matched = True
                updated_count += 1
                console.print(f"[green]+[/] Updated {env_key} = {value if 'password' not in env_key.lower() else '********'}")
                break

        if not matched:
            console.print(f"[red]Error:[/] Variable '{key}' not found in {server}")
            console.print(f"\n[dim]Available variables:[/]")
            for env_key in env_vars.keys():
                console.print(f"  - {env_key}")
            raise click.Abort()

    # Save the configuration
    if updated_count > 0:
        try:
            config_ctx.update_server_config(server, env_vars)
            console.print(f"\n[green]Configuration saved![/] Updated {updated_count} variable(s)")
            _handle_view(server, env_vars)
        except Exception as e:
            console.print(f"[red]Error:[/] Failed to save configuration: {e}")
            raise click.Abort()


def _handle_edit(server: str, server_config, config_ctx: ConfigContext):
    """Open configuration in text editor"""
    env_vars = server_config.env

    # Build the config content
    lines = [
        f"# Configuration for {server}",
        f"# Edit the values below and save the file",
        f"# Lines starting with # are comments and will be ignored",
        "",
    ]

    for var_name, value in env_vars.items():
        # Add comment for placeholders
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            lines.append(f"# REQUIRED: {var_name}")
        else:
            lines.append(f"# {var_name}")

        lines.append(f"{var_name}={value}")
        lines.append("")

    content = "\n".join(lines)

    # Get editor
    editor_cmd = os.environ.get("EDITOR") or os.environ.get("VISUAL")

    # Try common editors if EDITOR not set
    if not editor_cmd:
        for cmd in ["code", "nano", "vim", "vi", "notepad"]:
            if _command_exists(cmd):
                editor_cmd = cmd
                break

    if not editor_cmd:
        console.print("[red]Error:[/] No editor found")
        console.print(f"[dim]Set the EDITOR environment variable or use:[/] cpm config {server}")
        raise click.Abort()

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    try:
        console.print(f"[dim]Opening in {editor_cmd}...[/]")

        # Open editor and wait for it to close
        result = subprocess.run([editor_cmd, temp_path], check=False)

        if result.returncode != 0:
            console.print("[red]Error:[/] Editor exited with error")
            return

        # Check if file still exists after editor closes
        if not os.path.exists(temp_path):
            console.print("[yellow]Configuration cancelled - file was deleted[/]")
            return

        # Read the modified file
        with open(temp_path, "r", encoding="utf-8") as f:
            modified_content = f.read()

        # Parse the modified content
        new_env = {}
        for line in modified_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    new_env[key] = value

        # Check if anything changed
        if new_env != env_vars:
            # Update the server config
            config_ctx.update_server_config(server, new_env)
            console.print("\n[green]+ Configuration saved![/]")
            _handle_view(server, new_env)
        else:
            console.print("\n[yellow]No changes made[/]")

    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass


def _handle_reset(server: str, server_config, config_ctx: ConfigContext):
    """Reset configuration to defaults"""
    # Get original env vars from registry
    registry = RegistryClient()

    try:
        server_meta = registry.get_server(server)
    except Exception:
        console.print(f"[red]Error:[/] Cannot reset - server '{server}' not found in registry")
        raise click.Abort()

    installations = server_meta.get("installations", {})
    if not installations:
        console.print(f"[red]Error:[/] Cannot reset - no installation info available")
        raise click.Abort()

    # Get first/recommended installation method
    install_method = None
    for key, method in installations.items():
        if method.get("recommended", False):
            install_method = method
            break
    if not install_method:
        install_method = list(installations.values())[0]

    # Get original env vars (with placeholders)
    original_env = install_method.get("env", {})

    # Update server env
    config_ctx.update_server_config(server, original_env)

    console.print(f"[green]+ Configuration reset to defaults![/]")
    _handle_view(server, original_env)


def _handle_interactive(server: str, server_config, config_ctx: ConfigContext):
    """Interactive configuration using questionary"""
    try:
        import questionary
    except ImportError:
        console.print("[yellow]Interactive mode requires questionary package[/]")
        console.print("[dim]Install with:[/] pip install questionary")
        console.print("\n[dim]Or use:[/] cpm config {server} --set KEY=VALUE")
        raise click.Abort()

    console.print(f"\n[bold cyan]{server} Configuration[/]")
    console.print("[dim]Select fields to edit using arrow keys, Enter to confirm, Ctrl+C to cancel[/]\n")

    # Get current values
    env_vars = server_config.env.copy()
    current_values = env_vars.copy()

    while True:
        # Build menu choices showing current state
        choices = []
        for var_name, value in current_values.items():
            is_placeholder = isinstance(env_vars[var_name], str) and env_vars[var_name].startswith("${")

            if is_placeholder and value.startswith("${"):
                # Not configured yet
                choices.append(f"{var_name} (not set)")
            else:
                # Configured - show value
                if any(k in var_name.lower() for k in ["password", "secret", "token", "key"]):
                    display_val = "********"
                else:
                    display_val = value[:40] + ("..." if len(value) > 40 else "")
                choices.append(f"{var_name} [OK] {display_val}")

        choices.append("──────────────")
        choices.append("Save and Exit")
        choices.append("Cancel")

        try:
            # Show menu
            selection = questionary.select(
                "Select a field to edit:",
                choices=choices
            ).ask()

            if selection is None or selection == "Cancel":
                console.print("\n[yellow]Configuration cancelled[/]")
                return

            if selection == "Save and Exit":
                break

            if selection == "──────────────":
                continue

            # Extract variable name from selection
            if " (not set)" in selection:
                var_name = selection.replace(" (not set)", "")
            elif " [OK] " in selection:
                var_name = selection.split(" [OK] ")[0]
            else:
                var_name = selection

            current_value = current_values[var_name]
            is_placeholder = isinstance(env_vars[var_name], str) and env_vars[var_name].startswith("${")
            is_password = any(k in var_name.lower() for k in ["password", "secret", "token", "key"])

            default = "" if is_placeholder else current_value

            # Ask for new value
            console.print()
            if is_password:
                new_value = questionary.password(
                    f"Enter value for {var_name}:",
                    default=default
                ).ask()
            else:
                new_value = questionary.text(
                    f"Enter value for {var_name}:",
                    default=default
                ).ask()

            if new_value is not None and new_value:
                current_values[var_name] = new_value
                console.print(f"[green]+ Updated {var_name}[/]\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled[/]")
            sys.exit(0)

    # Check if anything changed
    if current_values != env_vars:
        # Update the server config
        config_ctx.update_server_config(server, current_values)
        console.print("\n[green]+ Configuration saved![/]")
        _handle_view(server, current_values)
    else:
        console.print("\n[yellow]No changes made[/]")


def _command_exists(cmd: str) -> bool:
    """Check if a command exists"""
    try:
        # Special handling for notepad on Windows
        if cmd == "notepad":
            result = subprocess.run(["where", "notepad"], capture_output=True, check=False)
            return result.returncode == 0

        # For other commands, try --version
        subprocess.run([cmd, "--version"], capture_output=True, check=False, timeout=2)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
