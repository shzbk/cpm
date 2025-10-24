"""
Version command - Show version information and manage project versions
"""

import json
import platform
import sys
from pathlib import Path

import click
from rich.console import Console

from cpm import __version__
from cpm.core.local_config import LocalConfigManager

console = Console()
console_err = Console(stderr=True)


@click.command()
@click.argument("newversion", required=False)
@click.option("--json-output", "-j", "--json", is_flag=True, help="Output as JSON")
@click.pass_context
def version(ctx, newversion, json_output):
    """
    Display version information or bump project version

    Without arguments: Shows CPM and dependency versions
    With argument: Bumps project version in server.json (requires server.json)

    \b
    Examples:
        cpm version                    # Show all versions
        cpm version --json             # Show as JSON
        cpm version 1.2.0              # Set project version to 1.2.0
        cpm version major              # Bump major version (1.0.0 -> 2.0.0)
        cpm version minor              # Bump minor version (1.0.0 -> 1.1.0)
        cpm version patch              # Bump patch version (1.0.0 -> 1.0.1)

    Version bump requires server.json in current directory.
    """
    # Check if we're bumping project version
    if newversion:
        bump_project_version(newversion)
        return

    # Show version information
    show_version_info(json_output, ctx.obj.get("local", False))


def show_version_info(json_output: bool, local_context: bool):
    """Show CPM and dependency versions"""
    # Get Python version
    python_version = platform.python_version()

    # Get dependency versions
    versions = {
        "cpm": __version__,
        "python": python_version,
    }

    # Try to get versions of key dependencies
    try:
        import click as click_module

        versions["click"] = click_module.__version__
    except (ImportError, AttributeError):
        pass

    try:
        import rich

        versions["rich"] = rich.__version__
    except (ImportError, AttributeError):
        pass

    try:
        import pydantic

        versions["pydantic"] = pydantic.__version__
    except (ImportError, AttributeError):
        pass

    try:
        import requests

        versions["requests"] = requests.__version__
    except (ImportError, AttributeError):
        pass

    try:
        import fastmcp

        versions["fastmcp"] = fastmcp.__version__
    except (ImportError, AttributeError):
        pass

    try:
        import mcp

        versions["mcp"] = mcp.__version__
    except (ImportError, AttributeError):
        pass

    # Add system info
    versions["platform"] = platform.system().lower()
    versions["arch"] = platform.machine()

    # Add project version if in local context
    if LocalConfigManager.detect_project():
        try:
            local_config = LocalConfigManager()
            manifest = local_config.load_manifest()
            versions[manifest.name] = manifest.version
        except Exception:
            pass

    # Print as JSON (npm style)
    print(json.dumps(versions, indent=2))


def bump_project_version(newversion: str):
    """Bump project version in server.json"""
    # Check if server.json exists
    if not LocalConfigManager.detect_project():
        console_err.print(
            "[red]Error:[/] No server.json found. Run [cyan]cpm init[/] first."
        )
        raise click.Abort()

    local_config = LocalConfigManager()

    try:
        manifest = local_config.load_manifest()
        current_version = manifest.version

        # Parse version bump type or use exact version
        if newversion in ["major", "minor", "patch"]:
            new_version = calculate_semver_bump(current_version, newversion)
        else:
            # Validate version format (basic check)
            if not is_valid_version(newversion):
                console_err.print(
                    f"[red]Error:[/] Invalid version format: {newversion}"
                )
                console_err.print(
                    "Use semantic version (e.g., 1.2.3) or bump type (major, minor, patch)"
                )
                raise click.Abort()
            new_version = newversion

        # Update manifest
        manifest.version = new_version
        local_config._save_manifest(manifest)

        # Show result (npm style - just the version)
        console.print(f"v{new_version}")

    except Exception as e:
        console_err.print(f"[red]Error:[/] {e}")
        raise click.Abort()


def calculate_semver_bump(current: str, bump_type: str) -> str:
    """Calculate new version based on bump type"""
    # Remove 'v' prefix if present
    current = current.lstrip("v")

    # Parse version
    parts = current.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")

    try:
        major, minor, patch = map(int, parts)
    except ValueError:
        raise ValueError(f"Invalid version format: {current}")

    # Bump version
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1

    return f"{major}.{minor}.{patch}"


def is_valid_version(version: str) -> bool:
    """Validate version format (basic semantic versioning)"""
    # Remove 'v' prefix if present
    version = version.lstrip("v")

    # Check format: x.y.z where x, y, z are numbers
    parts = version.split(".")
    if len(parts) != 3:
        return False

    try:
        for part in parts:
            int(part)
        return True
    except ValueError:
        return False
