"""
Manage CPM settings
"""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


# Default settings
DEFAULT_SETTINGS = {
    "add.defaultTarget": "all",  # all, first, ask
    "install.defaultContext": "global",  # global, local
    "uninstall.purgeClients": False,  # true, false
}


def get_settings_path() -> Path:
    """Get settings file path"""
    return Path.home() / ".cpm" / "settings.json"


def load_settings() -> dict:
    """Load settings from file"""
    settings_path = get_settings_path()

    if not settings_path.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with open(settings_path, "r") as f:
            user_settings = json.load(f)

        # Merge with defaults
        settings = DEFAULT_SETTINGS.copy()
        settings.update(user_settings)
        return settings

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load settings: {e}[/]")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Save settings to file"""
    settings_path = get_settings_path()

    # Ensure directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

    except Exception as e:
        console.print(f"[red]Error: Failed to save settings: {e}[/]")
        raise click.Abort()


@click.group()
def settings():
    """
    Manage CPM settings

    Configure default behavior for CPM commands.

    Examples:

        \b
        cpm settings                          # Show all settings
        cpm settings get add.defaultTarget    # Get specific setting
        cpm settings set add.defaultTarget=all# Set setting
        cpm settings reset                    # Reset to defaults
    """
    pass


@settings.command("get")
@click.argument("key", required=False)
def settings_get(key):
    """
    Get setting value(s)

    Examples:

        \b
        cpm settings get                      # Show all settings
        cpm settings get add.defaultTarget    # Get specific setting
    """
    current_settings = load_settings()

    if key:
        # Get specific setting
        if key in current_settings:
            value = current_settings[key]
            console.print(f"\n[cyan]{key}:[/] {value}\n")
        else:
            console.print(f"[red]Error:[/] Unknown setting: {key}")
            console.print(f"\n[dim]Available settings: {', '.join(DEFAULT_SETTINGS.keys())}[/]")
            raise click.Abort()

    else:
        # Show all settings
        console.print("\n[cyan]CPM Settings:[/]\n")

        table = Table(show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Default", style="dim")

        for setting_key, default_value in DEFAULT_SETTINGS.items():
            current_value = current_settings.get(setting_key, default_value)
            is_default = current_value == default_value

            value_str = str(current_value)
            default_str = str(default_value)

            if is_default:
                value_str = f"[dim]{value_str}[/]"

            table.add_row(setting_key, value_str, default_str)

        console.print(table)
        console.print(f"\n[dim]Settings file: {get_settings_path()}[/]\n")


@settings.command("set")
@click.argument("key_value")
def settings_set(key_value):
    """
    Set setting value

    Examples:

        \b
        cpm settings set add.defaultTarget=all
        cpm settings set install.defaultContext=local
        cpm settings set uninstall.purgeClients=true
    """
    # Parse key=value
    if "=" not in key_value:
        console.print("[red]Error:[/] Invalid format. Use: key=value")
        console.print("\n[dim]Example: cpm settings set add.defaultTarget=all[/]")
        raise click.Abort()

    key, value = key_value.split("=", 1)
    key = key.strip()
    value = value.strip()

    # Validate key
    if key not in DEFAULT_SETTINGS:
        console.print(f"[red]Error:[/] Unknown setting: {key}")
        console.print(f"\n[dim]Available settings: {', '.join(DEFAULT_SETTINGS.keys())}[/]")
        raise click.Abort()

    # Parse value based on type
    default_value = DEFAULT_SETTINGS[key]

    if isinstance(default_value, bool):
        # Boolean value
        if value.lower() in ["true", "1", "yes"]:
            parsed_value = True
        elif value.lower() in ["false", "0", "no"]:
            parsed_value = False
        else:
            console.print(f"[red]Error:[/] Invalid boolean value: {value}")
            console.print("[dim]Use: true, false, 1, 0, yes, or no[/]")
            raise click.Abort()

    elif isinstance(default_value, int):
        # Integer value
        try:
            parsed_value = int(value)
        except ValueError:
            console.print(f"[red]Error:[/] Invalid integer value: {value}")
            raise click.Abort()

    else:
        # String value
        parsed_value = value

    # Validate specific settings
    if key == "add.defaultTarget" and parsed_value not in ["all", "first", "ask"]:
        console.print(f"[red]Error:[/] Invalid value for add.defaultTarget: {parsed_value}")
        console.print("[dim]Valid values: all, first, ask[/]")
        raise click.Abort()

    if key == "install.defaultContext" and parsed_value not in ["global", "local"]:
        console.print(f"[red]Error:[/] Invalid value for install.defaultContext: {parsed_value}")
        console.print("[dim]Valid values: global, local[/]")
        raise click.Abort()

    # Save setting
    current_settings = load_settings()
    current_settings[key] = parsed_value
    save_settings(current_settings)

    console.print(f"\n[green]+[/] Set {key} = {parsed_value}\n")


@settings.command("reset")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def settings_reset(yes):
    """
    Reset settings to defaults

    Examples:

        \b
        cpm settings reset                    # Reset with confirmation
        cpm settings reset --yes              # Reset without confirmation
    """
    if not yes:
        console.print("\n[yellow]This will reset all settings to defaults[/]")
        if not click.confirm("Continue?", default=False):
            console.print("[yellow]Aborted[/]")
            return

    # Reset to defaults
    save_settings(DEFAULT_SETTINGS.copy())

    console.print("\n[green]+[/] Settings reset to defaults\n")


@settings.command("list")
def settings_list():
    """
    List all available settings

    Shows all configurable settings and their descriptions.

    Examples:

        \b
        cpm settings list                     # List all settings
    """
    console.print("\n[cyan]Available Settings:[/]\n")

    descriptions = {
        "add.defaultTarget": "Default target when adding servers (all, first, ask)",
        "install.defaultContext": "Default context for installing servers (global, local)",
        "uninstall.purgeClients": "Auto-purge from clients when uninstalling (true, false)",
    }

    for key, default_value in DEFAULT_SETTINGS.items():
        description = descriptions.get(key, "No description available")

        console.print(f"[cyan]{key}[/]")
        console.print(f"  [dim]Default:[/] {default_value}")
        console.print(f"  [dim]Description:[/] {description}")
        console.print()
