"""
Initialize a new CPM project
"""

import click
from pathlib import Path
from rich.console import Console

from cpm.core.local_config import LocalConfigManager

console = Console()


@click.command()
@click.option("-y", "--yes", is_flag=True, help="Use default values without prompting")
@click.option("--template", type=str, help="Use a template (ai-agent, basic)")
@click.option("--name", type=str, help="Project name")
@click.option("--version", default="1.0.0", help="Project version")
def init(yes, template, name, version):
    """
    Initialize a new CPM project

    Creates a server.json file in the current directory and sets up
    the project structure for managing MCP servers.

    Examples:

        \b
        cpm init                              # Interactive wizard
        cpm init --yes                        # Use defaults
        cpm init --template ai-agent          # Use ai-agent template
        cpm init --name my-project            # Specify name
    """
    # Check if already initialized
    manager = LocalConfigManager()

    if manager.config_file.exists():
        console.print(f"[yellow]Warning:[/] Project already initialized: {manager.config_file}")
        if not click.confirm("Reinitialize project?", default=False):
            console.print("[yellow]Aborted[/]")
            return
        console.print()

    # Get project name
    if not name:
        if yes:
            # Use directory name as default
            name = Path.cwd().name
        else:
            name = click.prompt("Project name", default=Path.cwd().name)

    # Get version
    if not yes and not version:
        version = click.prompt("Version", default="1.0.0")

    # Get template
    if not template and not yes:
        console.print("\n[cyan]Available templates:[/]")
        console.print("  [green]basic[/]     - Empty project")
        console.print("  [green]ai-agent[/]  - AI agent with common tools")
        console.print()

        template = click.prompt(
            "Template",
            default="basic",
            type=click.Choice(["basic", "ai-agent"], case_sensitive=False),
        )

    # Initialize project
    try:
        console.print(f"\n[cyan]Initializing project...[/]\n")

        manifest = manager.init_project(
            name=name,
            version=version,
            template=template if template else "basic",
        )

        console.print(f"[green]+[/] Created {manager.config_file}")
        console.print(f"[green]+[/] Created {manager.local_dir}/")

        # Show what was created
        console.print(f"\n[cyan]Project initialized:[/]")
        console.print(f"  [dim]Name:[/] {manifest.name}")
        console.print(f"  [dim]Version:[/] {manifest.version}")

        if manifest.servers:
            console.print(f"  [dim]Servers:[/] {', '.join(manifest.servers.keys())}")

        if manifest.groups:
            console.print(f"  [dim]Groups:[/] {', '.join(manifest.groups.keys())}")

        console.print(f"\n[green]Next steps:[/]")
        console.print(f"  cpm install <server>            # Add servers (auto-detects server.json)")
        console.print(f"  cpm install                     # Install from server.json")
        console.print(f"  cpm run <server>                # Run servers")
        console.print()

    except FileExistsError as e:
        console.print(f"[red]Error:[/] {e}")
        raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to initialize project: {e}")
        raise click.Abort()
