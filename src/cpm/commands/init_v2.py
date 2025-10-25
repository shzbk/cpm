"""
Initialize command v2 - Create MCP-compliant projects

Replaces old init command with one that creates proper server.json
following MCP official registry standards.

Creates:
  server.json - Project manifest (like package.json)
  server-lock.json - Lockfile with pinned versions
  .cpmrc (optional) - Project-specific CPM configuration
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from cpm.core.schema import ServerLockfile, ServerManifest

console = Console()


@click.command()
@click.argument("project_name")
@click.option(
    "--description",
    "-d",
    help="Project description",
)
@click.option(
    "--version",
    "-v",
    default="1.0.0",
    help="Initial version",
)
@click.option(
    "--with-example",
    is_flag=True,
    help="Add example servers (brave-search, filesystem)",
)
def init(
    project_name: str,
    description: Optional[str] = None,
    version: str = "1.0.0",
    with_example: bool = False,
):
    """
    Initialize a new MCP project with server.json.

    Creates a project directory with:
    - server.json (project manifest)
    - server-lock.json (lock file, initially empty)
    - .cpm/ (directory for CPM metadata)

    Examples:

        \b
        cpm init my-project
        cpm init my-project --description "My MCP Project"
        cpm init my-project --with-example
    """

    project_path = Path(project_name)

    # Check if directory already exists
    if project_path.exists():
        console.print(f"[red]Error:[/] Directory already exists: {project_name}")
        raise click.Abort()

    # Create project structure
    console.print(f"[cyan]Initializing project:[/] {project_name}\n")

    try:
        # Create directories
        project_path.mkdir(parents=True, exist_ok=True)
        cpm_dir = project_path / ".cpm"
        cpm_dir.mkdir(exist_ok=True)

        console.print(f"  [green][OK][/] Created directory: {project_name}")

        # Create server.json (manifest)
        manifest = ServerManifest(
            name=project_name,
            version=version,
            description=description or "",
        )

        # Add example servers if requested
        if with_example:
            manifest.servers = {
                "brave-search": "latest",
                "filesystem": "latest",
            }
            manifest.groups = {
                "tools": ["brave-search"],
                "utilities": ["filesystem"],
            }

        # Write server.json
        server_json_file = project_path / "server.json"
        with open(server_json_file, "w") as f:
            json.dump(manifest.model_dump(exclude_unset=True), f, indent=2)

        console.print(f"  [green][OK][/] Created: server.json")

        # Create server-lock.json (empty lockfile)
        lockfile = ServerLockfile()
        server_lock_file = project_path / "server-lock.json"
        with open(server_lock_file, "w") as f:
            json.dump(lockfile.model_dump(), f, indent=2)

        console.print(f"  [green][OK][/] Created: server-lock.json")

        # Create .cpm directory for CPM metadata
        console.print(f"  [green][OK][/] Created: .cpm/")

        # Create .gitignore
        gitignore_content = """.cpm/
node_modules/
__pycache__/
*.pyc
.env
.env.local
"""
        gitignore_file = project_path / ".gitignore"
        gitignore_file.write_text(gitignore_content)
        console.print(f"  [green][OK][/] Created: .gitignore")

        # Success message
        console.print(f"\n[green]Project initialized![/]\n")

        console.print("[bold]Next steps:[/]\n")
        console.print(f"  cd {project_name}")
        console.print(f"  cpm install <server-name>      # Install a server")
        if with_example:
            console.print(f"  cpm install                    # Install example servers")

        console.print(f"\n  cpm run <server-name>          # Run a server")
        console.print(f"  cpm add <server-name>          # Add to MCP clients")
        console.print(f"\nServer manifest: [cyan]{project_name}/server.json[/]")

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to initialize project: {e}")
        # Clean up on failure
        if project_path.exists():
            import shutil
            shutil.rmtree(project_path)
        raise click.Abort()


# Optional: cpm init --template command for future templates
@click.command()
def list_templates():
    """List available project templates (future feature)."""

    console.print("[yellow]Available templates:[/]\n")
    console.print("  [cyan]basic[/]          - Minimal MCP project")
    console.print("  [cyan]web-search[/]     - With web search servers")
    console.print("  [cyan]data-tools[/]     - With database/data tools")
    console.print("  [cyan]ai-agent[/]       - Full AI agent setup")
    console.print("\n[dim]Run:[/] cpm init my-project --template <template>")
