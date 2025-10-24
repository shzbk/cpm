"""
Upgrade CPM itself
"""

import click
import subprocess
import sys
from rich.console import Console

console = Console()


@click.command()
@click.option("--check", is_flag=True, help="Check for updates without installing")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def upgrade(check, yes):
    """
    Upgrade CPM to the latest version

    Updates the CPM package using pip.

    Examples:

        \b
        cpm upgrade                           # Upgrade CPM
        cpm upgrade --check                   # Check for updates only
        cpm upgrade --yes                     # Upgrade without confirmation
    """
    console.print("[cyan]Checking for CPM updates...[/]\n")

    try:
        # Get current version
        from cpm import __version__ as current_version

        console.print(f"[dim]Current version:[/] {current_version}")

        # Check for latest version on PyPI
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "cpm-mcp"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            console.print(f"[red]Error:[/] Failed to check for updates")
            if result.stderr:
                console.print(f"[dim]{result.stderr}[/]")
            raise click.Abort()

        # Parse output to find latest version
        # Output format: "cpm-mcp (X.Y.Z)"
        import re

        versions = re.findall(r"cpm-mcp \(([0-9.]+)\)", result.stdout)

        if not versions:
            console.print("[yellow]Could not determine latest version[/]")
            if not check:
                console.print("\n[dim]Attempting upgrade anyway...[/]")
        else:
            latest_version = versions[0]
            console.print(f"[dim]Latest version:[/] {latest_version}")

            # Compare versions
            if current_version == latest_version:
                console.print(f"\n[green]+ CPM is up to date ({current_version})[/]")
                return

            console.print(f"\n[yellow]Update available: {current_version} → {latest_version}[/]")

            if check:
                console.print("\n[dim]Run 'cpm upgrade' to update[/]")
                return

    except subprocess.TimeoutExpired:
        console.print("[yellow]Warning: Check timed out[/]")
        if check:
            return

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to check version: {e}[/]")
        if check:
            return

    # Confirm upgrade
    if not yes and not check:
        console.print()
        if not click.confirm("Upgrade CPM?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    # Perform upgrade
    console.print("\n[cyan]Upgrading CPM...[/]\n")

    try:
        # Run pip upgrade
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "cpm-mcp"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]+ CPM upgraded successfully![/]")

            # Try to get new version
            try:
                import importlib
                import cpm

                importlib.reload(cpm)
                new_version = cpm.__version__
                console.print(f"\n[dim]New version:[/] {new_version}")
            except:
                pass

            console.print("\n[dim]Restart your terminal to use the new version[/]")

        else:
            console.print("[red]Error:[/] Upgrade failed")
            if result.stderr:
                console.print(f"\n[dim]{result.stderr}[/]")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to upgrade: {e}")
        raise click.Abort()
